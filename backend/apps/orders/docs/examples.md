# Примеры запросов и webhook-пейлоадов

## Пополнение Stars из CRM
```bash
curl -X POST https://api.nutribot.local/api/orders/wallet/manual-stars/ \
  -H "Authorization: Bearer <token>" \
  -H "Idempotency-Key: <uuid>" \
  -H "Content-Type: application/json" \
  -d '{"amount": 150, "source": "crm_purchase_card"}'
```

## Пополнение CaloCoin через карту
```bash
curl -X POST https://api.nutribot.local/api/orders/wallet/topup/ \
  -H "Authorization: Bearer <token>" \
  -H "Idempotency-Key: <uuid>" \
  -H "Content-Type: application/json" \
  -d '{"currency": "calo", "amount": "250", "provider": "card"}'
```

## Пример webhook от Telegram Stars
```json
{
  "external_payment_id": "stars-78f1b2",
  "status": "succeeded",
  "amount": 120,
  "currency": "STARS",
  "profile_id": 42
}
```

## Пример webhook от карточного провайдера
```json
{
  "external_payment_id": "card-991",
  "status": "succeeded",
  "amount": "500.00",
  "currency": "CALO",
  "profile_id": 42
}
```

## Покупка функции compose_recipe
```bash
curl -X POST https://api.nutribot.local/api/orders/features/compose_recipe/purchase/ \
  -H "Authorization: Bearer <token>" \
  -H "Idempotency-Key: <uuid>" \
  -H "Content-Type: application/json" \
  -d '{"currency": "calo", "amount": "15"}'
```