import { useEffect, useMemo, useState } from 'react'
import { CalendarIcon, CheckCircle2Icon, LayoutTemplateIcon, Wand2Icon } from 'lucide-react'

import { SheetContent, SheetFooter, SheetRoot } from '../../../components/ui/Sheet'
import { Badge, Button, Card } from '../../../components/ui'
import type { MealPlan } from '../../../types/meal-plan'
import {
  createEmptyPlanDescription,
  formatFollowUpToMultiline,
  parseFollowUpFromMultiline,
  parsePlanDescription,
  serializePlanDescription,
  type PlanDescriptionSchema,
} from '../planDescription'
import { PLAN_DESCRIPTION_TEMPLATES, applyTemplateToDescription, type PlanDescriptionTemplate } from '../planTemplates'

interface PlanDescriptionEditorProps {
  plan: MealPlan | null | undefined
  open: boolean
  onOpenChange: (open: boolean) => void
  onSave: (schema: PlanDescriptionSchema, serialized: string) => void
}

interface TemplateCardProps {
  template: PlanDescriptionTemplate
  isActive: boolean
  onApply: (template: PlanDescriptionTemplate) => void
}

function TemplateCard({ template, isActive, onApply }: TemplateCardProps) {
  return (
    <Card
      className={`flex flex-col gap-3 rounded-2xl border border-border/60 bg-muted/20 p-4 transition ${
        isActive ? 'border-primary/70 shadow-level-2' : 'hover:border-primary/50'
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex flex-col gap-1">
          <div className="text-sm font-semibold text-foreground">{template.title}</div>
          <div className="text-xs text-muted-foreground">{template.summary}</div>
        </div>
        {isActive ? (
          <Badge variant="outline" className="gap-1 text-[10px] uppercase">
            <CheckCircle2Icon className="h-3.5 w-3.5" aria-hidden="true" /> Активен
          </Badge>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
        <span>Тон: {template.tone}</span>
        <span>Пересмотр через {template.reviewIntervalDays} дн.</span>
      </div>
      <Button
        type="button"
        variant={isActive ? 'secondary' : 'primary'}
        size="sm"
        onClick={() => onApply(template)}
        leadingIcon={<Wand2Icon className="h-4 w-4" aria-hidden="true" />}
      >
        {isActive ? 'Применён' : 'Использовать шаблон'}
      </Button>
    </Card>
  )
}

export function PlanDescriptionEditor({ plan, open, onOpenChange, onSave }: PlanDescriptionEditorProps) {
  const [schema, setSchema] = useState<PlanDescriptionSchema>(() => createEmptyPlanDescription())
  const [followUp, setFollowUp] = useState('')

  useEffect(() => {
    if (!plan) {
      setSchema(createEmptyPlanDescription())
      setFollowUp('')
      return
    }
    const parsed = parsePlanDescription(plan.description)
    setSchema(parsed)
    setFollowUp(formatFollowUpToMultiline(parsed.sections.followUpRequirements))
  }, [plan?.id, plan?.description])

  const templateMap = useMemo(() => {
    return PLAN_DESCRIPTION_TEMPLATES.reduce<Record<string, PlanDescriptionTemplate>>((acc, template) => {
      acc[template.slug] = template
      return acc
    }, {})
  }, [])

  const handleApplyTemplate = (template: PlanDescriptionTemplate) => {
    const next = applyTemplateToDescription(template, schema)
    setSchema(next)
    setFollowUp(formatFollowUpToMultiline(next.sections.followUpRequirements))
  }

  const handleSubmit = () => {
    const followUpRequirements = parseFollowUpFromMultiline(followUp)
    const nextSchema: PlanDescriptionSchema = {
      ...schema,
      sections: { ...schema.sections, followUpRequirements },
    }
    const serialized = serializePlanDescription(nextSchema)
    onSave(nextSchema, serialized)
  }

  const handleFieldChange = (field: keyof PlanDescriptionSchema['sections'], value: string) => {
    setSchema(prev => ({
      ...prev,
      sections: {
        ...prev.sections,
        [field]: value,
      },
    }))
  }

  const selectedTemplate = schema.templateSlug ? templateMap[schema.templateSlug] : null

  return (
    <SheetRoot open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        title="Описание плана"
        description="Структурируйте вмешательство по стандарту NCP/ADIME, чтобы масштабировать экспорт и телемедицину."
        footer={
          <SheetFooter>
            <Button type="button" variant="primary" onClick={handleSubmit} leadingIcon={<CheckCircle2Icon className="h-4 w-4" aria-hidden="true" />}>
              Сохранить описание
            </Button>
            <p className="text-xs text-muted-foreground">
              Персонализированный фидбек и самоконтроль повышают приверженность к цифровым нутриционным программам и телемедицине (обзоры 2022–2024).
            </p>
          </SheetFooter>
        }
        className="w-full max-w-[560px]"
      >
        <div className="flex flex-col gap-6">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <LayoutTemplateIcon className="h-4 w-4" aria-hidden="true" /> Библиотека шаблонов
            </div>
            <p className="text-sm text-muted-foreground">
              Выберите шаблон как отправную точку — все поля можно редактировать, добавляя детали клиента, диагноз и стратегию вмешательства.
            </p>
            <div className="flex flex-col gap-3">
              {PLAN_DESCRIPTION_TEMPLATES.map(template => (
                <TemplateCard
                  key={template.slug}
                  template={template}
                  isActive={schema.templateSlug === template.slug}
                  onApply={handleApplyTemplate}
                />
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
              Цель вмешательства
              <textarea
                className="min-h-[80px] rounded-2xl border border-border/60 bg-card/80 px-4 py-3 text-sm text-foreground shadow-inner focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                value={schema.sections.interventionGoal}
                onChange={event => handleFieldChange('interventionGoal', event.target.value)}
                placeholder="Опишите целевое состояние, ожидаемые результаты и сроки."
              />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
              Обоснование (Assessment & Diagnosis)
              <textarea
                className="min-h-[80px] rounded-2xl border border-border/60 bg-card/80 px-4 py-3 text-sm text-foreground shadow-inner focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                value={schema.sections.rationale}
                onChange={event => handleFieldChange('rationale', event.target.value)}
                placeholder="Ключевые выводы оценки, диагнозы NCP, факторы поведения."
              />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
              Ключевые диетпринципы
              <textarea
                className="min-h-[80px] rounded-2xl border border-border/60 bg-card/80 px-4 py-3 text-sm text-foreground shadow-inner focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                value={schema.sections.dietaryPrinciples}
                onChange={event => handleFieldChange('dietaryPrinciples', event.target.value)}
                placeholder="Опишите макросы, распределение приёмов, ограничения и допуски."
              />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
              Рекомендации клиенту (Intervention)
              <textarea
                className="min-h-[100px] rounded-2xl border border-border/60 bg-card/80 px-4 py-3 text-sm text-foreground shadow-inner focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                value={schema.sections.clientRecommendations}
                onChange={event => handleFieldChange('clientRecommendations', event.target.value)}
                placeholder="Добавьте конкретные шаги, образовательные материалы, поведенческие техники."
              />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
              Мониторинг и контроль (Monitoring & Evaluation)
              <textarea
                className="min-h-[100px] rounded-2xl border border-border/60 bg-card/80 px-4 py-3 text-sm text-foreground shadow-inner focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                value={schema.sections.monitoringPlan}
                onChange={event => handleFieldChange('monitoringPlan', event.target.value)}
                placeholder="Укажите метрики самоконтроля, каналы обратной связи, частоту отчётности."
              />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
              Что клиент должен прислать к следующей встрече
              <textarea
                className="min-h-[100px] rounded-2xl border border-border/60 bg-card/80 px-4 py-3 text-sm text-foreground shadow-inner focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                value={followUp}
                onChange={event => setFollowUp(event.target.value)}
                placeholder="Например: вес, дневник питания, фото приёмов пищи, глюкоза/АД. Один пункт на строку."
              />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
              Когда пересмотреть план
              <div className="flex items-center gap-2">
                <CalendarIcon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                <input
                  type="date"
                  className="flex-1 rounded-2xl border border-border/60 bg-card/80 px-4 py-2 text-sm text-foreground shadow-inner focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                  value={schema.sections.nextReviewDate ?? ''}
                  onChange={event => handleFieldChange('nextReviewDate', event.target.value)}
                />
              </div>
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
              Тон коммуникации
              <input
                type="text"
                className="rounded-2xl border border-border/60 bg-card/80 px-4 py-2 text-sm text-foreground shadow-inner focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                value={schema.sections.communicationTone}
                onChange={event => handleFieldChange('communicationTone', event.target.value)}
                placeholder="Например: поддерживающий, экспертный, эмпатичный."
              />
            </label>
            {selectedTemplate ? (
              <p className="text-xs text-muted-foreground">
                Используется шаблон «{selectedTemplate.title}». Добавьте детали истории, цели и барьеры клиента, чтобы персонализировать рекомендации.
              </p>
            ) : null}
          </div>
        </div>
      </SheetContent>
    </SheetRoot>
  )
}

export default PlanDescriptionEditor
