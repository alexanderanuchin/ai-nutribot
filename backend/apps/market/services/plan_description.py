from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

from django.utils import timezone

PLAN_DESCRIPTION_FORMAT = "ncp-adime-v1"


@dataclass
class PlanDescriptionSections:
    intervention_goal: str
    rationale: str
    dietary_principles: str
    client_recommendations: str
    monitoring_plan: str
    follow_up_requirements: list[str]
    next_review_date: Optional[date]
    communication_tone: str


@dataclass
class PlanDescriptionSchema:
    format: str
    language: str
    template_slug: Optional[str]
    sections: PlanDescriptionSections


_DEFAULT_SECTIONS = PlanDescriptionSections(
    intervention_goal="",
    rationale="",
    dietary_principles="",
    client_recommendations="",
    monitoring_plan="",
    follow_up_requirements=[],
    next_review_date=None,
    communication_tone="профессиональный поддерживающий",
)


def _clone_sections(sections: PlanDescriptionSections) -> PlanDescriptionSections:
    return PlanDescriptionSections(
        intervention_goal=sections.intervention_goal,
        rationale=sections.rationale,
        dietary_principles=sections.dietary_principles,
        client_recommendations=sections.client_recommendations,
        monitoring_plan=sections.monitoring_plan,
        follow_up_requirements=list(sections.follow_up_requirements),
        next_review_date=sections.next_review_date,
        communication_tone=sections.communication_tone,
    )


def _ensure_list(value: Any) -> list[str]:
    if isinstance(value, list):
        items = []
        for entry in value:
            if not entry:
                continue
            if isinstance(entry, str):
                items.append(entry.strip())
            else:
                items.append(str(entry).strip())
        return [item for item in items if item]
    if isinstance(value, str):
        return [item.strip() for item in value.splitlines() if item.strip()]
    if value is None:
        return []
    return [str(value).strip()]


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        try:
            return date.fromtimestamp(value)
        except (OSError, OverflowError):  # pragma: no cover - defensive
            return None
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def parse_plan_description(raw: Optional[str]) -> PlanDescriptionSchema:
    if not raw:
        return PlanDescriptionSchema(
            format=PLAN_DESCRIPTION_FORMAT,
            language="ru",
            template_slug=None,
            sections=_clone_sections(_DEFAULT_SECTIONS),
        )

    payload: dict[str, Any]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        defaults = _clone_sections(_DEFAULT_SECTIONS)
        defaults.client_recommendations = raw.strip()
        sections = defaults
        return PlanDescriptionSchema(
            format=PLAN_DESCRIPTION_FORMAT,
            language="ru",
            template_slug=None,
            sections=sections,
        )

    data_format = str(payload.get("format") or PLAN_DESCRIPTION_FORMAT)
    language = str(payload.get("language") or "ru")
    template_slug = payload.get("template_slug")
    sections_payload = payload.get("sections") or {}

    sections = PlanDescriptionSections(
        intervention_goal=str(sections_payload.get("intervention_goal") or "").strip(),
        rationale=str(sections_payload.get("rationale") or "").strip(),
        dietary_principles=str(sections_payload.get("dietary_principles") or "").strip(),
        client_recommendations=str(sections_payload.get("client_recommendations") or "").strip(),
        monitoring_plan=str(sections_payload.get("monitoring_plan") or "").strip(),
        follow_up_requirements=_ensure_list(sections_payload.get("follow_up_requirements")),
        next_review_date=_parse_date(sections_payload.get("next_review_date")),
        communication_tone=str(sections_payload.get("communication_tone") or _DEFAULT_SECTIONS.communication_tone).strip()
        or _DEFAULT_SECTIONS.communication_tone,
    )

    return PlanDescriptionSchema(
        format=data_format,
        language=language,
        template_slug=str(template_slug) if template_slug else None,
        sections=sections,
    )


def serialize_plan_description(schema: PlanDescriptionSchema) -> str:
    payload = {
        "format": schema.format or PLAN_DESCRIPTION_FORMAT,
        "language": schema.language or "ru",
        "template_slug": schema.template_slug,
        "sections": {
            "intervention_goal": schema.sections.intervention_goal,
            "rationale": schema.sections.rationale,
            "dietary_principles": schema.sections.dietary_principles,
            "client_recommendations": schema.sections.client_recommendations,
            "monitoring_plan": schema.sections.monitoring_plan,
            "follow_up_requirements": schema.sections.follow_up_requirements,
            "next_review_date": schema.sections.next_review_date.isoformat()
            if schema.sections.next_review_date
            else None,
            "communication_tone": schema.sections.communication_tone,
        },
        "generated_at": timezone.now().isoformat(),
    }
    return json.dumps(payload, ensure_ascii=False)


__all__ = [
    "PLAN_DESCRIPTION_FORMAT",
    "PlanDescriptionSchema",
    "PlanDescriptionSections",
    "parse_plan_description",
    "serialize_plan_description",
]
