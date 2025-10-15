from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.users.mtproto import TelegramMTProtoClient
from apps.users.services.stars_reconcile import StarsReconciliationService


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

        api_id = getattr(settings, "TELEGRAM_MT_API_ID", 0)
        api_hash = getattr(settings, "TELEGRAM_MT_API_HASH", "")
        if not api_id or not api_hash:
            raise CommandError("TELEGRAM_MT_API_ID and TELEGRAM_MT_API_HASH must be configured")

        session = getattr(settings, "TELEGRAM_MT_SESSION", "") or None
        bot_token = getattr(settings, "TELEGRAM_MT_BOT_TOKEN", "") or None
        test_mode = getattr(settings, "TELEGRAM_MT_TEST_MODE", False)

        limit = int(options.get("limit") or 200)

        with TelegramMTProtoClient(
            api_id=api_id,
            api_hash=api_hash,
            session=session,
            bot_token=bot_token,
            test_mode=test_mode,
        ) as client:
            service = StarsReconciliationService(client)
            summary = service.reconcile(limit=limit)

        self.stdout.write(
            self.style.SUCCESS(
                f"Checked {summary.checked_transactions} transactions. "
                f"Remote balance={summary.remote_balance}, "
                f"ledger balance={summary.ledger_balance}, "
                f"bot balance={summary.bot_balance}."
            )
        )
        if summary.has_discrepancies:
            self.stdout.write(
                self.style.WARNING(
                    f"Detected {len(summary.mismatches)} mismatches. Notifications were sent."
                )
            )