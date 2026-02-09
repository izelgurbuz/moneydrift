from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from ledger.models import LedgerTransaction


class Command(BaseCommand):
    help = "Checks ledger invariants for all transactions."

    def handle(self, *args, **options):
        errors = 0
        checked = 0

        for tx in LedgerTransaction.objects.all():
            checked += 1
            try:
                tx.assert_balanced()
            except ValidationError as e:
                errors += 1
                self.stderr.write(
                    f"❌ Invariant violation for transaction {tx.id}: {e}"
                )

        if errors:
            raise SystemExit(
                f"Ledger integrity check failed: {errors} invalid transactions out of {checked}"
            )

        self.stdout.write(
            self.style.SUCCESS(f"Ledger integrity OK ({checked} transactions checked)")
        )
