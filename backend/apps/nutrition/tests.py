import json
import pytest

from apps.nutrition.llm_provider import OpenAIProvider


class DummyMessage:
    def __init__(self, content: str):
        self.content = content


class DummyChoice:
    def __init__(self, content: str):
        self.message = DummyMessage(content)


class DummyResponse:
    def __init__(self, content: str):
        self.choices = [DummyChoice(content)]


class DummyChatCompletions:
    def __init__(self, response: DummyResponse):
        self._response = response
        self.calls = []

    def create(self, **kwargs):  # noqa: D401
        """Mimic openai.chat.completions.create."""
        self.calls.append(kwargs)
        return self._response


class DummyChat:
    def __init__(self, completions: DummyChatCompletions):
        self.completions = completions


class DummyClient:
    def __init__(self, completions: DummyChatCompletions):
        self.chat = DummyChat(completions)


@pytest.fixture(autouse=True)
def _clear_openai_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_ORGANIZATION", raising=False)


@pytest.fixture
def sample_context():
    return {
        "targets": {"calories": 1800, "protein": 120, "fat": 60, "carbs": 220},
        "items": [
            {
                "id": 1,
                "title": "Овсяная каша",
                "kcal": 350,
                "protein": 12,
                "fat": 8,
                "carbs": 55,
                "tags": ["breakfast"],
                "price": 220,
            },
            {
                "id": 2,
                "title": "Куриное филе",
                "kcal": 250,
                "protein": 35,
                "fat": 5,
                "carbs": 0,
                "tags": ["lunch"],
                "price": 350,
            },
        ],
        "restrictions": {"allergies": [], "exclusions": []},
    }


def test_provider_returns_empty_without_api_key(sample_context):
    provider = OpenAIProvider()
    assert provider.compose_menu(sample_context) == []


def test_provider_parses_valid_response(sample_context):
    payload = json.dumps({
        "plan": [
            {"item_id": 1, "qty": 1.5, "time_hint": "Dinner", "title": "Овсяная каша"},
        ]
    })
    completions = DummyChatCompletions(DummyResponse(payload))
    client = DummyClient(completions)
    provider = OpenAIProvider(client=client)

    plan = provider.compose_menu(sample_context)

    assert plan == [
        {"item_id": 1, "qty": 1.5, "time_hint": "dinner", "title": "Овсяная каша"}
    ]
    assert completions.calls, "LLM client should be invoked"
    assert completions.calls[0]["messages"][0]["role"] == "system"
    assert "Цели пользователя" in completions.calls[0]["messages"][1]["content"]


def test_provider_drops_invalid_entries(sample_context):
    payload = json.dumps({
        "plan": [
            {"item_id": 999, "qty": 1},  # отсутствует в меню
            {"item_id": 1, "qty": 0},  # количество должно быть > 0
            {"item_id": 2, "qty": "not-a-number"},
        ]
    })
    completions = DummyChatCompletions(DummyResponse(payload))
    client = DummyClient(completions)
    provider = OpenAIProvider(client=client)

    plan = provider.compose_menu(sample_context)

    assert plan == [
        {"item_id": 2, "qty": 1.0, "time_hint": "any", "title": "Куриное филе"}
    ]