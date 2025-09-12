from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id","username","email","first_name","last_name")

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = (
            "id","user",
            "telegram_id","city",
            "sex","birth_date",
            "height_cm","weight_kg","body_fat_pct",
            "activity_level","goal",
            "allergies","exclusions",
            "daily_budget",
            "created_at","updated_at",
        )
