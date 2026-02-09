from django.core.management.base import BaseCommand

from integrations.stripe_client import list_balance_transactions
from integrations.stripe_ingest import ingest_balance_tx


class Command(BaseCommand):
    help = "Sync Stripe balance transactions into ledger"

    def handle(self, *args, **options):
        txs = list_balance_transactions(limit=100)
        count = 0
        for bt in txs.auto_paging_iter():
            ingest_balance_tx(bt)
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Ingested {count} Stripe transactions"))
