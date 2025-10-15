from django.conf import settings
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.users.mtproto import TelegramMTProtoClient
from apps.users.services.stars_metrics import StarsMetricsService


class Command(BaseCommand):
    help = "Fetch payments.getStarsRevenueStats and update Stars rate across profiles"

    def handle(self, *args, **options):
        api_id = getattr(settings, "TELEGRAM_MT_API_ID", 0)
        api_hash = getattr(settings, "TELEGRAM_MT_API_HASH", "")
        if not api_id or not api_hash:
            raise CommandError("TELEGRAM_MT_API_ID and TELEGRAM_MT_API_HASH must be configured")

        session = getattr(settings, "TELEGRAM_MT_SESSION", "") or None
        bot_token = getattr(settings, "TELEGRAM_MT_BOT_TOKEN", "") or None
        test_mode = getattr(settings, "TELEGRAM_MT_TEST_MODE", False)

        with TelegramMTProtoClient(
            api_id=api_id,
            api_hash=api_hash,
            session=session,
            bot_token=bot_token,
            test_mode=test_mode,
        ) as client:
            service = StarsMetricsService(client)
            result = service.sync()

        self.stdout.write(
            self.style.SUCCESS(
                f"Stars metrics updated. Rate: {result.rate_rub} RUB for {result.snapshot.stars_total} stars"
            )
        )
