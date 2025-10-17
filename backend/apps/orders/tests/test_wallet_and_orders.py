import uuid
from decimal import Decimal
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.services import get_profile_stars_balance

from apps.orders.models import (
    DeliveryService,
    DeliveryWindow,
    IntegrationWebhookEvent,
    MealSubscription,
    Order,
    PaymentAttempt,
    SubscriptionPlan,
    WalletPerk,
    WalletTarget,
    WalletTransaction,
)
from apps.orders.services import BillingService, PaymentService
from apps.orders.services.payment import PaymentProviderError, TelegramStarsProvider
from apps.orders.services.telegram_invoice import TelegramInvoiceResult, TelegramStarsInvoiceError
from apps.orders.services.wallet import get_wallet_balance

User = get_user_model()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user() -> User:
    user = User.objects.create_user(
        username="+79990001122",
        email="wallet@example.com",
        password="StrongPass!1",
    )
    profile = user.profile
    if not profile.telegram_id:
        profile.telegram_id = 700000 + user.pk
        profile.save(update_fields=["telegram_id", "updated_at"])
    return user


@pytest.fixture(autouse=True)
def stub_invoice_service(monkeypatch, settings):
    settings.TELEGRAM_BOT_TOKEN = "test-token"

    class FakeInvoiceService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_wallet_topup_invoice(
                self,
                *,
                profile,
                amount_stars: int,
                comment,
                metadata,
                idempotency_key,
                request_id,
        ) -> TelegramInvoiceResult:
            return TelegramInvoiceResult(
                invoice_link="https://t.me/pay?start=stub",
                payload=f"uid={profile.telegram_id}",
                title="Пополнение баланса Stars",
                description=f"Быстрое пополнение на {amount_stars} XTR.",
                start_parameter="wallet",
            )

    monkeypatch.setattr(TelegramStarsProvider, "invoice_service_class", FakeInvoiceService)

    from apps.orders import views as orders_views

    orders_views.WalletTopUpView.payment_service = PaymentService()
    orders_views.TelegramStarsInvoiceView.payment_service = PaymentService()
    orders_views.TelegramBotPaymentReportView.payment_service = PaymentService()


@pytest.fixture
def auth_client(api_client: APIClient, user: User) -> APIClient:
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def payment_service() -> PaymentService:
    return PaymentService()


