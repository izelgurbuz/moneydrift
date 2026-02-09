import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def list_balance_transactions(limit=100):
    return stripe.BalanceTransaction.list(limit=limit)
