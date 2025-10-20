from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class FeedTag(TimeStampedModel):
    class Kind(models.TextChoices):
        GENERIC = "generic", "Generic"
        NEWS = "news", "News"
        RECIPE = "recipe", "Recipe"
        DEAL = "deal", "Deal"

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.GENERIC)

    class Meta:
        verbose_name = "Feed tag"
        verbose_name_plural = "Feed tags"
        ordering = ("name",)

    def __str__(self) -> str:  # pragma: no cover - debug convenience
        return self.name


class NewsArticle(TimeStampedModel):
    class Tonality(models.TextChoices):
        POSITIVE = "positive", "Positive"
        NEUTRAL = "neutral", "Neutral"
        NEGATIVE = "negative", "Negative"

    source_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=240)
    lead = models.TextField()
    source_name = models.CharField(max_length=120)
    source_url = models.URLField()
    published_at = models.DateTimeField(default=timezone.now, db_index=True)
    preview_image_url = models.URLField(blank=True)
    tonality = models.CharField(
        max_length=16,
        choices=Tonality.choices,
        default=Tonality.NEUTRAL,
        db_index=True,
    )
    source_categories = models.JSONField(default=list, blank=True)
    toxicity_score = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0"))
    clickbait_score = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0"))
    is_flagged = models.BooleanField(default=False)
    ingested_at = models.DateTimeField(null=True, blank=True, db_index=True)
    ingestion_source = models.CharField(max_length=64, blank=True)
    ingestion_rid = models.CharField(max_length=128, blank=True)
    ingestion_metadata = models.JSONField(default=dict, blank=True)

    tags = models.ManyToManyField(FeedTag, related_name="news_articles", blank=True)

    class Meta:
        verbose_name = "News article"
        verbose_name_plural = "News articles"
        ordering = ("-published_at", "-id")

    def __str__(self) -> str:  # pragma: no cover
        return self.title


class Recipe(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        MODERATION = "moderation", "Moderation"
        PUBLISHED = "published", "Published"
        HIDDEN = "hidden", "Hidden"

    class Difficulty(models.TextChoices):
        EASY = "easy", "Легко"
        MEDIUM = "medium", "Средне"
        HARD = "hard", "Сложно"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recipes")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    short_description = models.CharField(max_length=280)
    description = models.TextField(blank=True)
    hero_image = models.URLField(blank=True)
    gallery = models.JSONField(default=list, blank=True)
    cook_time_minutes = models.PositiveSmallIntegerField(default=15)
    difficulty = models.CharField(max_length=16, choices=Difficulty.choices, default=Difficulty.EASY)
    calories = models.DecimalField(max_digits=6, decimal_places=1, validators=[MinValueValidator(Decimal("0"))])
    protein = models.DecimalField(max_digits=6, decimal_places=1, validators=[MinValueValidator(Decimal("0"))])
    fat = models.DecimalField(max_digits=6, decimal_places=1, validators=[MinValueValidator(Decimal("0"))])
    carbs = models.DecimalField(max_digits=6, decimal_places=1, validators=[MinValueValidator(Decimal("0"))])
    allergens = models.JSONField(default=list, blank=True)
    diet_tags = models.JSONField(default=list, blank=True)
    base_content = models.TextField()
    premium_content = models.TextField(blank=True)
    is_premium = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0"))],
                                default=Decimal("0"))
    currency = models.CharField(max_length=3, default="RUB")
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0"))
    rating_count = models.PositiveIntegerField(default=0)
    purchases_count = models.PositiveIntegerField(default=0)

    tags = models.ManyToManyField(FeedTag, related_name="recipes", blank=True)

    class Meta:
        verbose_name = "Recipe"
        verbose_name_plural = "Recipes"
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:  # pragma: no cover
        return self.title


class RecipeStep(TimeStampedModel):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveSmallIntegerField(default=1)
    text = models.TextField()
    media_url = models.URLField(blank=True)

    class Meta:
        ordering = ("order", "id")
        unique_together = ("recipe", "order")


class RecipeReaction(TimeStampedModel):
    class Kind(models.TextChoices):
        LIKE = "like", "Лайк"
        SAVE = "save", "Сохранить"
        FIRE = "fire", "Огонь"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="reactions")
    kind = models.CharField(max_length=16, choices=Kind.choices)

    class Meta:
        unique_together = ("user", "recipe", "kind")
        indexes = [
            models.Index(fields=["recipe", "kind"], name="feed_reaction_recipe_kind"),
        ]


class RecipePurchase(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        COMPLETED = "completed", "Завершено"
        REFUNDED = "refunded", "Возврат"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recipe_purchases")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="purchases")
    amount = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    currency = models.CharField(max_length=3, default="RUB")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=64, default="test")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("user", "recipe")
        ordering = ("-created_at",)


class DealOffer(TimeStampedModel):
    external_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=160)
    product_name = models.CharField(max_length=160)
    network = models.CharField(max_length=120)
    city = models.CharField(max_length=120)
    address = models.CharField(max_length=255, blank=True)
    is_online = models.BooleanField(default=False)
    price_before = models.DecimalField(max_digits=8, decimal_places=2)
    price_after = models.DecimalField(max_digits=8, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    valid_until = models.DateTimeField()
    offer_url = models.URLField(blank=True)
    image_url = models.URLField(blank=True)

    tags = models.ManyToManyField(FeedTag, related_name="deal_offers", blank=True)

    class Meta:
        verbose_name = "Deal offer"
        verbose_name_plural = "Deal offers"
        ordering = ("-valid_until", "-id")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.product_name} — {self.network}"
