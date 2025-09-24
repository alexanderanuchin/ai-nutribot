from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.users.models import Profile
from apps.users.serializers import ProfileSerializer, ProfileUpdateSerializer




class ProfileSerializerTest(TestCase):
    def test_wallet_fields_serialized(self):
        User = get_user_model()
        user = User.objects.create_user(username="wallet_tester", password="StrongPass!1")
        profile = user.profile
        profile.city = "Москва"
        profile.telegram_stars_balance = 125
        profile.telegram_stars_rate_rub = Decimal("7.50")
        profile.calocoin_balance = Decimal("1250.00")
        profile.calocoin_rate_rub = Decimal("3.20")
        profile.daily_budget = Decimal("1500.50")
        profile.experience_level = Profile.ExperienceLevel.LEGEND
        profile.save(update_fields=[
            "city",
            "telegram_stars_balance",
            "telegram_stars_rate_rub",
            "calocoin_balance",
            "calocoin_rate_rub",
            "daily_budget",
            "experience_level",
        ])

        data = ProfileSerializer(profile).data

        self.assertEqual(data["city"], "Москва")
        self.assertEqual(data["telegram_stars_balance"], 125)
        self.assertEqual(data["telegram_stars_rate_rub"], "7.50")
        self.assertEqual(data["calocoin_balance"], "1250.00")
        self.assertEqual(data["calocoin_rate_rub"], "3.20")
        self.assertEqual(data["daily_budget"], "1500.50")
        self.assertEqual(data["experience_level"], Profile.ExperienceLevel.LEGEND)
        self.assertEqual(data["experience_level_display"], Profile.ExperienceLevel.LEGEND.label)

    def test_metrics_calculated(self):
        User = get_user_model()
        user = User.objects.create_user(username="metrics_user", password="StrongPass!1")
        profile = user.profile

        today = date.today()
        day = today.day
        if today.month == 2 and day == 29:
            day = 28
        birth_date = date(today.year - 30, today.month, day)

        profile.birth_date = birth_date
        profile.sex = "m"
        profile.height_cm = 180
        profile.weight_kg = Decimal("82.5")
        profile.activity_level = "moderate"
        profile.goal = "lose"
        profile.save(
            update_fields=[
                "birth_date",
                "sex",
                "height_cm",
                "weight_kg",
                "activity_level",
                "goal",
            ]
        )

        data = ProfileSerializer(profile).data
        metrics = data["metrics"]

        self.assertEqual(metrics["age"], 30)
        self.assertEqual(metrics["age_display"], "30 лет")
        self.assertEqual(metrics["bmi"], 25.5)
        self.assertEqual(metrics["bmi_status"], "Избыточная масса")
        self.assertEqual(metrics["bmr"], 1887)
        self.assertEqual(metrics["tdee"], 2925)
        self.assertEqual(metrics["recommended_calories"], 2475)
        self.assertEqual(
            metrics["macros"],
            [
                {"label": "Белки", "grams": 198, "ratio": 0.32},
                {"label": "Жиры", "grams": 74, "ratio": 0.27},
                {"label": "Углеводы", "grams": 254, "ratio": 0.41},
            ],
        )


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
            "city": "Санкт-Петербург",
            "daily_budget": "2100.40",
            "telegram_stars_balance": 312,
            "telegram_stars_rate_rub": "6.45",
            "calocoin_balance": "1500.00",
            "calocoin_rate_rub": "4.15",
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
        self.assertEqual(updated_profile.city, "Санкт-Петербург")
        self.assertEqual(updated_profile.daily_budget, Decimal("2100.40"))
        self.assertEqual(updated_profile.telegram_stars_balance, 312)
        self.assertEqual(updated_profile.telegram_stars_rate_rub, Decimal("6.45"))
        self.assertEqual(updated_profile.calocoin_balance, Decimal("1500.00"))
        self.assertEqual(updated_profile.calocoin_rate_rub, Decimal("4.15"))

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

    def test_email_must_be_unique(self):
        self.User.objects.create_user(
            username="+79990000002",
            password="StrongPass!3",
            email="existing@example.com",
        )

        data = {"email": "existing@example.com"}
        serializer = ProfileUpdateSerializer(self.profile, data=data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    class MeProfileAPITest(TestCase):
        def setUp(self):
            super().setUp()
            self.client = APIClient()
            self.User = get_user_model()
            self.user = self.User.objects.create_user(
                username="+79990000000",
                password="StrongPass!1",
                email="old@example.com",
                first_name="Old",
                last_name="Name",
            )
            self.profile = self.user.profile
            self.client.force_authenticate(user=self.user)

        def test_me_profile_returns_full_wallet_payload(self):
            self.profile.city = "Москва"
            self.profile.daily_budget = Decimal("1350.50")
            self.profile.telegram_stars_balance = 88
            self.profile.telegram_stars_rate_rub = Decimal("5.15")
            self.profile.calocoin_balance = Decimal("120.00")
            self.profile.calocoin_rate_rub = Decimal("2.50")
            self.profile.experience_level = Profile.ExperienceLevel.PRO
            self.profile.save()

            resp = self.client.get("/api/users/me/profile/")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()

            self.assertEqual(data["city"], "Москва")
            self.assertEqual(data["daily_budget"], "1350.50")
            self.assertEqual(data["telegram_stars_balance"], 88)
            self.assertEqual(data["telegram_stars_rate_rub"], "5.15")
            self.assertEqual(data["calocoin_balance"], "120.00")
            self.assertEqual(data["calocoin_rate_rub"], "2.50")
            self.assertEqual(data["experience_level"], Profile.ExperienceLevel.PRO)
            self.assertEqual(data["experience_level_display"], Profile.ExperienceLevel.PRO.label)
            self.assertIn("user", data)
            self.assertEqual(data["user"]["email"], "old@example.com")

        def test_me_profile_patch_updates_contact_and_wallet_fields(self):
            payload = {
                "first_name": "Ирина",
                "last_name": "Новая",
                "email": "irina@example.com",
                "phone": "+7 (912) 000-00-02",
                "password": "NewStrong!2",
                "city": "Казань",
                "daily_budget": "1500.50",
                "telegram_stars_balance": 321,
                "telegram_stars_rate_rub": "5.75",
                "calocoin_balance": "2100.00",
                "calocoin_rate_rub": "3.40",
                "experience_level": Profile.ExperienceLevel.LEGEND,
            }

            resp = self.client.patch("/api/users/me/profile/update/", payload, format="json")

            self.assertEqual(resp.status_code, 200)
            data = resp.json()

            # contract matches GET representation
            self.assertIn("user", data)
            self.assertNotIn("first_name", data)
            self.assertNotIn("last_name", data)
            self.assertEqual(data["city"], "Казань")
            self.assertEqual(data["daily_budget"], "1500.50")
            self.assertEqual(data["telegram_stars_balance"], 321)
            self.assertEqual(data["telegram_stars_rate_rub"], "5.75")
            self.assertEqual(data["calocoin_balance"], "2100.00")
            self.assertEqual(data["calocoin_rate_rub"], "3.40")
            self.assertEqual(data["experience_level"], Profile.ExperienceLevel.LEGEND)
            self.assertEqual(data["experience_level_display"], Profile.ExperienceLevel.LEGEND.label)

            user_payload = data["user"]
            self.assertEqual(user_payload["first_name"], "Ирина")
            self.assertEqual(user_payload["last_name"], "Новая")
            self.assertEqual(user_payload["email"], "irina@example.com")
            self.assertEqual(user_payload["username"], "+79120000002")

            self.user.refresh_from_db()
            self.profile.refresh_from_db()

            self.assertEqual(self.user.first_name, "Ирина")
            self.assertEqual(self.user.last_name, "Новая")
            self.assertEqual(self.user.email, "irina@example.com")
            self.assertEqual(self.user.username, "+79120000002")
            self.assertTrue(self.user.check_password("NewStrong!2"))
            self.assertEqual(self.profile.city, "Казань")
            self.assertEqual(self.profile.daily_budget, Decimal("1500.50"))
            self.assertEqual(self.profile.telegram_stars_balance, 321)
            self.assertEqual(self.profile.telegram_stars_rate_rub, Decimal("5.75"))
            self.assertEqual(self.profile.calocoin_balance, Decimal("2100.00"))
            self.assertEqual(self.profile.calocoin_rate_rub, Decimal("3.40"))
            self.assertEqual(self.profile.experience_level, Profile.ExperienceLevel.LEGEND)

        def test_me_profile_patch_rejects_duplicate_phone(self):
            self.User.objects.create_user(
                username="+79990000003",
                password="StrongPass!3",
            )

            resp = self.client.patch(
                "/api/users/me/profile/update/",
                {"phone": "+7 (999) 000-00-03"},
                format="json",
            )

            self.assertEqual(resp.status_code, 400)
            self.assertIn("phone", resp.json())

        def test_me_profile_patch_rejects_duplicate_email(self):
            self.User.objects.create_user(
                username="+79990000004",
                password="StrongPass!4",
                email="existing@example.com",
            )

            resp = self.client.patch(
                "/api/users/me/profile/update/",
                {"email": "existing@example.com"},
                format="json",
            )

            self.assertEqual(resp.status_code, 400)
            self.assertIn("email", resp.json())