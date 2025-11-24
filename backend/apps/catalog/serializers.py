from rest_framework import serializers
from .models import MenuItem, Nutrients


class NutrientsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nutrients
        fields = "__all__"


class MenuItemSerializer(serializers.ModelSerializer):
    nutrients = NutrientsSerializer(allow_null=True, required=False)

    class Meta:
        model = MenuItem
        fields = "__all__"
