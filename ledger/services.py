from django.db import transaction
from django.db.models import Sum

from ledger.models import Account, LedgerEntry, LedgerTransaction


class LedgerError(Exception):
    """Base error for ledger problems."""

    pass


class AccountNotFound(LedgerError):
    pass


class InvalidAmount(LedgerError):
    pass


def post_move(
    *,
    reference: str,
    currency: str,
    from_account_code: str,
    to_account_code: str,
    amount_minor: int,
) -> None:
    if amount_minor <= 0:
        raise InvalidAmount("amount_minor must be a positive integer")

    try:
        from_account = Account.objects.get(code=from_account_code)
        to_account = Account.objects.get(code=to_account_code)
    except Account.DoesNotExist:
        raise AccountNotFound("One or both accounts do not exist")

    with transaction.atomic():
        tx, created = LedgerTransaction.objects.get_or_create(reference=reference)
        if not created:
            # This intent was already processed
            return
        LedgerEntry.objects.create(
            transaction=tx,
            account=from_account,
            currency=currency,
            amount_minor=-amount_minor,
        )
        LedgerEntry.objects.create(
            transaction=tx,
            account=to_account,
            currency=currency,
            amount_minor=amount_minor,
        )


def bal(account_code: str, *, currency: str | None = None) -> int:
    account = Account.objects.get(code=account_code)

    qs = LedgerEntry.objects.filter(account=account)
    if currency:
        qs = qs.filter(currency=currency.upper())

    result = qs.aggregate(total=Sum("amount_minor"))["total"]
    return result or 0
