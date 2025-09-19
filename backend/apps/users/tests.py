from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .serializers import ProfileSerializer


class ProfileSerializerTest(TestCase):
    def test_wallet_fields_serialized(self):
        User = get_user_model()
        user = User.objects.create_user(username="wallet_tester", password="StrongPass!1")
        profile = user.profile
        profile.telegram_stars_balance = 125
        profile.telegram_stars_rate_rub = Decimal("7.50")
        profile.calocoin_balance = Decimal("1250.00")
        profile.calocoin_rate_rub = Decimal("3.20")
        profile.save(update_fields=[
            "telegram_stars_balance",
            "telegram_stars_rate_rub",
            "calocoin_balance",
            "calocoin_rate_rub",
        ])

        data = ProfileSerializer(profile).data

        self.assertEqual(data["telegram_stars_balance"], 125)
        self.assertEqual(data["telegram_stars_rate_rub"], "7.50")
        self.assertEqual(data["calocoin_balance"], "1250.00")
        self.assertEqual(data["calocoin_rate_rub"], "3.20")
