# Live Audio Transcription System

A real-time web application that captures microphone audio in the browser, streams it over WebSockets to a Django backend, transcribes speech using OpenAI Whisper, and displays live transcription results in a React/Next.js frontend.

## Objective

Build a production-ready live audio transcription system that:
- Provides near real-time speech-to-text conversion with low latency
- Persists transcription sessions and text for later retrieval
- Supports multiple languages with automatic detection
- Scales horizontally using Redis as a message broker
- Deploys easily via Docker with NGINX as a reverse proxy

## How It Works

### Architecture Overview

```
Browser (React/Next.js)
    ↓ WebSocket (audio chunks)
NGINX (reverse proxy + TLS)
    ↓
Django + Channels (ASGI)
    ↓
AudioTranscriptConsumer
    ↓
WhisperTranscriber (OpenAI Whisper)
    ↓
PostgreSQL (persistence)
    ↑
Redis (channel layer)
```

### Core Flow

1. **Audio Capture (Browser)**
   - User grants microphone permission
   - Web Audio API captures PCM audio at 16kHz mono
   - MediaRecorder emits 1-second chunks
   - Each chunk is sent as binary data over WebSocket

2. **WebSocket Connection**
   - Client connects to `ws://server/ws/transcribe/{session_id}/`
   - Django Channels consumer validates UUID and authenticates token
   - Creates `TranscriptSession` record in PostgreSQL
   - Sends `session.started` confirmation to client

3. **Real-Time Transcription**
   - Consumer receives binary audio chunk
   - Validates chunk size (max 1MB)
   - Runs Whisper inference in thread pool executor (non-blocking)
   - Whisper converts PCM bytes → float32 numpy array → text
   - Persists `TranscriptChunk` with sequence number
   - Broadcasts `transcript.partial` message to client via Redis

4. **Session Finalization**
   - User stops recording or disconnects
   - Consumer assembles `full_transcript` from ordered chunks
   - Sets `is_active=False` and `ended_at` timestamp
   - Sends `session.ended` with full transcript to client

5. **REST API Retrieval**
   - `GET /api/sessions/` — list all sessions (ordered by date)
   - `GET /api/sessions/{id}/` — retrieve session with nested chunks
   - `GET /api/sessions/{id}/chunks/` — list chunks ordered by sequence
   - Token authentication required for all endpoints

### Key Components

**Backend (Django + Channels)**
- `AudioTranscriptConsumer` — WebSocket handler for audio streaming
- `WhisperTranscriber` — Singleton wrapper around OpenAI Whisper model
- `TranscriptSession` / `TranscriptChunk` models — PostgreSQL persistence
- REST API views — DRF endpoints for transcript retrieval
- Token authentication — DRF TokenAuthentication

**Frontend (React/Next.js)**
- `useAudioRecorder` hook — MediaRecorder + WebSocket streaming
- `useTranscriptionSocket` hook — WebSocket lifecycle + reconnection
- `TranscriptionPanel` component — UI for recording + live display

**Infrastructure**
- PostgreSQL — Persistent storage for sessions and chunks
- Redis — Django Channels channel layer (pub/sub)
- NGINX — Reverse proxy, TLS termination, rate limiting
- Docker Compose — Orchestrates all services

### Data Flow Example

```
1. Browser: Start recording
   → WebSocket: CONNECT ws://server/ws/transcribe/{uuid}/
   ← Server: {"type": "session.started", "session_id": "..."}

2. Browser: Send audio chunk (1 second of PCM)
   → Server: [binary data]
   ← Server: {"type": "transcript.partial", "text": "Hello world", "timestamp": "..."}

3. Browser: Send audio chunk
   → Server: [binary data]
   ← Server: {"type": "transcript.partial", "text": "How are you", "timestamp": "..."}

4. Browser: Stop recording
   → Server: {"type": "recording.stop"}
   ← Server: {"type": "session.ended", "full_transcript": "Hello world How are you"}

5. Browser: Retrieve past sessions
   → Server: GET /api/sessions/
   ← Server: [{"id": "...", "full_transcript": "...", "created_at": "..."}, ...]
```

## Technology Stack

**Backend**
- Django 6.0 — Web framework
- Django Channels 4.0 — WebSocket support (ASGI)
- Django REST Framework 3.16 — REST API
- OpenAI Whisper — Speech-to-text model
- PostgreSQL — Database
- Redis — Channel layer broker
- Daphne — ASGI server

**Frontend**
- React / Next.js — UI framework
- TypeScript — Type safety
- Web Audio API — Microphone capture
- WebSocket API — Real-time communication

**Infrastructure**
- Docker + Docker Compose — Containerization
- NGINX — Reverse proxy + rate limiting
- python-decouple — Environment config

## Features

- ✅ Real-time audio transcription with <1s latency
- ✅ Automatic language detection (supports 99 languages)
- ✅ Session persistence with full transcript history
- ✅ Token-based authentication
- ✅ WebSocket reconnection with exponential backoff
- ✅ Rate limiting at NGINX level
- ✅ CORS configuration for cross-origin requests
- ✅ Docker deployment with health checks
- ✅ Graceful error handling and retry logic
- ✅ Sequence number validation for chunk ordering

## Optional Advanced Features

- Speaker diarization (identify multiple speakers)
- Real-time translation to target language
- Automatic summarization on session end
- Keyword extraction from transcripts

## Getting Started

### Prerequisites
- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- Node.js 18+ (for frontend)
- Docker + Docker Compose (optional)

### Backend Setup

```bash
cd backend
python -m venv env
source env/bin/activate  # Windows: env\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your database credentials
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Docker Setup

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with production values
docker-compose up --build
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/token/` | Obtain auth token |
| GET | `/api/sessions/` | List all sessions |
| GET | `/api/sessions/{id}/` | Get session detail |
| GET | `/api/sessions/{id}/chunks/` | List session chunks |
| WS | `/ws/transcribe/{uuid}/` | WebSocket transcription |

### Authentication

```bash
# Get token
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Use token
curl http://localhost:8000/api/sessions/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"
```

## Project Structure

```
.
├── backend/
│   ├── streaming/          # Django project config
│   │   ├── settings.py     # Settings with env vars
│   │   ├── urls.py         # URL routing
│   │   └── asgi.py         # ASGI config for Channels
│   ├── transcription/      # Main app
│   │   ├── models.py       # TranscriptSession, TranscriptChunk
│   │   ├── consumers.py    # WebSocket consumer
│   │   ├── transcriber.py  # Whisper wrapper
│   │   ├── views.py        # REST API views
│   │   ├── serializers.py  # DRF serializers
│   │   ├── urls.py         # API routes
│   │   └── routing.py      # WebSocket routes
│   ├── manage.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React/Next.js (to be implemented)
├── nginx/
│   └── nginx.conf         # Reverse proxy config
├── docker-compose.yml
└── README.md
```

## License

MIT
