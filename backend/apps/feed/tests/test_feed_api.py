from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.feed.models import DealOffer, FeedTag, NewsArticle, Recipe, RecipeStep
from apps.feed.services.translation import TranslationOutcome

User = get_user_model()


@pytest.fixture(autouse=True)
def _configure_bot_token(settings):
    settings.TELEGRAM_BOT_TOKEN = "test-token"


@pytest.fixture(autouse=True)
def _disable_db_logging(monkeypatch):
    monkeypatch.setattr('apps.monitoring.handlers.DatabaseLogHandler.emit', lambda self, record: None)


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
        body='Полный текст статьи',
        source_name='Health News',
        source_url='https://example.com/health',
        published_at=timezone.now(),
        lang='ru',
        tonality=NewsArticle.Tonality.POSITIVE,
        source_categories=['wellness'],
    )
    article.tags.add(tag)

    response = auth_client.get('/api/v1/feed/', {'type': 'news'})
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload['results'][0]['title'] == 'Суперфуды в 2025'
    assert payload['results'][0]['tags'][0]['slug'] == 'wellness'
    assert payload['results'][0]['tonality'] == NewsArticle.Tonality.POSITIVE
    assert payload['results'][0]['published_at_msk']
    assert payload['results'][0]['published_at'].endswith('+03:00')
    assert payload['results'][0]['timezone_label'] == 'MSK'
    assert payload['results'][0]['lang'] == 'ru'
    assert 'published_at_localized' in payload['results'][0]


@pytest.mark.django_db
def test_feed_filters_news_by_moderation(auth_client: APIClient):
    clean = NewsArticle.objects.create(
        source_id='ext-clean',
        title='Чистая новость',
        lead='Никаких флагов',
        source_name='Health',
        source_url='https://example.com/clean',
        published_at=timezone.now(),
        is_flagged=False,
        toxicity_score=Decimal('0.1000'),
        clickbait_score=Decimal('0.2000'),
    )
    flagged = NewsArticle.objects.create(
        source_id='ext-flagged',
        title='Фейковая сенсация',
        lead='Содержит преувеличения',
        source_name='Viral',
        source_url='https://example.com/flagged',
        published_at=timezone.now(),
        is_flagged=True,
        toxicity_score=Decimal('0.7500'),
        clickbait_score=Decimal('0.8800'),
    )

    response = auth_client.get('/api/v1/feed/', {'type': 'news', 'is_flagged': '1'})
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert len(payload['results']) == 1
    assert payload['results'][0]['id'] == flagged.id

    response_any = auth_client.get('/api/v1/feed/', {'type': 'news', 'is_flagged': 'any'})
    assert response_any.status_code == status.HTTP_200_OK
    results = response_any.json()['results']
    assert {item['id'] for item in results} == {clean.id, flagged.id}


