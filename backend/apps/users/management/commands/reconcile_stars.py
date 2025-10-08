from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Reconcile Telegram Stars ledger with data from MTProto payments.getStarsTransactions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Maximum number of transactions to inspect per run",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "STARS_RECONCILE_ENABLED", False):
            self.stdout.write(
                self.style.WARNING(
                    "Reconciliation is disabled. Set STARS_RECONCILE_ENABLED=1 to enable this command."
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                "MTProto reconciliation is not implemented in this environment. "
                "Integrate with payments.getStarsTransactions to compare bot and ledger balances."
            )
        )
        self.stdout.write(self.style.SUCCESS("No changes were made."))