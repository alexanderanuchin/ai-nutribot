from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from typing import Iterable
from html import escape

from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify

from ..models import MealPlan, MealPlanItem
from .meal_plan_metrics import empty_nutrition, format_nutrition, item_total_nutrition
from .plan_description import parse_plan_description


class MealPlanExportError(ValueError):
    pass


def _plan_items(plan: MealPlan) -> Iterable[MealPlanItem]:
    if hasattr(plan, "_prefetched_objects_cache") and "items" in plan._prefetched_objects_cache:
        items = plan._prefetched_objects_cache["items"]
        return [item for item in items]
    return plan.items.all()


def _format_filename(plan: MealPlan, suffix: str, extension: str) -> str:
    title_slug = slugify(plan.title or "plan") or f"plan-{plan.id}"
    today = timezone.now().date().isoformat()
    return f"{title_slug}-{suffix}-{today}.{extension}"


def _build_client_export(plan: MealPlan) -> tuple[str, str, str]:
    schema = parse_plan_description(plan.description)
    sections = schema.sections
    items_by_day: dict[str, list[MealPlanItem]] = defaultdict(list)
    for item in _plan_items(plan):
        key = item.scheduled_for.isoformat() if item.scheduled_for else "Без даты"
        items_by_day[key].append(item)

    def render_item(entry: MealPlanItem) -> str:
        title = ""
        subtitle = ""
        if entry.recipe:
            title = entry.recipe.title
            subtitle = "рецепт"
        elif entry.product:
            title = entry.product.title
            subtitle = "продукт"
        totals = item_total_nutrition(entry)
        totals_text = f"{totals['calories']:.0f} ккал · Б {totals['protein_g']:.1f} · Ж {totals['fat_g']:.1f} · У {totals['carbs_g']:.1f}"
        return (
            "<li class=\"plan-item\">"
            f"<span class=\"item-title\">{escape(title or 'Без названия')}</span>"
            f"<span class=\"item-meta\">{escape(subtitle)} · порций: {entry.servings}</span>"
            f"<span class=\"item-nutrition\">{totals_text}</span>"
            "</li>"
        )

    day_sections: list[str] = []
    for key in sorted(items_by_day.keys()):
        entries = "".join(render_item(item) for item in items_by_day[key])
        heading = key if key != "Без даты" else "Без даты"
        day_sections.append(
            "<section class=\"plan-day\">"
            f"<h3>{escape(heading)}</h3>"
            f"<ul>{entries or '<li>Нет назначений</li>'}</ul>"
            "</section>"
        )

    follow_up_list = "".join(
        f"<li>{escape(item)}</li>" for item in sections.follow_up_requirements
    ) or "<li>Отслеживание согласуйте с нутрициологом.</li>"
    next_review_text = (
        sections.next_review_date.isoformat() if sections.next_review_date else "По согласованию"
    )

    html = f"""
<!DOCTYPE html>
<html lang=\"ru\">
  <head>
    <meta charset=\"utf-8\" />
    <title>{escape(plan.title)} — План питания</title>
    <style>
      body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 32px; color: #111827; background: #F9FAFB; }}
      header {{ margin-bottom: 32px; }}
      h1 {{ font-size: 28px; margin: 0 0 8px; }}
      h2 {{ font-size: 20px; margin: 24px 0 12px; }}
      h3 {{ font-size: 18px; margin: 16px 0 8px; }}
      p {{ line-height: 1.6; margin: 0 0 12px; }}
      section {{ margin-bottom: 24px; padding: 16px; border-radius: 16px; background: #FFFFFF; box-shadow: 0 12px 24px rgba(15, 23, 42, 0.06); }}
      .badge {{ display: inline-block; padding: 6px 10px; border-radius: 9999px; background: #EEF2FF; color: #3730A3; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }}
      .plan-grid {{ display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}
      .plan-item {{ list-style: none; padding: 12px; border-radius: 12px; background: #F3F4F6; margin-bottom: 8px; }}
      .plan-item .item-title {{ display: block; font-weight: 600; margin-bottom: 4px; }}
      .plan-item .item-meta {{ display: block; font-size: 12px; color: #6B7280; margin-bottom: 4px; }}
      .plan-item .item-nutrition {{ display: block; font-size: 12px; color: #374151; }}
      ul {{ padding-left: 16px; margin: 0; }}
      ul li {{ margin-bottom: 6px; }}
    </style>
  </head>
  <body>
    <header>
      <span class=\"badge\">Персонализированный план</span>
      <h1>{escape(plan.title)}</h1>
      <p>Период: {plan.start_date.isoformat()} — {plan.end_date.isoformat() if plan.end_date else 'по плану'}</p>
      <p>Тон общения: {escape(sections.communication_tone or 'профессиональный поддерживающий')}</p>
    </header>
    <section>
      <h2>Цель вмешательства</h2>
      <p>{escape(sections.intervention_goal or 'Формулировка цели будет добавлена нутрициологом.')}</p>
      <h2>Обоснование</h2>
      <p>{escape(sections.rationale or 'Опишите ключевые факторы диагностики и поведения.')}</p>
      <h2>Ключевые диетпринципы</h2>
      <p>{escape(sections.dietary_principles or 'Задайте принципы питания и распределение приёмов пищи.')}</p>
      <h2>Рекомендации клиенту</h2>
      <p>{escape(sections.client_recommendations or 'Пропишите конкретные шаги и заметки по внедрению.')}</p>
      <h2>Мониторинг и контроль</h2>
      <p>{escape(sections.monitoring_plan or 'Опишите параметры самоконтроля, частоту отчётности и каналы связи.')}</p>
      <h2>Что прислать к следующей встрече</h2>
      <ul>{follow_up_list}</ul>
      <p><strong>Пересмотр плана:</strong> {escape(next_review_text)}</p>
      <p style=\"font-size: 12px; color: #6B7280;\">Персонализированный фидбек и регулярный самоконтроль повышают приверженность к питанию и телемедицинским рекомендациям (обзоры цифровых нутриционных сервисов 2022–2024).</p>
    </section>
    <section>
      <h2>График приёмов пищи</h2>
      <div class=\"plan-grid\">
        {''.join(day_sections)}
      </div>
    </section>
  </body>
</html>
"""
    filename = _format_filename(plan, "client", "html")
    return html, filename, "text/html; charset=utf-8"


