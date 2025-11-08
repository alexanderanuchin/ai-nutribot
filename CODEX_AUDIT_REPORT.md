# Codex Security & Quality Audit – ai-nutribot

## 1. Резюме

| Всего | P0 | P1 | P2 | P3 |
| ---: | --: | --: | --: | --: |
| 11 | 1 | 3 | 6 | 1 |

## 2. Матрица проверок

| Раздел | Статус | Доказательство |
| --- | --- | --- |
| Python lint (ruff) | FAIL | `ruff check .` → 33 ошибок lint.【513b34†L1-L109】 |
| Python format (black/isort) | FAIL | `black --check .`/`isort --check-only .` → 237 файлов к форматированию.【af6b3a†L1-L25】【7e7674†L1-L19】 |
| Python typing (mypy) | FAIL | `mypy backend bot` → 993 ошибок, отсутствуют stubs и типы.【daa157†L1-L120】【e1ca65†L1-L40】 |
| Shell lint | PASS | `shellcheck scripts/gen_rid.sh`.【acc8a8†L1-L2】 |
| Docker lint (hadolint) | N/A | Инструмент отсутствует, использован Trivy config (см. ниже). |
| Python security (bandit) | FAIL | 935 замечаний (assert/секреты).【adba6e†L1-L120】 |
| Python deps (pip-audit) | FAIL | CVE в aiohttp и simplejwt.【d3be41†L1-L5】 |
| JS lint (eslint) | PASS | `npm run lint`.【751662†L1-L1】 |
| JS format (prettier) | FAIL | 183 файлов требуют форматирования.【414cb3†L1-L99】 |
| TypeScript (tsc --noEmit) | FAIL | 205 ошибок типизации.【372a08†L1-L120】 |
| Frontend tests (vitest) | FAIL | 6 тестов упали (AuthProvider и websocket моки).【5837d8†L1-L37】 |
| Backend tests (pytest) | FAIL | Конфликт `apps/users/tests`.【75365b†L1-L13】 |
| Secret scanning (gitleaks) | FAIL | 9 токенов обнаружено (см. Finding P0-001).【a10980†L1-L82】 |
| Container scan (trivy fs) | WARN | База уязвимостей не найдена (нет отчёта). |
| IaC/Docker misconfig (trivy config) | FAIL | Dockerfile: root user + отсутствие HEALTHCHECK.【711d82†L1-L44】 |

## 3. Детализация findings

### P0-001 · Production secrets committed
- **Severity:** P0
- **Scope:** `infra/.env.example`
- **Evidence:**
  ```text
  infra/.env.example:L15-L35
  TELEGRAM_BOT_TOKEN=8281146404:AAFBxR1jetjlAJvYox5Cspu-3X25_0-LeTw
  JWT_SECRET=U7sNhRQYVOclegYfgB4DHurjvNFo3lcuORrjmvgFCdY_4lCSAlkB6oWkvhqyT1fIaCJleDjiNjybLYZard76Ng
  CLOUDPUB_TOKEN=t1sQrar30dUD2csQ3nv0O7WrENB0DS4yoiaXYxypImo
  YANDEX_API_KEY=AQVNya8NB9JiBoLTsTGi6Wan4ViHz4aPKjW8NMtU
  ```
  Gitleaks подтвердил 9 утечек.【a10980†L1-L82】
- **Root cause:** В `.env.example` вместо моков используются реальные токены и секреты.
- **Risk:** Компрометация Telegram-бота, JWT-подписей и внешних API → полный захват инфраструктуры.
- **Fix Plan:**
  1. Немедленно отозвать / ротация всех обнаруженных ключей (Telegram, JWT, CloudPub, Yandex).
  2. Заменить значения на макеты (`<set-in-secrets>`) и зашифровать реальные секреты в Vault/CI secrets.
  3. Добавить pre-commit/secrets scanning в CI.

### P1-001 · Insecure Django defaults
- **Severity:** P1
- **Scope:** `backend/nutribot/settings.py`
- **Evidence:**
  ```text
  backend/nutribot/settings.py:L27-L43
  SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret")
  ...
  if not raw_value:
      return ["*"]  # ALLOWED_HOSTS wildcard
  ```
- **Root cause:** Значения по умолчанию оставлены «боевыми» и допускают wildcard-хосты.
- **Risk:** При ошибке конфигурации в проде → предсказуемый SECRET_KEY и Host header injection.
- **Fix Plan:**
  1. Сделать `DJANGO_SECRET_KEY` обязательным (panic без переменной).
  2. Запретить `*` по умолчанию: fallback на `localhost` только в dev, иначе raise.
  3. Добавить проверку в healthcheck/CI на наличие secure ALLOWED_HOSTS.

### P1-002 · Vulnerable dependencies (aiohttp, simplejwt)
- **Severity:** P1
- **Scope:** `backend/requirements.txt`, `bot/requirements.txt`
- **Evidence:** `pip-audit` нашёл GHSA-8495-4g3g-x7pr, GHSA-9548-qrrj-x5pj (aiohttp 3.9.5) и GHSA-5vcc-86wm-547q (simplejwt 5.3.1).【d3be41†L1-L5】
- **Root cause:** Нет политики обновления зависимостей; отсутствует security scanning в CI.
- **Risk:** RCE/privilege escalation через веб-сервер или компрометация JWT авторизации.
- **Fix Plan:**
  1. Обновить `aiohttp` ≥ 3.12.14 и `djangorestframework-simplejwt` ≥ 5.5.1.
  2. Добавить `pip-audit` в CI и фиксировать версии в Dependabot.

