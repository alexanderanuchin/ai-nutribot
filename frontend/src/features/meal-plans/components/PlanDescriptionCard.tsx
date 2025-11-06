import { AlertTriangleIcon, ClipboardListIcon, DownloadIcon } from 'lucide-react'

import { Badge, Button, Card } from '../../../components/ui'
import type { MealPlan } from '../../../types/meal-plan'
import {
  computeDaysUntilReview,
  parsePlanDescription,
  type MealPlanExportFormat,
  type PlanDescriptionSchema,
} from '../planDescription'

interface PlanDescriptionCardProps {
  plan: MealPlan | null | undefined
  onEdit: () => void
  onExport: (format: MealPlanExportFormat) => void
  isExporting?: MealPlanExportFormat | null
}

function Section({ title, content }: { title: string; content: string }) {
  return (
    <div className="space-y-1">
      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</div>
      <div className="text-sm leading-6 text-foreground whitespace-pre-line">{content || '—'}</div>
    </div>
  )
}

export function PlanDescriptionCard({ plan, onEdit, onExport, isExporting = null }: PlanDescriptionCardProps) {
  const schema: PlanDescriptionSchema = parsePlanDescription(plan?.description)
  const sections = schema.sections
  const daysToReview = computeDaysUntilReview(sections.nextReviewDate)
  const exportsDisabled = !plan
  const nextReviewDateText = (() => {
    if (!sections.nextReviewDate) return 'По согласованию'
    const parsed = new Date(sections.nextReviewDate)
    if (Number.isNaN(parsed.getTime())) {
      return sections.nextReviewDate
    }
    return parsed.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    })
  })()
  const reviewBadge = (() => {
    if (daysToReview == null) return null
    if (daysToReview < 0) {
      return (
        <Badge variant="destructive" className="gap-1 text-[10px] uppercase">
          <AlertTriangleIcon className="h-3.5 w-3.5" aria-hidden="true" /> Просрочен {Math.abs(daysToReview)} дн.
        </Badge>
      )
    }
    if (daysToReview <= 3) {
      return (
        <Badge variant="secondary" className="gap-1 text-[10px] uppercase">
          <AlertTriangleIcon className="h-3.5 w-3.5" aria-hidden="true" /> Контроль через {daysToReview} дн.
        </Badge>
      )
    }
    return (
      <Badge variant="outline" className="gap-1 text-[10px] uppercase">
        <ClipboardListIcon className="h-3.5 w-3.5" aria-hidden="true" /> Пересмотр {sections.nextReviewDate}
      </Badge>
    )
  })()

  return (
    <Card className="flex flex-col gap-4 border-border/70 bg-background/60 p-5 shadow-level-1">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-muted-foreground">Описание плана</div>
          <div className="text-foreground">NCP / ADIME структура вмешательства</div>
          <p className="mt-2 max-w-xl text-xs text-muted-foreground">
            Стандартизированное описание облегчает экспорт в PDF/JSON/CSV и поддерживает персонализированный фидбек в телемедицине.
          </p>
          {plan ? null : (
            <p className="mt-1 text-xs text-muted-foreground">
              Создайте или выберите план, чтобы сохранить описание вмешательства и готовить экспортируемые файлы.
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {reviewBadge}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            leadingIcon={<span aria-hidden="true">🖉</span>}
            onClick={onEdit}
            disabled={exportsDisabled}
          >
            Редактировать
          </Button>
        </div>
      </div>

      <div className="grid gap-4">
        <Section title="Цель вмешательства" content={sections.interventionGoal} />
        <Section title="Обоснование" content={sections.rationale} />
        <Section title="Ключевые диетпринципы" content={sections.dietaryPrinciples} />
        <Section title="Рекомендации клиенту" content={sections.clientRecommendations} />
        <Section title="Мониторинг и контроль" content={sections.monitoringPlan} />
        <Section title="Тон коммуникации" content={sections.communicationTone} />
        <Section title="Когда пересмотреть план" content={nextReviewDateText} />
        <div className="space-y-1">
          <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Что прислать к следующей встрече</div>
          {sections.followUpRequirements.length > 0 ? (
            <ul className="list-disc space-y-1 pl-5 text-sm leading-6 text-foreground">
              {sections.followUpRequirements.map(item => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-muted-foreground">Добавьте параметры самоконтроля — вес, дневник, фото приёмов пищи, глюкоза/АД.</div>
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-border/60 bg-card/70 p-4 text-xs text-muted-foreground">
        Персонализированный фидбек и регулярный самоконтроль — ключевые драйверы приверженности в цифровых нутриционных сервисах и телемедицине (обзоры 2022–2025).
      </div>

      <div className="space-y-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Экспортировать</div>
        <div className="grid gap-2 md:grid-cols-3">
          {(
            [
              { format: 'client' as MealPlanExportFormat, label: 'Для клиента (HTML)' },
              { format: 'specialist' as MealPlanExportFormat, label: 'Для специалиста (JSON NCP)' },
              { format: 'table' as MealPlanExportFormat, label: 'Табличный (CSV)' },
            ] as const
          ).map(option => (
            <Button
              key={option.format}
              type="button"
              variant="outline"
              size="sm"
              loading={isExporting === option.format}
              disabled={exportsDisabled}
              onClick={() => onExport(option.format)}
              leadingIcon={<DownloadIcon className="h-4 w-4" aria-hidden="true" />}
            >
              {option.label}
            </Button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          • HTML содержит клиентские поля и расписание. • JSON — полный профиль NCP/ADIME с нутриентами и графиком.
          • CSV — таблица по дням: дата, тип приёма, блюдо/продукт, порции, калории и макросы.
        </p>
      </div>
    </Card>
  )
}

export default PlanDescriptionCard
