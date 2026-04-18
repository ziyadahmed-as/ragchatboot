from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("admin/", admin.site.urls),
    # Token auth — POST {"username": "...", "password": "..."} → {"token": "..."}
    path("api/auth/token/", obtain_auth_token, name="api-token-auth"),
    # Transcript endpoints
    path("api/", include("transcription.urls")),
    # DRF browsable API login (optional, useful in DEBUG)
    path("api-auth/", include("rest_framework.urls")),
]
