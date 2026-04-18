"""
WhisperTranscriber — singleton wrapper around OpenAI Whisper.
"""
import numpy as np
from dataclasses import dataclass, field


@dataclass
class TranscriptionResult:
    text: str
    language: str
    segments: list = field(default_factory=list)
    duration: float = 0.0


class WhisperTranscriber:
    """Singleton that loads the Whisper model once and reuses it."""

    _instance = None

    def __new__(cls, model_name: str = "base"):
        if cls._instance is None:
            import whisper
            import torch

            cls._instance = super().__new__(cls)
            cls._instance._model_name = model_name
            cls._instance.model = whisper.load_model(
                model_name,
                device="cuda" if torch.cuda.is_available() else "cpu",
            )
        return cls._instance

    def _bytes_to_audio_array(self, audio_bytes: bytes) -> np.ndarray:
        """Convert raw PCM 16-bit LE bytes to float32 array in [-1.0, 1.0]."""
        if len(audio_bytes) == 0 or len(audio_bytes) % 2 != 0:
            raise ValueError(
                f"Malformed PCM bytes: length {len(audio_bytes)} is not a multiple of 2."
            )
        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
        return audio_int16.astype(np.float32) / 32768.0

    def transcribe(self, audio_bytes: bytes, language: str = None) -> TranscriptionResult:
        """
        Transcribe raw PCM audio bytes using Whisper.

        Raises:
            ValueError: if audio_bytes are malformed PCM.
            RuntimeError: propagated from Whisper (e.g. GPU OOM).
        """
        audio_float32 = self._bytes_to_audio_array(audio_bytes)

        options = {}
        if language:
            options["language"] = language

        result = self.model.transcribe(audio_float32, **options)

        return TranscriptionResult(
            text=result["text"],
            language=result.get("language", language or "en"),
            segments=result.get("segments", []),
            duration=result.get("duration", 0.0),
        )