@pytest.mark.django_db
def test_feed_filters_news_by_scores(auth_client: APIClient):
    NewsArticle.objects.create(
        source_id='ext-low',
        title='Спокойная аналитика',
        lead='Рассказ без кликов',
        source_name='Wellness',
        source_url='https://example.com/low',
        published_at=timezone.now(),
        toxicity_score=Decimal('0.1200'),
        clickbait_score=Decimal('0.1500'),
        tonality=NewsArticle.Tonality.NEUTRAL,
        source_categories=['analysis'],
    )
    NewsArticle.objects.create(
        source_id='ext-high',
        title='Громкие заголовки',
        lead='Очень кликбейтная новость',
        source_name='Buzz',
        source_url='https://example.com/high',
        published_at=timezone.now(),
        toxicity_score=Decimal('0.8200'),
        clickbait_score=Decimal('0.9100'),
        tonality=NewsArticle.Tonality.NEGATIVE,
        source_categories=['buzz'],
    )

    response = auth_client.get(
        '/api/v1/feed/',
        {
            'type': 'news',
            'tonality': NewsArticle.Tonality.NEUTRAL,
            'toxicity_max': '0.3',
            'clickbait_max': '0.3',
            'categories': 'analysis',
        },
    )
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert len(payload['results']) == 1
    assert payload['results'][0]['source_id'] == 'ext-low'


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
def test_ingest_requires_integration_key(api_client: APIClient, settings, db):
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
def test_news_ingest_creates_article_with_tags_and_metadata(api_client: APIClient, settings, monkeypatch, db):
    settings.BOT_INTERNAL_KEY = 'secret-key'
    captured: dict[str, object] = {}

    def _capture_event(article, action, rid=None):
        captured['action'] = action
        captured['article_id'] = article.id
        captured['rid'] = rid

    monkeypatch.setattr('apps.feed.views.publish_news_article_event', _capture_event)
    published_at = timezone.now()
    response = api_client.post(
        '/api/v1/feed/news/ingest/',
        {
            'source_id': 'ext-42',
            'title': 'Питательные привычки',
            'lead': 'Эксперты рассказали о новом подходе к питанию',
            'source_name': 'NutriDaily',
            'source_url': 'https://example.com/nutri',
            'preview_image_url': 'https://cdn.example.com/image.jpg',
            'published_at': published_at.isoformat(),
            'tonality': NewsArticle.Tonality.POSITIVE,
            'source_categories': ['health', 'nutrition'],
            'toxicity_score': '0.0123',
            'clickbait_score': '0.1000',
            'ingestion_source': 'partner-api',
            'ingestion_metadata': {'batch': 'b-1'},
            'tags': [
                'wellness',
                {'slug': 'vitamins', 'name': 'Vitamins', 'children': [{'slug': 'vitamin-d'}]},
            ],
        },
        format='json',
        HTTP_X_INTEGRATION_KEY='secret-key',
    )

    assert response.status_code == status.HTTP_201_CREATED
    article = NewsArticle.objects.get(source_id='ext-42')
    assert article.tonality == NewsArticle.Tonality.POSITIVE
    assert article.source_categories == ['health', 'nutrition']
    assert article.ingestion_source == 'partner-api'
    assert article.ingestion_metadata['batch'] == 'b-1'
    assert article.ingestion_rid == captured['rid']
    assert captured['action'] == 'created'
    slugs = sorted(article.tags.values_list('slug', flat=True))
    assert slugs == ['vitamin-d', 'vitamins', 'wellness']


@pytest.mark.django_db
def test_news_ingest_updates_existing_article(api_client: APIClient, settings, monkeypatch, db):
    settings.BOT_INTERNAL_KEY = 'secret-key'
    article = NewsArticle.objects.create(
        source_id='ext-43',
        title='Старый заголовок',
        lead='Старый лид',
        source_name='Old Source',
        source_url='https://example.com/old',
        published_at=timezone.now(),
        tonality=NewsArticle.Tonality.NEUTRAL,
        ingestion_metadata={'source': 'legacy'},
    )

    captured: dict[str, object] = {}

    def _capture_event(article, action, rid=None):
        captured['action'] = action
        captured['article_id'] = article.id

    monkeypatch.setattr('apps.feed.views.publish_news_article_event', _capture_event)
    response = api_client.post(
        '/api/v1/feed/news/ingest/',
        {
            'source_id': 'ext-43',
            'title': 'Обновлённый заголовок',
            'lead': 'Обновлённый лид',
            'source_name': 'Nutri Update',
            'source_url': 'https://example.com/new',
            'tonality': NewsArticle.Tonality.NEGATIVE,
            'ingestion_metadata': {'batch': 'b-2'},
            'tags': [{'slug': 'analysis', 'name': 'Analysis'}],
        },
        format='json',
        HTTP_X_INTEGRATION_KEY='secret-key',
    )

    assert response.status_code == status.HTTP_200_OK
    article.refresh_from_db()
    assert article.title == 'Обновлённый заголовок'
    assert article.tonality == NewsArticle.Tonality.NEGATIVE
    assert article.ingestion_metadata == {'source': 'legacy', 'batch': 'b-2'}
    assert captured['action'] == 'updated'
    assert list(article.tags.values_list('slug', flat=True)) == ['analysis']


