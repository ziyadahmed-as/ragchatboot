import uuid
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class TranscriptSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    language = models.CharField(max_length=10, default="en")
    full_transcript = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    speaker_label = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        """Ensure ended_at >= created_at when both are set."""
        if self.ended_at is not None and self.created_at is not None:
            if self.ended_at < self.created_at:
                raise ValidationError(
                    {"ended_at": "ended_at must be greater than or equal to created_at."}
                )

    def __str__(self):
        return f"TranscriptSession({self.id}, active={self.is_active})"


class TranscriptChunk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        TranscriptSession, on_delete=models.CASCADE, related_name="chunks"
    )
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    sequence_number = models.PositiveIntegerField()
    language = models.CharField(max_length=10, default="en")
    confidence = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    speaker_label = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        ordering = ["sequence_number"]
        unique_together = [("session", "sequence_number")]

    def __str__(self):
        return f"TranscriptChunk({self.session_id}, seq={self.sequence_number})"


class Speaker(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        TranscriptSession, on_delete=models.CASCADE, related_name="speakers"
    )
    label = models.CharField(max_length=100)
    voice_embedding = models.BinaryField(null=True, blank=True)

    def __str__(self):
        return f"Speaker({self.label}, session={self.session_id})"
