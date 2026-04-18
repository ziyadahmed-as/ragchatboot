from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound

from .models import TranscriptChunk, TranscriptSession
from .serializers import (
    TranscriptChunkSerializer,
    TranscriptSessionSerializer,
    TranscriptSessionListSerializer,
)


class TranscriptSessionListView(generics.ListAPIView):
    """GET /api/sessions/ — list all sessions ordered by created_at desc."""
    queryset = TranscriptSession.objects.all().order_by("-created_at")
    serializer_class = TranscriptSessionListSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


class TranscriptSessionDetailView(generics.RetrieveAPIView):
    """GET /api/sessions/{id}/ — retrieve a single session with chunks."""
    queryset = TranscriptSession.objects.all()
    serializer_class = TranscriptSessionSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


class TranscriptChunkListView(generics.ListAPIView):
    """GET /api/sessions/{id}/chunks/ — list chunks ordered by sequence_number asc."""
    serializer_class = TranscriptChunkSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        session_id = self.kwargs["pk"]
        # Return 404 if session doesn't exist
        if not TranscriptSession.objects.filter(pk=session_id).exists():
            raise NotFound(detail="Session not found.")
        return TranscriptChunk.objects.filter(
            session_id=session_id
        ).order_by("sequence_number")
