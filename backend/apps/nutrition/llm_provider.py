import os
from typing import List, Dict

class LLMProvider:
    def compose_menu(self, context: Dict) -> List[Dict]:
        raise NotImplementedError

class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    def compose_menu(self, context: Dict) -> List[Dict]:
        # Реальную интеграцию добавим позже; пока пустой ответ -> включится фоллбек
        return []

PROVIDERS = {"openai": OpenAIProvider}

def get_provider():
    key = os.getenv("LLM_PROVIDER", "openai")
    return PROVIDERS[key]()
