import requests
from django.conf import settings


class TrueLayerClient:
    def __init__(self, access_token: str):
        self.access_token = access_token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def list_accounts(self) -> list[dict]:
        url = f"{settings.TRUELAYER_BASE_URL}/data/v1/accounts"
        resp = requests.get(url, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()["results"]

    def list_transactions(self, account_id: str) -> list[dict]:
        url = (
            f"{settings.TRUELAYER_BASE_URL}/data/v1/accounts/{account_id}/transactions"
        )
        resp = requests.get(url, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()["results"]
