import uuid
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="TranscriptSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("language", models.CharField(default="en", max_length=10)),
                ("full_transcript", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("speaker_label", models.CharField(blank=True, default="", max_length=100)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="TranscriptChunk",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chunks", to="transcription.transcriptsession")),
                ("text", models.TextField()),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("sequence_number", models.PositiveIntegerField()),
                ("language", models.CharField(default="en", max_length=10)),
                ("confidence", models.FloatField(
                    blank=True,
                    null=True,
                    validators=[
                        django.core.validators.MinValueValidator(0.0),
                        django.core.validators.MaxValueValidator(1.0),
                    ],
                )),
                ("speaker_label", models.CharField(blank=True, default="", max_length=100)),
            ],
            options={"ordering": ["sequence_number"]},
        ),
        migrations.AlterUniqueTogether(
            name="transcriptchunk",
            unique_together={("session", "sequence_number")},
        ),
        migrations.CreateModel(
            name="Speaker",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="speakers", to="transcription.transcriptsession")),
                ("label", models.CharField(max_length=100)),
                ("voice_embedding", models.BinaryField(blank=True, null=True)),
            ],
        ),
    ]
