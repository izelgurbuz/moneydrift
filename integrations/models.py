from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class TrueLayerToken(models.Model):
    """
    Stores the current TrueLayer access token.
    Single-tenant for now; can be extended to multi-user later.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, default="")
    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    class Meta:
        db_table = "integrations_truelayer_token"


class OAuthState(models.Model):
    """
    Production-grade OAuth state store.
    Avoids browser sessions entirely.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    provider = models.CharField(max_length=32)  # e.g. "truelayer"
    state = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "integrations_oauth_state"
        indexes = [
            models.Index(fields=["provider", "state"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["used_at"]),
        ]

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def mark_used(self) -> None:
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])
