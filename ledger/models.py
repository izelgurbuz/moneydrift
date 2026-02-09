import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum


class Account(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(
        max_length=64, unique=True
    )  # e.g. "revenue", "stripe_clearing"
    name = models.CharField(max_length=128)  # e.g. "Revenue"

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ledger_account"

    def __str__(self) -> str:
        return self.code


class LedgerTransaction(models.Model):
    """
    Groups multiple ledger entries that were created
    because of the same real-world intent.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(
        max_length=200,
        unique=True,
        help_text="External reference, e.g. Stripe event id",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ledger_transaction"

    def __str__(self) -> str:
        return self.reference

    def assert_balanced(self) -> None:
        total = LedgerEntry.objects.filter(transaction=self).aggregate(
            total=Sum("amount_minor")
        )["total"]
        if total != 0:
            raise ValidationError(
                f"LedgerTransaction {self.id} is unbalanced: sum={total}"
            )


class LedgerEntry(models.Model):
    """
    Append-only record of a money movement affecting one account
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="entries"
    )
    transaction = models.ForeignKey(
        LedgerTransaction,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    currency = models.CharField(max_length=3)
    amount_minor = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ledger_entry"
        indexes = [
            models.Index(fields=["account", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.account.code} {self.currency} {self.amount_minor}"
