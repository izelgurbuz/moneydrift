from __future__ import annotations

import logging
import secrets

import requests
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils import timezone

from integrations.models import OAuthState, TrueLayerToken
from integrations.truelayer_oauth import (
    build_auth_link,
    exchange_code_for_token,
    refresh_access_token,
)
from ledger.services import post_move

logger = logging.getLogger(__name__)

OAUTH_STATE_TTL_SECONDS = 10 * 60  # 10 minutes


def truelayer_connect(request: HttpRequest):
    state = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timezone.timedelta(seconds=OAUTH_STATE_TTL_SECONDS)

    OAuthState.objects.create(
        provider="truelayer",
        state=state,
        expires_at=expires_at,
    )

    auth_url = build_auth_link(state=state)
    logger.info(f"Redirecting to TrueLayer auth URL: {auth_url}")

    return redirect(auth_url)


def truelayer_callback(request: HttpRequest):
    """
    Step 2: Handle OAuth callback from TrueLayer
    - Validates the state token (CSRF protection)
    - Exchanges authorization code for access token
    - Stores access token in database
    """
    code = request.GET.get("code", "")
    state = request.GET.get("state", "")
    error = request.GET.get("error", "")
    error_description = request.GET.get("error_description", "")

    logger.info(
        f"Callback received - code: {bool(code)}, state: {bool(state)}, error: {error}"
    )

    if error:
        logger.error(f"TrueLayer OAuth error: {error} - {error_description}")
        return HttpResponse(
            f"TrueLayer error: {error} - {error_description}", status=400
        )

    if not code or not state:
        logger.error("Missing code or state parameter")
        return HttpResponse("Missing code/state", status=400)

    oauth = OAuthState.objects.filter(provider="truelayer", state=state).first()
    if not oauth:
        logger.error(f"Unknown state token: {state}")
        return HttpResponse("Unknown state (possible CSRF attack)", status=400)

    if oauth.used_at is not None:
        logger.warning(f"State already used: {state}")
        return HttpResponse("State already used (replay detected)", status=400)

    if oauth.is_expired():
        logger.warning(f"State expired: {state}")
        return HttpResponse("State expired (took too long to authorize)", status=400)

    oauth.mark_used()

    try:
        logger.info("Exchanging code for token...")
        token = exchange_code_for_token(code=code)
        logger.info(f"Token exchange successful. Token ID: {token.id}")
    except requests.HTTPError as e:
        logger.error(
            f"Token exchange failed: {e.response.status_code} - {e.response.text}"
        )
        return HttpResponse(
            f"Token exchange failed: {e.response.status_code} - {e.response.text}",
            status=400,
        )
    except Exception as e:
        logger.error(f"Unexpected error during token exchange: {e}")
        return HttpResponse(f"Unexpected error: {e}", status=500)

    return HttpResponse(
        "TrueLayer connected successfully! You can now sync your transactions at /truelayer/sync",
        status=200,
    )


def truelayer_sync(request: HttpRequest):
    token = TrueLayerToken.objects.first()
    if not token:
        logger.error("No TrueLayer token found")
        return HttpResponse(
            "No TrueLayer token stored. Please connect first at /truelayer/connect",
            status=400,
        )

    if token.is_expired:
        logger.info("Access token expired, refreshing...")
        if not token.refresh_token:
            logger.error("No refresh token available")
            return HttpResponse(
                "Access token expired and no refresh token available. Please reconnect at /truelayer/connect",
                status=400,
            )

        try:
            payload = refresh_access_token(refresh_token=token.refresh_token)
            token.access_token = payload["access_token"]
            token.refresh_token = payload.get("refresh_token", token.refresh_token)
            token.expires_at = timezone.now() + timezone.timedelta(
                seconds=int(payload["expires_in"])
            )
            token.save()
            logger.info("Token refreshed successfully")
        except requests.HTTPError as e:
            logger.error(f"Token refresh failed: {e.response.text}")
            return HttpResponse(
                f"Token refresh failed: {e.response.text}. Please reconnect at /truelayer/connect",
                status=400,
            )

    headers = {"Authorization": f"Bearer {token.access_token}"}

    # Fetch accounts
    try:
        accounts_url = f"{settings.TRUELAYER_DATA_BASE_URL}/data/v1/accounts"
        logger.info(f"Fetching accounts from: {accounts_url}")
        accounts_resp = requests.get(accounts_url, headers=headers, timeout=15)
        accounts_resp.raise_for_status()
        accounts = accounts_resp.json()["results"]
        logger.info(f"Found {len(accounts)} accounts")
    except requests.HTTPError as e:
        logger.error(
            f"Failed to fetch accounts: {e.response.status_code} - {e.response.text}"
        )
        return HttpResponse(
            f"Failed to fetch accounts: {e.response.status_code} - {e.response.text}",
            status=400,
        )

    ingested = 0

    # Fetch transactions for each account
    for acc in accounts:
        account_id = acc["account_id"]
        logger.info(f"Fetching transactions for account: {account_id}")

        try:
            tx_url = (
                f"{settings.TRUELAYER_DATA_BASE_URL}"
                f"/data/v1/accounts/{account_id}/transactions"
            )
            txs_resp = requests.get(tx_url, headers=headers, timeout=15)
            txs_resp.raise_for_status()
            txs = txs_resp.json()["results"]
            logger.info(f"Found {len(txs)} transactions for account {account_id}")
        except requests.HTTPError as e:
            logger.error(
                f"Failed to fetch transactions for {account_id}: {e.response.text}"
            )
            continue

        for tx in txs:
            amount_minor = int(round(float(tx["amount"]) * 100))
            if amount_minor <= 0:
                continue

            try:
                post_move(
                    reference=f"bank:{tx['transaction_id']}",
                    currency=tx["currency"].upper(),
                    from_account_code="external",
                    to_account_code="bank",
                    amount_minor=amount_minor,
                )
                ingested += 1
            except Exception as e:
                logger.error(f"Failed to post transaction {tx['transaction_id']}: {e}")
                continue

    logger.info(f"Sync complete. Ingested {ingested} transactions.")
    return HttpResponse(
        f"Sync complete. Ingested {ingested} transactions.",
        status=200,
    )