@pytest.mark.django_db
def test_news_ingest_applies_server_translation(api_client: APIClient, settings, monkeypatch, db):
    settings.BOT_INTERNAL_KEY = 'secret-key'
    settings.FEED_TRANSLATE_RU_ENABLED = True
    settings.TRANSLATE_TARGET_LANG = 'ru'
    settings.TRANSLATE_PROVIDERS = ('yandex',)

    monkeypatch.setenv('FEED_TRANSLATE_RU_ENABLED', '1')
    monkeypatch.setenv('TRANSLATE_TARGET_LANG', 'ru')
    monkeypatch.setenv('YANDEX_API_KEY', 'dummy')
    monkeypatch.setenv('YANDEX_FOLDER_ID', 'folder')
    monkeypatch.setattr('apps.feed.services.translation._translation_service', None, raising=False)

    class DummyTranslationService:
        is_available = True

        def translate_texts(self, texts, *, source_lang, target_lang, rid=None):
            return TranslationOutcome(
                texts=[f'ru::{text}' if text else text for text in texts],
                provider='yandex',
                source_lang=source_lang or 'en',
            )

    dummy_service = DummyTranslationService()
    monkeypatch.setattr('apps.feed.services.ingest_pipeline.get_translation_service', lambda: dummy_service)

    response = api_client.post(
        '/api/v1/feed/news/ingest/',
        {
            'source_id': 'ext-ru-1',
            'title': 'Protein improves recovery',
            'lead': 'Experts share daily dosage insights',
            'body': 'Full article content',
            'source_name': 'Health Weekly',
            'source_url': 'https://example.com/health',
            'published_at': timezone.now().isoformat(),
        },
        format='json',
        HTTP_X_INTEGRATION_KEY='secret-key',
    )

    assert response.status_code == status.HTTP_201_CREATED
    article = NewsArticle.objects.get(source_id='ext-ru-1')
    assert article.title == 'ru::Protein improves recovery'
    assert article.lead == 'ru::Experts share daily dosage insights'
    assert article.body == 'ru::Full article content'
    assert article.title_orig == 'Protein improves recovery'
    assert article.lead_orig == 'Experts share daily dosage insights'
    assert article.body_orig == 'Full article content'
    assert article.translated is True
    assert article.translation_provider == 'yandex'


@pytest.mark.django_db
def test_news_ingest_returns_validation_errors(api_client: APIClient, settings, db):
    settings.BOT_INTERNAL_KEY = 'secret-key'
    response = api_client.post(
        '/api/v1/feed/news/ingest/',
        {
            'title': 'Нет идентификатора',
            'lead': 'Пустой source_id',
        },
        format='json',
        HTTP_X_INTEGRATION_KEY='secret-key',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    errors = response.json()
    assert 'source_id' in errors


@pytest.mark.django_db
def test_deal_ingest_parses_dates(api_client: APIClient, settings, db):
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


@pytest.mark.django_db
def test_news_detail_returns_full_article(auth_client: APIClient):
    article = NewsArticle.objects.create(
        source_id='detail-1',
        title='Полный обзор исследований',
        lead='Ключевые выводы исследований питания',
        body='<p>HTML content</p>',
        title_orig='Full research overview',
        lead_orig='Key findings',
        body_orig='<p>Original HTML</p>',
        lang='ru',
        translated=True,
        translation_provider='test-provider',
        source_name='Nutri Journal',
        source_url='https://example.com/journal',
        published_at=timezone.now(),
        tonality=NewsArticle.Tonality.NEUTRAL,
        source_categories=['science'],
        toxicity_score=Decimal('0.1000'),
        clickbait_score=Decimal('0.2000'),
        ingestion_rid='RID-DETAIL',
    )

    response = auth_client.get(f'/api/v1/feed/news/{article.id}/')

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload['id'] == article.id
    assert payload['body'] == '<p>HTML content</p>'
    assert payload['title_orig'] == 'Full research overview'
    assert payload['is_published'] is True
    assert payload['translation_provider'] == 'test-provider'
    assert payload['tonality'] == NewsArticle.Tonality.NEUTRAL


@pytest.mark.django_db
def test_news_detail_requires_published_article(auth_client: APIClient):
    article = NewsArticle.objects.create(
        source_id='detail-2',
        title='Черновик статьи',
        lead='Недоступно читателям',
        source_name='Draft Source',
        source_url='https://example.com/draft',
        published_at=timezone.now(),
        is_published=False,
    )

    response = auth_client.get(f'/api/v1/feed/news/{article.id}/')

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_news_detail_requires_authentication(api_client: APIClient):
    article = NewsArticle.objects.create(
        source_id='detail-3',
        title='Аутентификация обязательна',
        lead='',
        source_name='Nutri',
        source_url='https://example.com/protected',
        published_at=timezone.now(),
    )

    response = api_client.get(f'/api/v1/feed/news/{article.id}/')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED