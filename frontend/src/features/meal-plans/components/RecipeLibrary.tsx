import { useDeferredValue, useMemo, useState } from 'react'
import { useDraggable } from '@dnd-kit/core'
import { FlameKindlingIcon, PackageIcon, PlusIcon, UtensilsCrossedIcon } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { Button, Card, SearchInput, SegmentedControl, Skeleton } from '../../../components/ui'
import type { MarketProduct, MarketRecipe } from '../../../types/market'
import { fetchMarketCollection } from '../../../api/market'
import { formatNutritionValue } from '../utils'
import type { PlanSlot } from '../types'
import CreateRecipeDialog from './CreateRecipeDialog'

interface RecipeLibraryProps {
  activeSlot: PlanSlot | null
  onAddItem: (item: { recipeId?: number; productId?: number }) => void
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

interface ProductCardProps {
  product: MarketProduct
  onAdd: () => void
}

function extractProductNutrition(product: MarketProduct) {
  const nutritionSource =
    (product.nutrition as Record<string, unknown> | undefined) ||
    (product.metadata?.nutrition as Record<string, unknown> | undefined) ||
    {}
  const toNumber = (value: unknown): number => {
    if (typeof value === 'number' && Number.isFinite(value)) return value
    if (typeof value === 'string') {
      const parsed = Number.parseFloat(value)
      if (Number.isFinite(parsed)) {
        return parsed
      }
    }
    return 0
  }
  return {
    calories: toNumber(nutritionSource['calories']),
    protein_g: toNumber(nutritionSource['protein_g']),
    fat_g: toNumber(nutritionSource['fat_g']),
    carbs_g: toNumber(nutritionSource['carbs_g']),
  }
}

function ProductCard({ product, onAdd }: ProductCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `product-${product.id}`,
    data: {
      type: 'product',
      productId: product.id,
    },
  })
  const style: React.CSSProperties = {
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    opacity: isDragging ? 0.6 : 1,
  }
  const nutrition = extractProductNutrition(product)
  const priceLabel = useMemo(() => {
    try {
      return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: product.currency || 'RUB',
        maximumFractionDigits: 0,
      }).format(product.price)
    } catch (_error) {
      return `${formatNutritionValue(product.price, 0)} ${product.currency ?? ''}`.trim()
    }
  }, [product.currency, product.price])
  const calorieLabel = product.weight_grams
    ? `${formatNutritionValue(nutrition.calories, 0)} ккал / 100 г`
    : `${formatNutritionValue(nutrition.calories, 0)} ккал за единицу`

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex flex-col gap-2 rounded-2xl border border-border/60 bg-card/90 p-4 shadow-level-1 transition hover:border-primary/60 hover:shadow-level-2"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-foreground">{product.title}</div>
          <div className="text-xs text-muted-foreground">{product.store_name}</div>
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
          <PackageIcon className="h-3.5 w-3.5" aria-hidden="true" />
          {priceLabel}
        </span>
        <span>{calorieLabel}</span>
      </div>
      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
        <span>Б {formatNutritionValue(nutrition.protein_g, 1)} г</span>
        <span>Ж {formatNutritionValue(nutrition.fat_g, 1)} г</span>
        <span>У {formatNutritionValue(nutrition.carbs_g, 1)} г</span>
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

export function RecipeLibrary({ activeSlot, onAddItem }: RecipeLibraryProps) {
  const [search, setSearch] = useState('')
  const [activeTab, setActiveTab] = useState<'recipes' | 'products'>('recipes')
  const [dialogOpen, setDialogOpen] = useState(false)
  const deferredSearch = useDeferredValue(search)
  const queryClient = useQueryClient()
  const queryKey = useMemo(
    () => ['mealPlans', 'library', activeTab, deferredSearch],
    [activeTab, deferredSearch]
  )
  const collectionQuery = useQuery({
    queryKey,
    queryFn: async () => {
      const resource = activeTab
      const { items } = await fetchMarketCollection({
        resource,
        search: deferredSearch,
        pageSize: 15,
      })
      return items
    },
  })

  const recipes = activeTab === 'recipes' ? (collectionQuery.data as MarketRecipe[] | undefined) : undefined
  const products = activeTab === 'products' ? (collectionQuery.data as MarketProduct[] | undefined) : undefined

  const handleRecipeCreated = (recipe: MarketRecipe) => {
    setActiveTab('recipes')
    onAddItem({ recipeId: recipe.id })
    void queryClient.invalidateQueries({ queryKey: ['mealPlans', 'library'] })
  }

  return (
    <Card className="space-y-4 border-border/70 bg-background/60 p-5 shadow-level-1">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-sm font-semibold text-muted-foreground">Библиотека</div>
            <div className="text-xs text-muted-foreground">
              {activeSlot?.date
                ? `Добавление в ${new Date(activeSlot.date).toLocaleDateString('ru-RU', {
                    weekday: 'long',
                    day: 'numeric',
                  })}`
                : 'Выберите ячейку в календаре, чтобы добавить элемент'}
            </div>
          </div>
          <SegmentedControl
            value={activeTab}
            onValueChange={value => {
              if (value === 'recipes' || value === 'products') {
                setActiveTab(value)
              }
            }}
            options={[
              { value: 'recipes', label: 'Рецепты' },
              { value: 'products', label: 'Продукты' },
            ]}
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <SearchInput
            placeholder={
              activeTab === 'recipes'
                ? 'Поиск блюд, например «боул»'
                : 'Поиск продуктов, например «творог»'
            }
            value={search}
            onChange={event => setSearch(event.target.value)}
            onClear={() => setSearch('')}
            loading={collectionQuery.isLoading}
            className="flex-1"
          />
          <Button type="button" variant="secondary" onClick={() => setDialogOpen(true)}>
            <PlusIcon className="mr-2 h-4 w-4" aria-hidden="true" />
            Новый рецепт
          </Button>
        </div>
      </div>
      {collectionQuery.isError ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-4 text-xs text-destructive">
          Не удалось загрузить данные. Попробуйте обновить страницу.
        </div>
      ) : collectionQuery.isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : activeTab === 'recipes' ? (
        recipes && recipes.length > 0 ? (
          <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
            {recipes.map(recipe => (
              <RecipeCard
                key={recipe.id}
                recipe={recipe}
                onAdd={() => {
                  onAddItem({ recipeId: recipe.id })
                }}
              />
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-border/60 bg-muted/20 px-3 py-6 text-center text-xs text-muted-foreground">
            Нет подходящих рецептов. Попробуйте изменить запрос.
          </div>
        )
      ) : products && products.length > 0 ? (
        <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
          {products.map(product => (
            <ProductCard
              key={product.id}
              product={product}
              onAdd={() => {
                onAddItem({ productId: product.id })
              }}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-border/60 bg-muted/20 px-3 py-6 text-center text-xs text-muted-foreground">
          Нет подходящих продуктов. Попробуйте изменить запрос.
        </div>
      )}
      <CreateRecipeDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onRecipeCreated={handleRecipeCreated}
      />
    </Card>
  )
}

export default RecipeLibrary
