import { differenceInCalendarDays, parseISO } from 'date-fns'

export type PlanDescriptionFormat = 'ncp-adime-v1'

export interface PlanDescriptionSections {
  interventionGoal: string
  rationale: string
  dietaryPrinciples: string
  clientRecommendations: string
  monitoringPlan: string
  followUpRequirements: string[]
  nextReviewDate: string | null
  communicationTone: string
}

export interface PlanDescriptionSchema {
  format: PlanDescriptionFormat
  language: string
  templateSlug?: string | null
  sections: PlanDescriptionSections
  generatedAt?: string
}

export type MealPlanExportFormat = 'client' | 'specialist' | 'table'

const DEFAULT_SECTIONS: PlanDescriptionSections = {
  interventionGoal: '',
  rationale: '',
  dietaryPrinciples: '',
  clientRecommendations: '',
  monitoringPlan: '',
  followUpRequirements: [],
  nextReviewDate: null,
  communicationTone: 'профессиональный поддерживающий',
}

export function createEmptyPlanDescription(): PlanDescriptionSchema {
  return {
    format: 'ncp-adime-v1',
    language: 'ru',
    sections: { ...DEFAULT_SECTIONS },
  }
}

function normalizeFollowUp(value: unknown): string[] {
  if (!value) return []
  if (Array.isArray(value)) {
    return value
      .map(entry => (typeof entry === 'string' ? entry.trim() : String(entry).trim()))
      .filter(Boolean)
  }
  if (typeof value === 'string') {
    return value
      .split(/\r?\n/)
      .map(item => item.trim())
      .filter(Boolean)
  }
  return [String(value).trim()].filter(Boolean)
}

export function parsePlanDescription(raw?: string | null): PlanDescriptionSchema {
  if (!raw) {
    return createEmptyPlanDescription()
  }
  try {
    const payload = JSON.parse(raw) as Partial<PlanDescriptionSchema> & { sections?: Record<string, unknown> }
    const sections = payload.sections ?? {}
    return {
      format: (payload.format as PlanDescriptionFormat) ?? 'ncp-adime-v1',
      language: typeof payload.language === 'string' ? payload.language : 'ru',
      templateSlug: typeof payload.templateSlug === 'string' ? payload.templateSlug : null,
      generatedAt: typeof payload.generatedAt === 'string' ? payload.generatedAt : undefined,
      sections: {
        interventionGoal: typeof sections.interventionGoal === 'string' ? sections.interventionGoal.trim() : '',
        rationale: typeof sections.rationale === 'string' ? sections.rationale.trim() : '',
        dietaryPrinciples: typeof sections.dietaryPrinciples === 'string' ? sections.dietaryPrinciples.trim() : '',
        clientRecommendations:
          typeof sections.clientRecommendations === 'string' ? sections.clientRecommendations.trim() : '',
        monitoringPlan: typeof sections.monitoringPlan === 'string' ? sections.monitoringPlan.trim() : '',
        followUpRequirements: normalizeFollowUp(sections.followUpRequirements),
        nextReviewDate:
          typeof sections.nextReviewDate === 'string' && sections.nextReviewDate
            ? sections.nextReviewDate
            : null,
        communicationTone:
          typeof sections.communicationTone === 'string' && sections.communicationTone
            ? sections.communicationTone
            : DEFAULT_SECTIONS.communicationTone,
      },
    }
  } catch (error) {
    return {
      ...createEmptyPlanDescription(),
      sections: {
        ...DEFAULT_SECTIONS,
        clientRecommendations: raw,
      },
    }
  }
}

export function serializePlanDescription(schema: PlanDescriptionSchema): string {
  const payload: PlanDescriptionSchema = {
    format: schema.format ?? 'ncp-adime-v1',
    language: schema.language ?? 'ru',
    templateSlug: schema.templateSlug ?? null,
    generatedAt: new Date().toISOString(),
    sections: {
      ...schema.sections,
      followUpRequirements: schema.sections.followUpRequirements.filter(Boolean),
      nextReviewDate: schema.sections.nextReviewDate?.trim() || null,
    },
  }
  return JSON.stringify(payload)
}

export function formatFollowUpToMultiline(list: string[]): string {
  return list.join('\n')
}

export function parseFollowUpFromMultiline(value: string): string[] {
  return normalizeFollowUp(value)
}

export function computeDaysUntilReview(nextReviewDate?: string | null): number | null {
  if (!nextReviewDate) return null
  try {
    const parsed = parseISO(nextReviewDate)
    return differenceInCalendarDays(parsed, new Date())
  } catch (error) {
    return null
  }
}
