from __future__ import annotations
import os
import re
from typing import List, Tuple
import httpx

_CYR = re.compile(r"[А-Яа-яЁё]")


def looks_russian(text: str | None) -> bool:
    if not text:
        return False
    return bool(_CYR.search(text))


def _yandex_translate(target_lang: str, texts: List[str]) -> List[str]:
    api_key = os.environ.get("YANDEX_API_KEY")
    folder_id = os.environ.get("YANDEX_FOLDER_ID")
    if not api_key or not folder_id:
        return texts

    url = "https://translate.api.cloud.yandex.net/translate/v2/translate"
    payload = {
        "folderId": folder_id,
        "targetLanguageCode": (target_lang or "ru"),
        "texts": texts,
    }
    headers = {"Authorization": f"Api-Key {api_key}"}

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            out = [item["text"] for item in data.get("translations", [])]
            return out if len(out) == len(texts) else texts
    except Exception:
        return texts


def translate_news_fields(
    *,
    title: str | None,
    lead: str | None,
    content: str | None,
    target_lang: str = "ru",
    enabled: bool = False,
) -> Tuple[str | None, str | None, str | None]:
    """
    Возвращает (title, lead, content) — переведённые, если enabled=True и язык не русский.
    При ошибках перевода возвращает исходные значения.
    """
    if not enabled:
        return title, lead, content

    items = [title or "", lead or "", content or ""]
    # Не отправляем в перевод строки, где уже есть кириллица или строка пустая
    to_translate = ["" if looks_russian(t) or not t.strip() else t for t in items]
    if not any(to_translate):
        return title, lead, content

    translated = _yandex_translate(target_lang, to_translate)
    # Склеиваем: если перевод пуст — оставляем оригинал
    merged: list[str] = []
    for original, new in zip(items, translated):
        merged.append(new or original)

    t_title, t_lead, t_content = merged
    return (t_title or None), (t_lead or None), (t_content or None)