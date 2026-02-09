from __future__ import annotations

import urllib.parse

import requests
from django.conf import settings
from django.utils import timezone

from integrations.models import TrueLayerToken


def build_auth_link(*, state: str) -> str:
    """
    Build TrueLayer authorization URL.

    According to TrueLayer docs:
    https://docs.truelayer.com/docs/generate-an-auth-link

    The auth URL format is:
    https://auth.truelayer.com/?response_type=code&client_id=...
    """
    params = {
        "response_type": "code",
        "client_id": settings.TRUELAYER_CLIENT_ID,
        "redirect_uri": settings.TRUELAYER_REDIRECT_URI,
        "scope": "accounts transactions offline_access",
        "providers": "uk-cs-mock uk-ob-all uk-oauth-all",  # Added more providers
        "state": state,
    }

    return f"https://auth.truelayer-sandbox.com/?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(*, code: str) -> TrueLayerToken:
    """
    Exchange authorization code for access token.

    Token endpoint: https://auth.truelayer.com/connect/token
    (or https://auth.truelayer-sandbox.com/connect/token for sandbox)
    """
    url = f"{settings.TRUELAYER_TOKEN_BASE_URL}/connect/token"

    data = {
        "grant_type": "authorization_code",
        "client_id": settings.TRUELAYER_CLIENT_ID,
        "client_secret": settings.TRUELAYER_CLIENT_SECRET,
        "redirect_uri": settings.TRUELAYER_REDIRECT_URI,
        "code": code,
    }

    resp = requests.post(url, data=data, timeout=15)
    resp.raise_for_status()
    payload = resp.json()

    expires_at = timezone.now() + timezone.timedelta(seconds=int(payload["expires_in"]))

    token = TrueLayerToken.objects.first()
    if token:
        token.access_token = payload["access_token"]
        token.refresh_token = payload.get("refresh_token", token.refresh_token)
        token.expires_at = expires_at
        token.save()
        return token

    return TrueLayerToken.objects.create(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token", ""),
        expires_at=expires_at,
    )


def refresh_access_token(*, refresh_token: str) -> dict:
    """
    Refresh an expired access token using a refresh token.

    Token endpoint: https://auth.truelayer.com/connect/token
    """
    url = f"{settings.TRUELAYER_TOKEN_BASE_URL}/connect/token"

    data = {
        "grant_type": "refresh_token",
        "client_id": settings.TRUELAYER_CLIENT_ID,
        "client_secret": settings.TRUELAYER_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }

    resp = requests.post(url, data=data, timeout=15)
    resp.raise_for_status()
    return resp.json()