def _build_specialist_export(plan: MealPlan) -> tuple[str, str, str]:
    schema = parse_plan_description(plan.description)
    sections = schema.sections
    totals = empty_nutrition()
    daily: dict[str, dict[str, float]] = defaultdict(empty_nutrition)
    items_payload: list[dict[str, object]] = []
    for item in _plan_items(plan):
        item_totals = item_total_nutrition(item)
        totals = {
            "calories": totals["calories"] + item_totals["calories"],
            "protein_g": totals["protein_g"] + item_totals["protein_g"],
            "fat_g": totals["fat_g"] + item_totals["fat_g"],
            "carbs_g": totals["carbs_g"] + item_totals["carbs_g"],
        }
        key = item.scheduled_for.isoformat() if item.scheduled_for else "unscheduled"
        day_totals = daily.setdefault(key, empty_nutrition())
        day_totals["calories"] += item_totals["calories"]
        day_totals["protein_g"] += item_totals["protein_g"]
        day_totals["fat_g"] += item_totals["fat_g"]
        day_totals["carbs_g"] += item_totals["carbs_g"]
        items_payload.append(
            {
                "id": item.id,
                "scheduled_for": item.scheduled_for.isoformat() if item.scheduled_for else None,
                "meal_type": item.meal_type,
                "servings": float(item.servings),
                "reference": {
                    "type": "recipe" if item.recipe_id else "product",
                    "id": item.recipe_id or item.product_id,
                    "title": getattr(item.recipe, "title", None) or getattr(item.product, "title", None),
                },
                "nutrition": format_nutrition(item_totals),
            }
        )

    description_payload = {
        "format": schema.format,
        "language": schema.language,
        "template_slug": schema.template_slug,
        "sections": {
            "intervention_goal": sections.intervention_goal,
            "rationale": sections.rationale,
            "dietary_principles": sections.dietary_principles,
            "client_recommendations": sections.client_recommendations,
            "monitoring_plan": sections.monitoring_plan,
            "follow_up_requirements": sections.follow_up_requirements,
            "next_review_date": sections.next_review_date.isoformat()
            if sections.next_review_date
            else None,
            "communication_tone": sections.communication_tone,
        },
    }

    payload = {
        "plan": {
            "id": plan.id,
            "title": plan.title,
            "start_date": plan.start_date.isoformat(),
            "end_date": plan.end_date.isoformat() if plan.end_date else None,
            "price": {
                "amount": float(plan.price_amount) if plan.price_amount is not None else None,
                "currency": plan.price_currency,
            },
            "metadata": plan.metadata,
            "description": description_payload,
        },
        "ncp": {
            "assessment": {
                "nutrition_targets": plan.metadata.get("targets", {}),
                "goal": sections.intervention_goal,
                "rationale": sections.rationale,
            },
            "diagnosis": {
                "statement": sections.rationale,
                "dietary_principles": sections.dietary_principles,
            },
            "intervention": {
                "client_recommendations": sections.client_recommendations,
                "monitoring_plan": sections.monitoring_plan,
                "communication_tone": sections.communication_tone,
            },
            "monitoring_evaluation": {
                "follow_up_requirements": sections.follow_up_requirements,
                "next_review_date": sections.next_review_date.isoformat()
                if sections.next_review_date
                else None,
            },
        },
        "totals": format_nutrition(totals),
        "daily_breakdown": [
            {
                "date": key if key != "unscheduled" else None,
                "nutrition": format_nutrition(value),
            }
            for key, value in sorted(daily.items(), key=lambda entry: entry[0] or "zzzz")
        ],
        "items": items_payload,
        "generated_at": timezone.now().isoformat(),
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    filename = _format_filename(plan, "ncp", "json")
    return content, filename, "application/json"


def _build_table_export(plan: MealPlan) -> tuple[str, str, str]:
    schema = parse_plan_description(plan.description)
    sections = schema.sections
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["plan_id", plan.id])
    writer.writerow(["title", plan.title])
    writer.writerow(["start_date", plan.start_date.isoformat()])
    writer.writerow(["end_date", plan.end_date.isoformat() if plan.end_date else ""])
    writer.writerow(["intervention_goal", sections.intervention_goal])
    writer.writerow(["monitoring_plan", sections.monitoring_plan])
    writer.writerow(["next_review_date", sections.next_review_date.isoformat() if sections.next_review_date else ""])
    writer.writerow(["communication_tone", sections.communication_tone])
    writer.writerow(["follow_up_requirements", " | ".join(sections.follow_up_requirements)])
    writer.writerow([])
    writer.writerow([
        "date",
        "meal_type",
        "reference_type",
        "reference_title",
        "servings",
        "calories",
        "protein_g",
        "fat_g",
        "carbs_g",
    ])
    for item in _plan_items(plan):
        totals = item_total_nutrition(item)
        writer.writerow(
            [
                item.scheduled_for.isoformat() if item.scheduled_for else "",
                item.meal_type or "",
                "recipe" if item.recipe_id else "product",
                getattr(item.recipe, "title", None) or getattr(item.product, "title", ""),
                float(item.servings),
                round(totals["calories"], 2),
                round(totals["protein_g"], 2),
                round(totals["fat_g"], 2),
                round(totals["carbs_g"], 2),
            ]
        )
    filename = _format_filename(plan, "table", "csv")
    return buffer.getvalue(), filename, "text/csv"


def export_meal_plan(plan: MealPlan, format_name: str) -> HttpResponse:
    normalized = (format_name or "").lower()
    if normalized not in {"client", "specialist", "table"}:
        raise MealPlanExportError("Unsupported export format")

    builders = {
        "client": _build_client_export,
        "specialist": _build_specialist_export,
        "table": _build_table_export,
    }
    content, filename, content_type = builders[normalized](plan)
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f"attachment; filename=\"{filename}\""
    return response


__all__ = ["export_meal_plan", "MealPlanExportError"]
