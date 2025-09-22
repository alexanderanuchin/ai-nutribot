from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .serializers import ProfileSerializer, ProfileUpdateSerializer



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


class ProfileUpdateSerializerTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="+79990000000",
            password="StrongPass!1",
            email="old@example.com",
            first_name="Old",
            last_name="Name",
        )
        self.profile = self.user.profile

    def test_updates_user_and_profile_fields(self):
        data = {
            "first_name": "Александр",
            "last_name": "Анучин",
            "middle_name": "Михайлович",
            "experience_level": "pro",
            "email": "alexander@example.com",
            "phone": "+7 (999) 123-45-67",
            "password": "SuperPass!9",
        }

        serializer = ProfileUpdateSerializer(self.profile, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_profile = serializer.save()

        self.user.refresh_from_db()
        updated_profile.refresh_from_db()

        self.assertEqual(self.user.first_name, "Александр")
        self.assertEqual(self.user.last_name, "Анучин")
        self.assertEqual(self.user.email, "alexander@example.com")
        self.assertEqual(self.user.username, "+79991234567")
        self.assertTrue(self.user.check_password("SuperPass!9"))
        self.assertEqual(updated_profile.middle_name, "Михайлович")
        self.assertEqual(updated_profile.experience_level, "pro")

    def test_phone_must_be_unique(self):
        other = self.User.objects.create_user(
            username="+79990000001",
            password="StrongPass!2",
        )
        other.profile

        data = {"phone": "+7 (999) 000-00-01"}
        serializer = ProfileUpdateSerializer(self.profile, data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("phone", serializer.errors)