### P1-003 · Docker images run as root without healthchecks
- **Severity:** P1
- **Scope:** `backend/Dockerfile`, `bot/Dockerfile`, `frontend/Dockerfile`
- **Evidence:** Dockerfile не содержит `USER` и `HEALTHCHECK`; Trivy отмечает high severity DS002/DS026.【cff960†L1-L19】【991675†L1-L10】【3904ea†L1-L10】【711d82†L1-L44】
- **Root cause:** Отсутствие hardening этапа и best practices.
- **Risk:** Root контейнер облегчает breakout; отсутствие healthcheck осложняет оркестрацию.
- **Fix Plan:**
  1. Добавить non-root пользователя, переключиться на него после установки зависимостей.
  2. Вынести `RUN` в multi-stage, добавить `HEALTHCHECK` (curl /healthz).

### P2-001 · Python style toolchain broken
- **Severity:** P2
- **Scope:** Весь `backend/`, `bot/`
- **Evidence:** `ruff` (33 ошибок), `black`/`isort` требуют форматирования 200+ файлов.【513b34†L1-L109】【af6b3a†L1-L25】【7e7674†L1-L19】
- **Root cause:** Нет `pyproject.toml`/pre-commit, большое дрейфование кода.
- **Risk:** Падает CI, усложняется review, технический долг.
- **Fix Plan:**
  1. Ввести `pyproject.toml` с настройками black/isort/ruff.
  2. Прогнать автоформатирование, включить pre-commit.

### P2-002 · Python typing baseline missing
- **Severity:** P2
- **Scope:** `backend/`, `bot/`
- **Evidence:** `mypy backend bot` → 993 ошибок, нет stubs для Django/DRF, некорректные типы в приложениях (`User? has no attribute`).【daa157†L1-L120】
- **Root cause:** Нет `mypy.ini`, смешение typed/untyped кода, отсутствие `django-stubs`.
- **Risk:** Type-safety отсутствует, сложнее ловить регрессии в больших сервисах.
- **Fix Plan:**
  1. Добавить `mypy.ini` (strict per app, `ignore_missing_imports` для сторонних libs).
  2. Установить `django-stubs`, `djangorestframework-stubs`, постепенно аннотировать сервисы.

### P2-003 · Backend tests fail (pytest import mismatch)
- **Severity:** P2
- **Scope:** `backend/apps/users/tests.py` vs `backend/apps/users/tests/`
- **Evidence:** Pytest конфликтует: импортирует пакет вместо файла (`apps/users/tests`).【75365b†L1-L13】
- **Root cause:** Одновременное существование `tests.py` и пакета `tests/`.
- **Risk:** Ни один тест не запускается; покрытие 0%.
- **Fix Plan:**
  1. Переименовать `tests.py` → `tests_root.py` либо переместить кейсы в пакет.
  2. Обновить `pytest.ini`/`__init__.py` для корректного discovery.

### P2-004 · Frontend formatting drift (Prettier)
- **Severity:** P2
- **Scope:** `frontend/src/**/*`
- **Evidence:** `npx prettier -c .` → 183 файлов с нарушением стиля.【414cb3†L1-L99】
- **Root cause:** Нет обязательного форматирования/притира.
- **Risk:** Merge-конфликты, нестабильный линт.
- **Fix Plan:**
  1. Добавить `prettier` в pre-commit/CI (with `--check`).
  2. Применить автоформатирование.

### P2-005 · TypeScript type errors (plan builder, env typing)
- **Severity:** P2
- **Scope:** `frontend/src/features/meal-plans/*`, `frontend/src/utils/realtime.ts`, UI kit
- **Evidence:** 205 ошибок `tsc --noEmit`: неверные пропы (`Badge` variant), отсутствует `import.meta.env`, несоответствие API типов.【372a08†L1-L120】
- **Root cause:** API типов не обновлены после новых фич, `tsconfig` не подключает `vite/client`.
- **Risk:** Prod build падает, автодеплой невозможен.
- **Fix Plan:**
  1. Добавить `"types": ["vite/client"]` в `tsconfig.json`.
  2. Привести UI пропсы и query-хуки к актуальным типам DTO.

### P2-006 · Vitest suite failing
- **Severity:** P2
- **Scope:** `frontend/src/pages/market/MarketCollectionPage.test.tsx`, `useFeedRealtime.test.tsx`
- **Evidence:** 6 падающих тестов (отсутствует AuthProvider, MockWebSocket не создаётся).【5837d8†L1-L37】
- **Root cause:** Перенос бизнес-логики без обновления тест-обвязки.
- **Risk:** Нет регрессионного контроля UI/реалтайма.
- **Fix Plan:**
  1. Обернуть страницы в `AuthProvider`/`QueryClientProvider` в тестах.
  2. Обновить моки WebSocket/SSE согласно новой реализации.

### P3-001 · README пустой
- **Severity:** P3
- **Scope:** `README.md`
- **Evidence:** `wc -l README.md` → 0 строк.【fa3cfc†L1-L2】
- **Root cause:** Отсутствует корневой onboarding.
- **Risk:** Сниженная DX, повышенный bus factor.
- **Fix Plan:**
  1. Заполнить README разделами: stack, запуск (Docker/Make), переменные окружения.
  2. Сослаться на `CODEX_AUDIT_REPORT.md`.

## 4. Приложение

- **Команды и журналы:** см. chunks `513b34`, `af6b3a`, `7e7674`, `daa157`, `91b638`, `414cb3`, `372a08`, `5837d8`, `75365b`, `adba6e`, `d3be41`, `711d82`, `acc8a8`.
- **Версии инструментов:** Python 3.12.12, Node 22.11 (из базовых образов), npm 10.x, pip 25.2.
- **Созданные PR/Issues:** отсутствуют (аудит-only).

