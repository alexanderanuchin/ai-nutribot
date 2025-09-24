import json
import logging
import os
import time
from textwrap import dedent
from typing import Dict, List

from openai import (
    APIConnectionError,
    APITimeoutError,
    BadRequestError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = dedent(
    """
    Ты — виртуальный нутрициолог. Подбирай суточное меню из доступных блюд
    так, чтобы пользователь получил разнообразный рацион и попал в целевые
    калории, белки, жиры и углеводы. Учитывай пищевые ограничения и бюджет,
    не добавляй блюда, которых нет в списке.
    """
).strip()


class LLMProvider:
    def compose_menu(self, context: Dict) -> List[Dict]:
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    def __init__(self, client: OpenAI | None = None) -> None:
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
        self.timeout = float(os.getenv("OPENAI_TIMEOUT", "20"))
        self.max_attempts = max(1, int(os.getenv("OPENAI_MAX_RETRIES", "3")))
        self.retry_delay = float(os.getenv("OPENAI_RETRY_DELAY", "2.0"))
        self.max_plan_items = max(1, int(os.getenv("NUTRIBOT_MAX_PLAN_ITEMS", "6")))
        self.prompt_items_limit = max(1, int(os.getenv("NUTRIBOT_PROMPT_ITEMS_LIMIT", "40")))

        self._client = client
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OpenAI API key is not configured; provider disabled.")
                self._enabled = False
                return

            client_kwargs = {
                "api_key": api_key,
                "timeout": self.timeout,
                "max_retries": 0,
            }

            base_url = os.getenv("OPENAI_BASE_URL")
            if base_url:
                client_kwargs["base_url"] = base_url

            organization = os.getenv("OPENAI_ORGANIZATION")
            if organization:
                client_kwargs["organization"] = organization

            self._client = OpenAI(**client_kwargs)

        self._enabled = True

    def compose_menu(self, context: Dict) -> List[Dict]:
        if not getattr(self, "_enabled", False):
            return []

        if not context.get("items"):
            logger.info("LLM provider received empty items list; returning fallback plan.")
            return []

        prompt = self._build_user_prompt(context)
        attempts_left = self.max_attempts

        while attempts_left > 0:
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=800,
                    response_format={"type": "json_object"},
                )
                raw_content = self._extract_message_content(response)
                if not raw_content:
                    logger.warning("LLM response is empty; falling back to greedy knapsack.")
                    return []
                plan = self._parse_plan(raw_content, context)
                return plan
            except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
                attempts_left -= 1
                logger.warning(
                    "OpenAI request failed (%s). Attempts left: %s",
                    exc,
                    attempts_left,
                )
                if attempts_left <= 0:
                    break
                time.sleep(self.retry_delay)
            except BadRequestError as exc:
                logger.error("OpenAI rejected request: %s", exc)
                break
            except OpenAIError:
                logger.exception("Unexpected OpenAI error while composing menu")
                break
            except Exception:  # pragma: no cover - safety net
                logger.exception("Unexpected error while talking to OpenAI")
                break
        return []
    def _build_user_prompt(self, context: Dict) -> str:
        targets = context.get("targets") or {}
        restrictions = context.get("restrictions") or {}
        items = context.get("items") or []

        restrictions_list = []
        allergies = restrictions.get("allergies") or []
        exclusions = restrictions.get("exclusions") or []
        if allergies:
            restrictions_list.append("Аллергии: " + ", ".join(map(str, allergies)))
        if exclusions:
            restrictions_list.append("Исключения: " + ", ".join(map(str, exclusions)))
        if not restrictions_list:
            restrictions_list.append("Без дополнительных ограничений.")
        restrictions_block = "\n".join(f"- {line}" for line in restrictions_list)

        item_lines: List[str] = []
        for item in items[: self.prompt_items_limit]:
            tags = item.get("tags") or []
            tags_text = f", теги: {', '.join(tags)}" if tags else ""
            price = item.get("price")
            price_text = f", цена: {price}₽" if price is not None else ""
            line = (
                f"- #{item['id']}: {item['title']} — {item['kcal']} ккал, "
                f"Б/Ж/У: {item['protein']}/{item['fat']}/{item['carbs']}г"
                f"{price_text}{tags_text}"
            )
            item_lines.append(line)
        if not item_lines:
            item_lines.append("- Нет доступных блюд — если план невозможен, верни пустой список.")
        items_block = "\n".join(item_lines)

        prompt = dedent(
            f"""
            Цели пользователя:
            - Калории: {targets.get('calories')}
            - Белки: {targets.get('protein')}
            - Жиры: {targets.get('fat')}
            - Углеводы: {targets.get('carbs')}

            Ограничения:
            {restrictions_block}

            Доступные блюда:
            {items_block}

            Составь дневной план питания из 3-5 приемов пищи, используя только блюда из списка.
            Старайся разнообразить выбор и соблюсти калорийность и макронутриенты.
            Для каждого приема пищи укажи идентификатор блюда, количество порций (может быть дробным) и тип приема пищи.
            Ответ верни строго в формате JSON:
            {{
              "plan": [
                {{"item_id": 1, "qty": 1.0, "time_hint": "breakfast", "title": "Название блюда"}}
              ]
            }}
            time_hint используй из набора ["breakfast", "lunch", "dinner", "snack", "any"].
            Если невозможно составить план, верни {{"plan": []}}.
            """
        ).strip()

        return prompt

    def _extract_message_content(self, response) -> str:
        try:
            choice = response.choices[0]
            message = choice.message
        except (AttributeError, IndexError):
            return ""

        content = getattr(message, "content", "")
        if isinstance(content, list):
            parts: List[str] = []
            for fragment in content:
                if isinstance(fragment, dict) and fragment.get("type") == "text":
                    text = fragment.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            content = "".join(parts)

        if not isinstance(content, str):
            return ""

        return content.strip()

    def _parse_plan(self, payload: str, context: Dict) -> List[Dict]:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning("Failed to decode LLM JSON response")
            return []

        if not isinstance(data, dict):
            return []

        raw_plan = data.get("plan")
        if not isinstance(raw_plan, list):
            return []

        items_lookup: Dict[int, Dict] = {}
        for item in context.get("items", []):
            item_id = item.get("id")
            try:
                int_id = int(item_id)
            except (TypeError, ValueError):
                continue
            items_lookup[int_id] = item

        parsed_plan: List[Dict] = []
        used_ids: set[int] = set()

        for entry in raw_plan:
            if not isinstance(entry, dict):
                continue

            try:
                item_id = int(entry.get("item_id"))
            except (TypeError, ValueError):
                continue

            if item_id in used_ids or item_id not in items_lookup:
                continue

            qty_raw = entry.get("qty", 1)
            try:
                qty = float(qty_raw)
            except (TypeError, ValueError):
                qty = 1.0

            if qty <= 0:
                continue

            qty = min(max(qty, 0.5), 5.0)

            time_hint = entry.get("time_hint") or "any"
            if not isinstance(time_hint, str):
                time_hint = "any"
            time_hint = time_hint.strip().lower() or "any"

            title = entry.get("title") or items_lookup[item_id].get("title")
            if not isinstance(title, str):
                title = str(items_lookup[item_id].get("title", ""))

            parsed_plan.append(
                {
                    "item_id": item_id,
                    "qty": round(qty, 2),
                    "time_hint": time_hint,
                    "title": title,
                }
            )

            used_ids.add(item_id)

            if len(parsed_plan) >= self.max_plan_items:
                break

        return parsed_plan


PROVIDERS = {"openai": OpenAIProvider}


def get_provider():
    key = os.getenv("LLM_PROVIDER", "openai")
    return PROVIDERS[key]()
