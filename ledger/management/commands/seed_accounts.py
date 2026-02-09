from django.core.management.base import BaseCommand
from django.db import transaction

from ledger.models import Account

SYSTEM_ACCOUNTS = [
    ("revenue", "Revenue"),
    ("stripe_clearing", "Stripe Clearing"),
    ("bank", "Bank"),
    ("fees", "Fees"),
    ("external", "External / Unattributed"),
]


class Command(BaseCommand):
    help = "Create system ledger accounts (idempotent)."

    def handle(self, *args, **options):
        created = 0
        updated = 0

        with transaction.atomic():
            for code, name in SYSTEM_ACCOUNTS:
                obj, is_created = Account.objects.update_or_create(
                    code=code, defaults={"name": name}
                )
                if is_created:
                    created += 1
                else:
                    updated += 1
        self.stdout.write(
            self.style.SUCCESS(f"seed_accounts: created={created}, updated={updated}")
        )
