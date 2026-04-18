from rest_framework import serializers
from .models import TranscriptSession, TranscriptChunk


class TranscriptChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranscriptChunk
        fields = [
            "id", "session", "text", "timestamp",
            "sequence_number", "language", "confidence", "speaker_label",
        ]
        read_only_fields = ["id", "timestamp"]


class TranscriptSessionSerializer(serializers.ModelSerializer):
    """Full session detail — includes nested chunks."""
    chunks = TranscriptChunkSerializer(many=True, read_only=True)

    class Meta:
        model = TranscriptSession
        fields = [
            "id", "created_at", "ended_at", "language",
            "full_transcript", "is_active", "speaker_label", "chunks",
        ]
        read_only_fields = ["id", "created_at"]


class TranscriptSessionListSerializer(serializers.ModelSerializer):
    """Lightweight session list — no nested chunks."""
    class Meta:
        model = TranscriptSession
        fields = [
            "id", "created_at", "ended_at", "language",
            "full_transcript", "is_active", "speaker_label",
        ]
        read_only_fields = ["id", "created_at"]
