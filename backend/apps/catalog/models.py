from django.db import models


class Restaurant(models.Model):
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["city", "is_active"], name="cat_rest_city_active_idx"),
        ]

    def __str__(self): return self.name


class Store(models.Model):
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["city", "is_active"], name="cat_store_city_active_idx"),
        ]

    def __str__(self): return self.name


class Nutrients(models.Model):
    calories = models.FloatField()
    protein = models.FloatField()
    fat = models.FloatField()
    carbs = models.FloatField()
    fiber = models.FloatField(default=0)
    sodium = models.FloatField(default=0)


class MenuItem(models.Model):
    SOURCE_CHOICES = [("restaurant", "restaurant"), ("store", "store")]
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES)
    source_id = models.PositiveIntegerField()
    external_id = models.CharField(max_length=64, null=True, blank=True, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    tags = models.JSONField(default=list)
    allergens = models.JSONField(default=list)
    exclusions = models.JSONField(default=list)
    nutrients = models.OneToOneField(Nutrients, on_delete=models.CASCADE, related_name="item")

    class Meta:
        indexes = [
            models.Index(fields=["source", "source_id", "is_available"], name="cat_menuitem_source_idx"),
            models.Index(fields=["is_available", "price"], name="cat_menuitem_avail_price_idx"),
            models.Index(fields=["tags"], name="cat_menuitem_tags_idx"),
            models.Index(fields=["allergens"], name="cat_menuitem_allergens_idx"),
            models.Index(fields=["exclusions"], name="cat_menuitem_exclusions_idx"),
        ]


    def __str__(self): return self.title
