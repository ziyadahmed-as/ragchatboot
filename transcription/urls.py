from django.urls import path
from .views import (
    TranscriptSessionListView,
    TranscriptSessionDetailView,
    TranscriptChunkListView,
)

urlpatterns = [
    path("sessions/", TranscriptSessionListView.as_view(), name="session-list"),
    path("sessions/<uuid:pk>/", TranscriptSessionDetailView.as_view(), name="session-detail"),
    path("sessions/<uuid:pk>/chunks/", TranscriptChunkListView.as_view(), name="chunk-list"),
]
