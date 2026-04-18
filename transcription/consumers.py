"""
AudioTranscriptConsumer — Django Channels WebSocket consumer.
"""
import asyncio
import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from .models import TranscriptChunk, TranscriptSession
from .transcriber import WhisperTranscriber

logger = logging.getLogger(__name__)

MAX_CHUNK_BYTES = 1_048_576  # 1 MB
MAX_DB_RETRIES = 3
_executor = ThreadPoolExecutor()


def _get_transcriber() -> WhisperTranscriber:
    """Lazy-load transcriber so tests can mock it easily."""
    return WhisperTranscriber()


class AudioTranscriptConsumer(AsyncWebsocketConsumer):
    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self):
        raw_id = self.scope["url_route"]["kwargs"].get("session_id", "")

        # Validate UUID before any DB work (Req 9.5)
        try:
            self.session_id = uuid.UUID(str(raw_id))
        except (ValueError, AttributeError):
            await self.close(code=4001)
            return

        # Token authentication (Req 9.1)
        if not await self._authenticate():
            await self.close(code=4001)
            return

        self.group_name = f"transcript_{self.session_id}"
        self.sequence_counter = 0
        self._finalized = False

        # Join channel group — Redis unreachable → 1011 (Req 1.7)
        try:
            await self.channel_layer.group_add(self.group_name, self.channel_name)
        except Exception:
            logger.critical("Redis channel layer unreachable on connect.")
            await self.close(code=1011)
            return

        # Create session record
        self.session = await TranscriptSession.objects.acreate(
            id=self.session_id, is_active=True
        )

        await self.accept()
        await self.send(
            json.dumps({"type": "session.started", "session_id": str(self.session_id)})
        )

    async def disconnect(self, close_code):
        if hasattr(self, "session") and self.session.is_active and not self._finalized:
            await self._finalize_session()
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data:
            await self._handle_audio_chunk(bytes_data)
        elif text_data:
            try:
                msg = json.loads(text_data)
            except json.JSONDecodeError:
                return
            if msg.get("type") == "recording.stop":
                await self._finalize_session()

    # ------------------------------------------------------------------
    # Audio processing
    # ------------------------------------------------------------------

    async def _handle_audio_chunk(self, audio_bytes: bytes):
        # Reject oversized chunks (Req 9.3)
        if len(audio_bytes) > MAX_CHUNK_BYTES:
            logger.warning("Rejected oversized audio chunk (%d bytes).", len(audio_bytes))
            return

        # Discard if session is no longer active (Req 2.4)
        if not self.session.is_active or self._finalized:
            return

        loop = asyncio.get_event_loop()
        transcriber = _get_transcriber()

        try:
            result = await loop.run_in_executor(
                _executor, transcriber.transcribe, audio_bytes
            )
        except ValueError as exc:
            logger.warning("Malformed PCM bytes: %s", exc)
            await self.send(json.dumps({"type": "transcript.error", "message": str(exc)}))
            return
        except RuntimeError as exc:
            logger.error("Whisper RuntimeError: %s", exc)
            await self.send(
                json.dumps({"type": "transcript.error", "message": "Transcription failed"})
            )
            return

        # Skip silence (Req 2.3)
        if not result.text.strip():
            return

        # Persist with retry/backoff (Req 4.5)
        chunk = await self._save_chunk_with_retry(result)
        if chunk is None:
            # DB failed after all retries — still broadcast (Req 10.2)
            pass

        # Broadcast partial transcript (Req 2.5)
        timestamp = timezone.now().isoformat()
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "transcript_partial",
                "text": result.text.strip(),
                "timestamp": timestamp,
                "language": result.language,
            },
        )

    async def transcript_partial(self, event):
        """Handler called by channel layer group_send."""
        await self.send(
            json.dumps(
                {
                    "type": "transcript.partial",
                    "text": event["text"],
                    "timestamp": event["timestamp"],
                    "language": event["language"],
                }
            )
        )

    async def _save_chunk_with_retry(self, result):
        from django.db import DatabaseError

        delay = 0.1
        for attempt in range(MAX_DB_RETRIES):
            try:
                chunk = await TranscriptChunk.objects.acreate(
                    session=self.session,
                    text=result.text.strip(),
                    sequence_number=self.sequence_counter,
                    language=result.language,
                )
                self.sequence_counter += 1
                return chunk
            except DatabaseError as exc:
                logger.error("DB write failed (attempt %d): %s", attempt + 1, exc)
                await asyncio.sleep(delay)
                delay *= 2
        logger.error("All DB retries exhausted for session %s.", self.session_id)
        return None

    # ------------------------------------------------------------------
    # Session finalization
    # ------------------------------------------------------------------

    async def _finalize_session(self):
        if self._finalized:
            return
        self._finalized = True

        chunks = TranscriptChunk.objects.filter(
            session=self.session
        ).order_by("sequence_number")

        texts = []
        async for chunk in chunks:
            texts.append(chunk.text)

        self.session.full_transcript = " ".join(texts)
        self.session.is_active = False
        self.session.ended_at = timezone.now()
        await self.session.asave()

        await self.send(
            json.dumps(
                {"type": "session.ended", "full_transcript": self.session.full_transcript}
            )
        )

    # ------------------------------------------------------------------
    # Auth helper
    # ------------------------------------------------------------------

    async def _authenticate(self) -> bool:
        """
        Validate token from query string or headers.
        Returns True if authenticated, False otherwise.
        """
        from rest_framework.authtoken.models import Token
        from asgiref.sync import sync_to_async

        # Try query string: ?token=<key>
        query_string = self.scope.get("query_string", b"").decode()
        token_key = None
        for part in query_string.split("&"):
            if part.startswith("token="):
                token_key = part[len("token="):]
                break

        # Try Authorization header
        if not token_key:
            headers = dict(self.scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            if auth_header.lower().startswith("token "):
                token_key = auth_header[6:].strip()

        if not token_key:
            return False

        try:
            token = await sync_to_async(Token.objects.select_related("user").get)(
                key=token_key
            )
            self.scope["user"] = token.user
            return True
        except Token.DoesNotExist:
            return False
