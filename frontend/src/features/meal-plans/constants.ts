import {
  CoffeeIcon,
  CupSodaIcon,
  MoonIcon,
  SandwichIcon,
  SoupIcon,
  SunriseIcon,
  UtensilsCrossedIcon,
} from 'lucide-react'

import type { MealTypeId } from '../../types/meal-plan'

type MealTypeConfig = {
  id: MealTypeId
  label: string
  description: string
  icon: typeof SunriseIcon
}

export const MEAL_TYPES: MealTypeConfig[] = [
  {
    id: 'breakfast',
    label: 'Завтрак',
    description: 'Начните день с энергии',
    icon: SunriseIcon,
  },
  {
    id: 'second_breakfast',
    label: 'Второй завтрак',
    description: 'Лёгкий перекус до обеда',
    icon: CoffeeIcon,
  },
  {
    id: 'brunch',
    label: 'Бранч',
    description: 'Комбо позднего завтрака и ланча',
    icon: SandwichIcon,
  },
  {
    id: 'lunch',
    label: 'Обед',
    description: 'Основной приём пищи днём',
    icon: SoupIcon,
  },
  {
    id: 'snack',
    label: 'Перекус',
    description: 'Поддержите уровень энергии',
    icon: CupSodaIcon,
  },
  {
    id: 'dinner',
    label: 'Ужин',
    description: 'Тёплый финал дня',
    icon: UtensilsCrossedIcon,
  },
  {
    id: 'supper',
    label: 'Поздний ужин',
    description: 'Лёгкий приём пищи перед сном',
    icon: MoonIcon,
  },
]

export const DEFAULT_WEEK_DAYS = 7