@pytest.mark.django_db
def test_wallet_topup_and_withdraw(auth_client: APIClient, user: User):
    headers = {"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex}
    resp = auth_client.post(
        "/api/orders/wallet/transactions/topup/",
        {"currency": "stars", "amount": "300", "description": "Пополнение тест"},
        format="json",
        **headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["direction"] == "in"
    assert data["currency"] == "stars"
    user.profile.refresh_from_db()
    assert get_profile_stars_balance(user.profile) == 300

    # повторный запрос с тем же ключом не создаёт дубликат
    repeat = auth_client.post(
        "/api/orders/wallet/transactions/topup/",
        {"currency": "stars", "amount": "300", "description": "Пополнение тест"},
        format="json",
        **headers,
    )
    assert repeat.status_code == 201
    assert repeat.json()["id"] == data["id"]

    withdraw_headers = {"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex}
    resp = auth_client.post(
        "/api/orders/wallet/transactions/withdraw/",
        {"currency": "stars", "amount": "120"},
        format="json",
        **withdraw_headers,
    )
    assert resp.status_code == 201
    withdraw_payload = resp.json()
    assert withdraw_payload["direction"] == "out"
    assert withdraw_payload["currency"] == "stars"
    user.profile.refresh_from_db()
    assert get_profile_stars_balance(user.profile) == 180

    resp = auth_client.post(
        "/api/orders/wallet/transactions/withdraw/",
        {"currency": "stars", "amount": "1000"},
        format="json",
        **{"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex},
    )
    assert resp.status_code == 400
    assert "amount" in resp.json()


@pytest.mark.django_db
def test_wallet_webhook_accepts_xtr_currency(payment_service: PaymentService, user: User):
    topup_result = payment_service.start_wallet_topup(
        user.profile,
        currency=WalletTransaction.Currency.TELEGRAM_STARS,
        amount=Decimal("150"),
        provider=PaymentAttempt.Provider.TELEGRAM_STARS,
        idempotency_key=uuid.uuid4().hex,
    )
    charge_id = "charge-xtr-1"
    payment_service.handle_webhook(
        PaymentAttempt.Provider.TELEGRAM_STARS,
        {
            "external_payment_id": topup_result.payment_attempt.external_payment_id,
            "status": "succeeded",
            "amount": 150,
            "currency": "XTR",
            "profile_id": user.profile.pk,
            "telegram_payment_charge_id": charge_id,
        },
        idempotency_key=uuid.uuid4().hex,
    )

    user.profile.refresh_from_db()
    assert get_profile_stars_balance(user.profile) == 150

    wallet_tx = WalletTransaction.objects.get(reference=charge_id)
    assert wallet_tx.currency == WalletTransaction.Currency.TELEGRAM_STARS


@pytest.mark.django_db
def test_generate_telegram_invoice(auth_client: APIClient, user: User):
    headers = {"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex}
    resp = auth_client.post(
        "/api/orders/wallet/telegram-stars/invoice/",
        {"amount": 150, "comment": "CRM topup"},
        format="json",
        **headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["payment_attempt_id"]
    assert data["invoice_link"].startswith("https://")
    assert data["stars_purchase_blocked"] is False
    attempt = PaymentAttempt.objects.get(pk=data["payment_attempt_id"])
    assert attempt.provider == PaymentAttempt.Provider.TELEGRAM_STARS
    assert attempt.confirmation_payload["invoice_link"] == data["invoice_link"]

    repeat = auth_client.post(
        "/api/orders/wallet/telegram-stars/invoice/",
        {"amount": 150, "comment": "CRM topup"},
        format="json",
        **headers,
    )
    assert repeat.status_code == 201
    assert repeat.json()["payment_attempt_id"] == data["payment_attempt_id"]


@pytest.mark.django_db
def test_generate_telegram_invoice_blocks_on_purchases_disabled(monkeypatch, auth_client: APIClient, user: User):
    class FailingInvoiceService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_wallet_topup_invoice(self, **kwargs):
            raise TelegramStarsInvoiceError(
                "Telegram временно отключил покупки Stars",
                code="purchases_disabled",
                details={"block_purchases": True},
            )

    monkeypatch.setattr(TelegramStarsProvider, "invoice_service_class", FailingInvoiceService)

    from apps.orders import views as orders_views

    orders_views.TelegramStarsInvoiceView.payment_service = PaymentService()

    headers = {"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex}
    resp = auth_client.post(
        "/api/orders/wallet/telegram-stars/invoice/",
        {"amount": 200},
        format="json",
        **headers,
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["code"] == "purchases_disabled"
    assert payload["stars_purchase_blocked"] is True
    user.profile.refresh_from_db()
    assert user.profile.stars_purchase_blocked is True


@pytest.mark.django_db
def test_generate_telegram_invoice_blocks_on_user_not_found(monkeypatch, auth_client: APIClient, user: User):
    class MissingUserInvoiceService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_wallet_topup_invoice(self, **kwargs):
            raise TelegramStarsInvoiceError(
                "Telegram не смог найти ваш аккаунт для оплаты Stars.",
                code="user_not_found",
                details={"block_purchases": True},
            )

    monkeypatch.setattr(TelegramStarsProvider, "invoice_service_class", MissingUserInvoiceService)

    from apps.orders import views as orders_views

    orders_views.TelegramStarsInvoiceView.payment_service = PaymentService()

    headers = {"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex}
    resp = auth_client.post(
        "/api/orders/wallet/telegram-stars/invoice/",
        {"amount": 200},
        format="json",
        **headers,
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    payload = resp.json()
    assert payload["code"] == "user_not_found"
    assert payload["stars_purchase_blocked"] is True
    user.profile.refresh_from_db()
    assert user.profile.stars_purchase_blocked is True


@pytest.mark.django_db
def test_payment_service_rejects_topup_when_blocked(user: User, payment_service: PaymentService):
    profile = user.profile
    profile.telegram_id = 9001
    profile.stars_purchase_blocked = True
    profile.save(update_fields=["telegram_id", "stars_purchase_blocked"])

    with pytest.raises(PaymentProviderError):
        payment_service.wallet_topup(
            profile,
            amount=Decimal("10"),
            charge_id="test-charge",
        )


@pytest.mark.django_db
def test_wallet_summary_contains_targets_and_transactions(auth_client: APIClient, user: User):
    WalletPerk.objects.create(
        profile=user.profile,
        title="Бесплатная доставка",
        description="для заказов от 2000₽",
        priority=1,
    )
    WalletTarget.objects.create(
        profile=user.profile,
        currency=WalletTransaction.Currency.CALOCOIN,
        target_amount=Decimal("900.00"),
        label="До расширенного PRO",
        progress_template="Осталось {left} CaloCoin до полного доступа.",
        completed_template="CaloCoin достаточно — обновите PRO прямо сейчас.",
        priority=1,
    )

    auth_client.post(
        "/api/orders/wallet/transactions/topup/",
        {"currency": "calo", "amount": "450.50", "description": "Первый платёж"},
        format="json",
        **{"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex},
    )
    resp = auth_client.get("/api/orders/wallet/summary/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["flags"]["stars_purchase_blocked"] is False
    calo_target = data["targets"]["calo"]
    assert calo_target["balance"] >= 450
    assert calo_target["target"] == pytest.approx(900.0)
    assert calo_target.get("label") == "До расширенного PRO"
    assert calo_target.get("progress_message").startswith("Осталось")
    assert calo_target.get("completed_message").startswith("CaloCoin достаточно")


@pytest.mark.django_db
def test_bot_payment_report_rejects_when_blocked(api_client: APIClient, user: User, settings):
    settings.BOT_INTERNAL_KEY = "bot-secret"
    profile = user.profile
    profile.telegram_id = 555123
    profile.stars_purchase_blocked = True
    profile.save(update_fields=["telegram_id", "stars_purchase_blocked"])

    resp = api_client.post(
        "/api/orders/bot/telegram-stars/payment/",
        {"user_id": profile.telegram_id, "amount": 50, "charge_id": "blocked-1"},
        format="json",
        HTTP_X_BOT_KEY="bot-secret",
    )

    assert resp.status_code == status.HTTP_403_FORBIDDEN
    payload = resp.json()
    assert "заблокировал" in payload.get("detail", "")
    assert payload.get("code") == "purchases_disabled"


@pytest.mark.django_db
def test_bot_payment_report_blocks_when_user_missing(monkeypatch, api_client: APIClient, user: User, settings):
    settings.BOT_INTERNAL_KEY = "bot-secret"
    from apps.orders import views as orders_views

    orders_views.TelegramStarsInvoiceView.payment_service = PaymentService()
    payment_service = PaymentService()
    orders_views.TelegramBotPaymentReportView.payment_service = payment_service

    def failing_wallet_topup(*args, **kwargs):
        raise PaymentProviderError(
            "Telegram не смог найти ваш аккаунт для оплаты Stars.",
            code="user_not_found",
            details={"block_purchases": True},
        )

    monkeypatch.setattr(payment_service, "wallet_topup", failing_wallet_topup)

    profile = user.profile
    profile.telegram_id = 775566
    profile.save(update_fields=["telegram_id", "updated_at"])

    resp = api_client.post(
        "/api/orders/bot/telegram-stars/payment/",
        {"user_id": profile.telegram_id, "amount": 50, "charge_id": "missing-user"},
        format="json",
        HTTP_X_BOT_KEY="bot-secret",
    )

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    payload = resp.json()
    assert payload["code"] == "user_not_found"
    assert payload["stars_purchase_blocked"] is True
    profile.refresh_from_db()
    assert profile.stars_purchase_blocked is True


@pytest.mark.django_db
def test_bot_payment_report_updates_attempt(api_client: APIClient, user: User, payment_service: PaymentService, settings):
    settings.BOT_INTERNAL_KEY = "bot-secret"
    profile = user.profile
    profile.telegram_id = 712345
    profile.save(update_fields=["telegram_id", "updated_at"])

    attempt_result = payment_service.start_wallet_topup(
        profile,
        currency=WalletTransaction.Currency.TELEGRAM_STARS,
        amount=Decimal("75"),
        provider=PaymentAttempt.Provider.TELEGRAM_STARS,
        idempotency_key=uuid.uuid4().hex,
        metadata={"comment": "auto"},
        request_id="test",
    )
    attempt = attempt_result.payment_attempt

    charge_id = "aid-charge-1"
    resp = api_client.post(
        "/api/orders/bot/telegram-stars/payment/",
        {
            "user_id": profile.telegram_id,
            "amount": 75,
            "charge_id": charge_id,
            "payment_attempt_id": attempt.pk,
        },
        format="json",
        HTTP_X_BOT_KEY="bot-secret",
        HTTP_IDEMPOTENCY_KEY=f"telegram-stars:{profile.telegram_id}:{charge_id}",
    )

    assert resp.status_code == status.HTTP_201_CREATED
    attempt.refresh_from_db()
    assert attempt.telegram_payment_charge_id == charge_id
    assert attempt.status == PaymentAttempt.Status.SUCCEEDED
    assert attempt.wallet_transaction is not None

    event = IntegrationWebhookEvent.objects.get(external_event_id=charge_id)
    assert event.related_payment_id == attempt.pk
    assert event.status == IntegrationWebhookEvent.ProcessingStatus.PROCESSED
    assert event.payload["payment_attempt_id"] == attempt.pk


@pytest.mark.django_db
def test_bot_payment_report_accepts_long_charge_id(api_client: APIClient, user: User, settings):
    settings.BOT_INTERNAL_KEY = "bot-secret"
    profile = user.profile
    profile.telegram_id = 845001
    profile.save(update_fields=["telegram_id", "updated_at"])

    long_charge = "charge-" + ("x" * 210)
    resp = api_client.post(
        "/api/orders/bot/telegram-stars/payment/",
        {
            "user_id": profile.telegram_id,
            "amount": 25,
            "charge_id": long_charge,
        },
        format="json",
        HTTP_X_BOT_KEY="bot-secret",
        HTTP_IDEMPOTENCY_KEY=f"telegram-stars:{profile.telegram_id}:{long_charge}",
    )

    assert resp.status_code == status.HTTP_201_CREATED
    payload = resp.json()
    tx = WalletTransaction.objects.get(pk=payload["id"])
    assert tx.reference == long_charge
    assert tx.idempotency_key == f"telegram-stars:{profile.telegram_id}:{long_charge}"


@pytest.mark.django_db
def test_duplicate_webhook_is_idempotent(user: User, payment_service: PaymentService):
    profile = user.profile
    result = payment_service.start_wallet_topup(
        profile,
        currency=WalletTransaction.Currency.TELEGRAM_STARS,
        amount=Decimal("100"),
        provider=PaymentAttempt.Provider.TELEGRAM_STARS,
        idempotency_key=uuid.uuid4().hex,
        metadata={"source": "test"},
    )
    payload = {
        "external_payment_id": result.payment_attempt.external_payment_id,
        "status": "succeeded",
        "amount": 100,
        "currency": WalletTransaction.Currency.TELEGRAM_STARS,
        "profile_id": profile.pk,
    }
    payment_service.handle_webhook(
        PaymentAttempt.Provider.TELEGRAM_STARS,
        payload,
        idempotency_key=uuid.uuid4().hex,
    )
    payment_service.handle_webhook(
        PaymentAttempt.Provider.TELEGRAM_STARS,
        payload,
        idempotency_key=uuid.uuid4().hex,
    )
    profile.refresh_from_db()
    assert get_profile_stars_balance(profile) == 100
    assert IntegrationWebhookEvent.objects.filter(
        external_event_id=result.payment_attempt.external_payment_id).count() == 1


@pytest.mark.django_db
def test_hold_confirm_and_release(user: User, payment_service: PaymentService):
    profile = user.profile
    wallet_headers = {"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex}
    client = APIClient()
    client.force_authenticate(user=user)
    client.post(
        "/api/orders/wallet/transactions/topup/",
        {"currency": "calo", "amount": "200"},
        format="json",
        **wallet_headers,
    )
    order = Order.objects.create(
        user=user,
        profile=profile,
        title="Тест заказ",
        currency=Order.Currency.CALOCOIN,
        total_price=Decimal("150"),
        status=Order.Status.PENDING_PAYMENT,
    )
    attempt = payment_service.start_order_payment(
        order,
        currency=order.currency,
        amount=order.total_price,
        provider=PaymentAttempt.Provider.CALOCOIN,
        idempotency_key=uuid.uuid4().hex,
        metadata={"reason": "test"},
    )
    assert attempt.wallet_transaction.direction == WalletTransaction.Direction.HOLD
    balance = get_wallet_balance(profile, WalletTransaction.Currency.CALOCOIN)
    assert balance.available == Decimal("50.00")

    payment_service.complete_calocoin_payment(attempt, idempotency_key=uuid.uuid4().hex)
    order.refresh_from_db()
    assert order.status == Order.Status.PAID
    balance = get_wallet_balance(profile, WalletTransaction.Currency.CALOCOIN)
    assert balance.total == Decimal("50.00")

    # start new hold and cancel it
    attempt2 = payment_service.start_order_payment(
        order,
        currency=order.currency,
        amount=Decimal("40"),
        provider=PaymentAttempt.Provider.CALOCOIN,
        idempotency_key=uuid.uuid4().hex,
    )
    payment_service.cancel_calocoin_payment(attempt2, reason="customer_cancelled", idempotency_key=uuid.uuid4().hex)
    attempt2.refresh_from_db()
    assert attempt2.status == PaymentAttempt.Status.CANCELLED


@pytest.mark.django_db
def test_subscription_autopay_success_and_failure(user: User):
    profile = user.profile
    plan = SubscriptionPlan.objects.create(
        slug="weekly-pro",
        name="Weekly PRO",
        city="Moscow",
        billing_period=SubscriptionPlan.BillingPeriod.WEEKLY,
        price_calocoin=Decimal("200"),
        delivery_service=DeliveryService.objects.create(slug="local", name="Local", city="Moscow"),
    )
    subscription = MealSubscription.objects.create(
        user=user,
        profile=profile,
        plan=plan,
        status=MealSubscription.Status.ACTIVE,
        autopay_enabled=True,
        city="Moscow",
    )
    payment_service = PaymentService()
    billing_service = BillingService(payment_service=payment_service)

    # пополняем кошелёк CaloCoin
    client = APIClient()
    client.force_authenticate(user=user)
    client.post(
        "/api/orders/wallet/transactions/topup/",
        {"currency": "calo", "amount": "250"},
        format="json",
        **{"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex},
    )
    result = billing_service.charge_subscription(subscription, idempotency_key=uuid.uuid4().hex)
    assert result.success
    assert result.order.status == Order.Status.PAID
    subscription.refresh_from_db()
    assert subscription.status == MealSubscription.Status.ACTIVE
    assert subscription.next_billing_at is not None

    # отсутствие средств => провал
    result_fail = billing_service.charge_subscription(subscription, idempotency_key=uuid.uuid4().hex)
    assert not result_fail.success
    subscription.refresh_from_db()
    assert subscription.status == MealSubscription.Status.PAUSED


@pytest.mark.django_db
def test_checkout_order_payment_flows(auth_client: APIClient, user: User, payment_service: PaymentService):
    service = DeliveryService.objects.create(slug="rocket", name="Rocket", city="Moscow")
    window = DeliveryWindow.objects.create(service=service, city="Moscow", start_time=timezone.now().time(),
                                           end_time=(timezone.now() + timedelta(hours=2)).time())

    # calocoin order
    auth_client.post(
        "/api/orders/wallet/transactions/topup/",
        {"currency": "calo", "amount": "400"},
        format="json",
        **{"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex},
    )
    resp = auth_client.post(
        "/api/orders/orders/",
        {
            "title": "Test order",
            "currency": "calo",
            "amount": "150",
            "pay_with_wallet": True,
        },
        format="json",
        **{"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex},
    )
    assert resp.status_code == 201

    checkout_resp = auth_client.post(
        "/api/orders/orders/checkout/",
        {
            "title": "Delivery",
            "description": "Calo checkout",
            "kind": "other",
            "currency": "calo",
            "amount": "120",
            "delivery_service": service.pk,
            "delivery_window": window.pk,
            "delivery_date": timezone.now().date().isoformat(),
            "address": "Test street",
            "items": [
                {"menu_item_id": 1, "quantity": "1", "unit_price": "120"},
            ],
        },
        format="json",
        **{"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex},
    )
    assert checkout_resp.status_code == 201
    payload = checkout_resp.json()
    order = Order.objects.get(pk=payload["order_id"])
    assert order.status == Order.Status.CONFIRMED

    # Stars checkout requires webhook to finish
    topup_result = payment_service.start_wallet_topup(
        user.profile,
        currency=WalletTransaction.Currency.TELEGRAM_STARS,
        amount=Decimal("300"),
        provider=PaymentAttempt.Provider.TELEGRAM_STARS,
        idempotency_key=uuid.uuid4().hex,
    )
    payment_service.handle_webhook(
        PaymentAttempt.Provider.TELEGRAM_STARS,
        {
            "external_payment_id": topup_result.payment_attempt.external_payment_id,
            "status": "succeeded",
            "amount": 300,
            "currency": WalletTransaction.Currency.TELEGRAM_STARS,
            "profile_id": user.profile.pk,
            "telegram_payment_charge_id": "charge-topup-1",
        },
        idempotency_key=uuid.uuid4().hex,
    )

    topup_result.payment_attempt.refresh_from_db()
    assert topup_result.payment_attempt.telegram_payment_charge_id == "charge-topup-1"
    topup_event = IntegrationWebhookEvent.objects.get(
        external_event_id=topup_result.payment_attempt.external_payment_id
    )
    assert topup_event.payload["telegram_payment_charge_id"] == "charge-topup-1"
    assert topup_event.related_payment_id == topup_result.payment_attempt.pk

    checkout_stars = auth_client.post(
        "/api/orders/orders/checkout/",
        {
            "title": "Stars delivery",
            "currency": "stars",
            "amount": "100",
            "delivery_service": service.pk,
            "delivery_window": window.pk,
            "delivery_date": timezone.now().date().isoformat(),
            "address": "Test street",
            "items": [
                {"menu_item_id": 2, "quantity": "1", "unit_price": "100"},
            ],
        },
        format="json",
        **{"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex},
    )
    assert checkout_stars.status_code == 201
    stars_payload = checkout_stars.json()
    attempt = PaymentAttempt.objects.get(pk=stars_payload["payment_attempt_id"])
    assert attempt.status == PaymentAttempt.Status.INITIATED
    order_stars = Order.objects.get(pk=stars_payload["order_id"])
    assert order_stars.status == Order.Status.PENDING_PAYMENT

    payment_service.handle_webhook(
        PaymentAttempt.Provider.TELEGRAM_STARS,
        {
            "external_payment_id": attempt.external_payment_id,
            "status": "succeeded",
            "amount": 100,
            "currency": WalletTransaction.Currency.TELEGRAM_STARS,
            "order_id": order_stars.pk,
            "profile_id": user.profile.pk,
            "telegram_payment_charge_id": "charge-order-1",
        },
        idempotency_key=uuid.uuid4().hex,
    )
    order_stars.refresh_from_db()
    assert order_stars.status == Order.Status.PAID
    attempt.refresh_from_db()
    assert attempt.telegram_payment_charge_id == "charge-order-1"
    event = IntegrationWebhookEvent.objects.get(
        external_event_id=attempt.external_payment_id
    )
    assert event.related_order_id == order_stars.pk
    assert event.payload["telegram_payment_charge_id"] == "charge-order-1"

    @pytest.mark.django_db
    def test_feature_purchase_with_idempotency(auth_client: APIClient, user: User):
        auth_client.post(
            "/api/orders/wallet/transactions/topup/",
            {"currency": "calo", "amount": "50"},
            format="json",
            **{"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex},
        )
        key = uuid.uuid4().hex
        resp = auth_client.post(
            "/api/orders/features/compose_recipe/purchase/",
            {"currency": "calo", "amount": "20"},
            format="json",
            **{"HTTP_IDEMPOTENCY_KEY": key},
        )
        assert resp.status_code == 201
        repeat = auth_client.post(
            "/api/orders/features/compose_recipe/purchase/",
            {"currency": "calo", "amount": "20"},
            format="json",
            **{"HTTP_IDEMPOTENCY_KEY": key},
        )
        assert repeat.status_code == 201
        assert repeat.json()["id"] == resp.json()["id"]
