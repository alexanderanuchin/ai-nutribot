import { useDeferredValue, useMemo, useState } from 'react'
import { useDraggable } from '@dnd-kit/core'
import { FlameKindlingIcon, UtensilsCrossedIcon } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'

import { Card, SearchInput, Skeleton } from '../../../components/ui'
import type { MarketRecipe } from '../../../types/market'
import { fetchMarketCollection } from '../../../api/market'
import { formatNutritionValue } from '../utils'
import type { PlanSlot } from '../types'

interface RecipeLibraryProps {
  activeSlot: PlanSlot | null
  onAddRecipe: (recipeId: number) => void
}

function RecipeCard({ recipe, onAdd }: { recipe: MarketRecipe; onAdd: () => void }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `recipe-${recipe.id}`,
    data: {
      type: 'recipe',
      recipeId: recipe.id,
    },
  })
  const style: React.CSSProperties = {
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    opacity: isDragging ? 0.6 : 1,
  }
  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex flex-col gap-2 rounded-2xl border border-border/60 bg-card/90 p-4 shadow-level-1 transition hover:border-primary/60 hover:shadow-level-2"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-foreground">{recipe.title}</div>
          <div className="text-xs text-muted-foreground">{recipe.store_name}</div>
        </div>
        <button
          type="button"
          className="rounded-full border border-border/60 px-3 py-1 text-xs font-semibold text-muted-foreground transition hover:border-primary hover:text-primary"
          onClick={onAdd}
        >
          Добавить
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <FlameKindlingIcon className="h-3.5 w-3.5" aria-hidden="true" />
          {formatNutritionValue(recipe.calories, 0)} ккал
        </span>
        <span className="inline-flex items-center gap-1">
          <UtensilsCrossedIcon className="h-3.5 w-3.5" aria-hidden="true" />
          {recipe.cooking_time_minutes} мин · {recipe.servings} порций
        </span>
      </div>
      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
        <span>Б {formatNutritionValue(recipe.protein_g, 1)} г</span>
        <span>Ж {formatNutritionValue(recipe.fat_g, 1)} г</span>
        <span>У {formatNutritionValue(recipe.carbs_g, 1)} г</span>
      </div>
      <button
        type="button"
        className="mt-1 inline-flex w-max items-center gap-2 rounded-full bg-muted/20 px-3 py-1 text-[11px] font-semibold text-muted-foreground"
        {...attributes}
        {...listeners}
      >
        Перетащить в календарь
      </button>
    </div>
  )
}

export function RecipeLibrary({ activeSlot, onAddRecipe }: RecipeLibraryProps) {
  const [search, setSearch] = useState('')
  const deferredSearch = useDeferredValue(search)
  const queryKey = useMemo(() => ['mealPlans', 'library', deferredSearch], [deferredSearch])
  const recipesQuery = useQuery({
    queryKey,
    queryFn: async () => {
      const { items } = await fetchMarketCollection({
        resource: 'recipes',
        search: deferredSearch,
        pageSize: 15,
      })
      return items
    },
  })

  return (
    <Card className="space-y-4 border-border/70 bg-background/60 p-5 shadow-level-1">
      <div className="flex items-center justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-muted-foreground">База рецептов</div>
          <div className="text-xs text-muted-foreground">
            {activeSlot?.date
              ? `Добавление в ${new Date(activeSlot.date).toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric' })}`
              : 'Выберите ячейку в календаре, чтобы добавить рецепт'}
          </div>
        </div>
      </div>
      <SearchInput
        placeholder="Поиск блюд, например «боул»"
        value={search}
        onChange={event => setSearch(event.target.value)}
        onClear={() => setSearch('')}
        loading={recipesQuery.isLoading}
      />
      {recipesQuery.isError ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-4 text-xs text-destructive">
          Не удалось загрузить рецепты. Попробуйте обновить страницу.
        </div>
      ) : recipesQuery.isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : recipesQuery.data && recipesQuery.data.length > 0 ? (
        <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
          {recipesQuery.data.map(recipe => (
            <RecipeCard
              key={recipe.id}
              recipe={recipe}
              onAdd={() => {
                onAddRecipe(recipe.id)
              }}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-border/60 bg-muted/20 px-3 py-6 text-center text-xs text-muted-foreground">
          Нет подходящих рецептов. Попробуйте изменить запрос.
        </div>
      )}
    </Card>
  )
}

export default RecipeLibrary
