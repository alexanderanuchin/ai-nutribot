from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.feed.models import DealOffer, FeedTag, NewsArticle, Recipe, RecipeStep

User = get_user_model()


@pytest.fixture(autouse=True)
def _configure_bot_token(settings):
    settings.TELEGRAM_BOT_TOKEN = "test-token"


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(username='+79000000000', email='feed@example.com', password='test-pass-1')


@pytest.fixture
def auth_client(api_client: APIClient, user: User) -> APIClient:
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
def test_feed_returns_news(auth_client: APIClient):
    tag = FeedTag.objects.create(name='Wellness', slug='wellness', kind=FeedTag.Kind.NEWS)
    article = NewsArticle.objects.create(
        source_id='ext-1',
        title='Суперфуды в 2025',
        lead='Эксперты рассказали о лучших суперфудах года',
        source_name='Health News',
        source_url='https://example.com/health',
        published_at=timezone.now(),
    )
    article.tags.add(tag)

    response = auth_client.get('/api/v1/feed/', {'type': 'news'})
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload['results'][0]['title'] == 'Суперфуды в 2025'
    assert payload['results'][0]['tags'][0]['slug'] == 'wellness'


@pytest.mark.django_db
def test_feed_filters_recipes(auth_client: APIClient, user: User):
    Recipe.objects.create(
        author=user,
        status=Recipe.Status.PUBLISHED,
        title='Фитнес боул',
        slug='fit-bowl',
        short_description='Яркий боул для зарядки энергии',
        description='Полезный боул с крупами и овощами.',
        hero_image='https://cdn.example.com/bowl.jpg',
        gallery=[],
        cook_time_minutes=15,
        calories=Decimal('340.0'),
        protein=Decimal('25.0'),
        fat=Decimal('12.0'),
        carbs=Decimal('40.0'),
        allergens=['nuts'],
        diet_tags=['vegan'],
        base_content='Бесплатная версия рецепта',
        premium_content='',
        is_premium=False,
        price=Decimal('0'),
        rating=Decimal('4.8'),
        rating_count=8,
        purchases_count=0,
    )
    premium_recipe = Recipe.objects.create(
        author=user,
        status=Recipe.Status.PUBLISHED,
        title='Премиум шейк',
        slug='premium-shake',
        short_description='Шейк с высоким содержанием белка',
        description='Вкусный и насыщенный протеиновый шейк.',
        hero_image='https://cdn.example.com/shake.jpg',
        gallery=[],
        cook_time_minutes=5,
        calories=Decimal('210.0'),
        protein=Decimal('32.0'),
        fat=Decimal('6.0'),
        carbs=Decimal('14.0'),
        allergens=[],
        diet_tags=['sport'],
        base_content='Бесплатные советы',
        premium_content='Полный план приготовления и видео.',
        is_premium=True,
        price=Decimal('199.00'),
        rating=Decimal('4.9'),
        rating_count=42,
        purchases_count=12,
    )
    RecipeStep.objects.create(recipe=premium_recipe, order=1, text='Смешайте ингредиенты', media_url='')

    response = auth_client.get('/api/v1/feed/', {'type': 'recipes', 'price_min': '1'})
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert len(payload['results']) == 1
    assert payload['results'][0]['slug'] == 'premium-shake'
    assert payload['results'][0]['is_premium'] is True


@pytest.mark.django_db
def test_feed_returns_deals_filtered_by_city(auth_client: APIClient):
    tag = FeedTag.objects.create(name='Органик', slug='organic', kind=FeedTag.Kind.DEAL)
    offer = DealOffer.objects.create(
        external_id='deal-1',
        title='Скидка на киноа',
        product_name='Киноа 500г',
        network='GreenMarket',
        city='Москва',
        address='ул. Примерная, 1',
        is_online=False,
        price_before=Decimal('399.00'),
        price_after=Decimal('299.00'),
        discount_percent=Decimal('25.00'),
        valid_until=timezone.now() + timedelta(days=5),
    )
    offer.tags.add(tag)

    response = auth_client.get('/api/v1/feed/', {'type': 'deals', 'city': 'Москва'})
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload['results'][0]['title'] == 'Скидка на киноа'
    assert payload['results'][0]['tags'][0]['slug'] == 'organic'


@pytest.mark.django_db
def test_recipe_purchase_flow(auth_client: APIClient, user: User):
    recipe = Recipe.objects.create(
        author=user,
        status=Recipe.Status.PUBLISHED,
        title='Премиум каша',
        slug='premium-porridge',
        short_description='Тёплая каша с ягодами',
        description='Полезный завтрак для продуктивного дня.',
        hero_image='',
        gallery=[],
        cook_time_minutes=10,
        calories=Decimal('320.0'),
        protein=Decimal('18.0'),
        fat=Decimal('9.0'),
        carbs=Decimal('45.0'),
        allergens=[],
        diet_tags=['sport'],
        base_content='Основные шаги приготовления',
        premium_content='Детальный план питания и видеоуроки',
        is_premium=True,
        price=Decimal('159.00'),
        rating=Decimal('4.6'),
        rating_count=12,
        purchases_count=0,
    )

    response = auth_client.post(f'/api/v1/recipes/{recipe.id}/purchase/')
    assert response.status_code == status.HTTP_201_CREATED
    payload = response.json()
    assert payload['amount'] == '159.00'
    recipe.refresh_from_db()
    assert recipe.purchases_count == 1


@pytest.mark.django_db
def test_ingest_requires_integration_key(api_client: APIClient, settings):
    settings.BOT_INTERNAL_KEY = 'secret-key'
    response = api_client.post(
        '/api/v1/feed/news/ingest/',
        {
            'source_id': 'ext-10',
            'title': 'Новое исследование о витаминах',
            'lead': 'Учёные подтвердили пользу витамина D',
            'source_name': 'Science Daily',
            'source_url': 'https://example.com/article',
            'published_at': timezone.now().isoformat(),
        },
        format='json',
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    ok_response = api_client.post(
        '/api/v1/feed/news/ingest/',
        {
            'source_id': 'ext-10',
            'title': 'Новое исследование о витаминах',
            'lead': 'Учёные подтвердили пользу витамина D',
            'source_name': 'Science Daily',
            'source_url': 'https://example.com/article',
            'published_at': timezone.now().isoformat(),
        },
        format='json',
        HTTP_X_INTEGRATION_KEY='secret-key',
    )
    assert ok_response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_deal_ingest_parses_dates(api_client: APIClient, settings):
    settings.BOT_INTERNAL_KEY = 'integration-token'
    response = api_client.post(
        '/api/v1/feed/deals/ingest/',
        {
            'external_id': 'deal-2',
            'title': 'Скидка на миндальное молоко',
            'product_name': 'Миндальное молоко 1л',
            'network': 'EcoMart',
            'city': 'Санкт-Петербург',
            'price_before': '250.00',
            'price_after': '199.00',
            'discount_percent': '20.00',
            'valid_until': (timezone.now() + timedelta(days=3)).isoformat(),
        },
        format='json',
        HTTP_X_INTEGRATION_KEY='integration-token',
    )
    assert response.status_code == status.HTTP_201_CREATED
    offer = DealOffer.objects.get(external_id='deal-2')
    assert offer.city == 'Санкт-Петербург'