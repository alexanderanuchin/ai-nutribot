import * as Dialog from '@radix-ui/react-dialog'
import { AnimatePresence, motion } from 'framer-motion'
import { ClockIcon, FlameKindlingIcon, LeafIcon, UsersIcon, UtensilsCrossedIcon, XIcon } from 'lucide-react'
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'

import { Badge, Button, IconButton, Skeleton } from '../../../components/ui'
import { fetchMarketRecipe } from '../../../api/market'
import type { MarketRecipe } from '../../../types/market'
import { formatNutritionValue } from '../utils'

interface RecipeDetailsDialogProps {
  recipeId: number | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onAddToPlan?: (recipeId: number) => void
}

const overlayVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
}

const contentVariants = {
  hidden: { opacity: 0, scale: 0.96 },
  visible: { opacity: 1, scale: 1 },
}

function IngredientRow({ ingredient }: { ingredient: MarketRecipe['ingredients'][number] }) {
  const quantityLabel = useMemo(() => {
    if (ingredient.quantity == null || ingredient.quantity === 0) return null
    const formatted = Number.isInteger(ingredient.quantity)
      ? ingredient.quantity
      : formatNutritionValue(ingredient.quantity, 1)
    return ingredient.unit ? `${formatted} ${ingredient.unit}` : `${formatted}`
  }, [ingredient.quantity, ingredient.unit])

  return (
    <li className="flex items-start justify-between gap-3 rounded-2xl border border-border/40 bg-muted/10 px-3 py-2">
      <span className="text-sm text-foreground">{ingredient.name}</span>
      <span className="text-xs font-medium text-muted-foreground">{quantityLabel}</span>
    </li>
  )
}

function StepRow({ step }: { step: MarketRecipe['steps'][number] }) {
  return (
    <li className="flex gap-3 rounded-2xl border border-border/40 bg-card/60 px-3 py-3">
      <span className="mt-0.5 h-6 w-6 flex-shrink-0 rounded-full bg-primary/10 text-center text-sm font-semibold text-primary">
        {step.order}
      </span>
      <div>
        <div className="text-sm font-semibold text-foreground">{step.title}</div>
        <p className="mt-1 whitespace-pre-line text-sm text-muted-foreground">{step.instructions}</p>
      </div>
    </li>
  )
}

export function RecipeDetailsDialog({ recipeId, open, onOpenChange, onAddToPlan }: RecipeDetailsDialogProps) {
  const query = useQuery({
    queryKey: ['mealPlans', 'library', 'recipe', recipeId],
    queryFn: async () => {
      if (!recipeId) throw new Error('recipeId is required')
      return fetchMarketRecipe(recipeId)
    },
    enabled: open && recipeId != null,
    staleTime: 60 * 1000,
  })

  const recipe = query.data

  const handleAddToPlan = () => {
    if (!recipe || !onAddToPlan) return
    onAddToPlan(recipe.id)
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open ? (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <motion.div
                className="fixed inset-0 z-[120] bg-background/80 backdrop-blur-sm"
                initial="hidden"
                animate="visible"
                exit="hidden"
                variants={overlayVariants}
                transition={{ duration: 0.18 }}
              />
            </Dialog.Overlay>
            <Dialog.Content asChild forceMount>
              <motion.div
                className="fixed left-1/2 top-1/2 z-[121] h-[min(90vh,720px)] w-[min(960px,96vw)] -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-3xl border border-border/60 bg-background/95 shadow-level-3"
                role="dialog"
                aria-modal="true"
                initial="hidden"
                animate="visible"
                exit="hidden"
                variants={contentVariants}
                transition={{ duration: 0.2 }}
              >
                <div className="flex h-full flex-col">
                  <div className="flex items-start justify-between gap-4 border-b border-border/40 px-6 py-4">
                    <div className="space-y-1">
                      <Dialog.Title className="text-lg font-semibold text-foreground">
                        {recipe?.title ?? 'Загрузка рецепта...'}
                      </Dialog.Title>
                      <Dialog.Description className="text-sm text-muted-foreground">
                        {recipe ? `${recipe.store_name} · ${recipe.cooking_time_minutes} мин · ${recipe.servings} порций` : ''}
                      </Dialog.Description>
                      {recipe?.tags && recipe.tags.length > 0 ? (
                        <div className="flex flex-wrap gap-2 pt-1">
                          {recipe.tags.map(tag => (
                            <Badge key={tag} variant="secondary" className="text-[11px] font-medium">
                              #{tag}
                            </Badge>
                          ))}
                        </div>
                      ) : null}
                    </div>
                    <Dialog.Close asChild>
                      <IconButton variant="ghost" aria-label="Закрыть карточку рецепта">
                        <XIcon className="h-5 w-5" aria-hidden="true" />
                      </IconButton>
                    </Dialog.Close>
                  </div>
                  <div className="flex-1 overflow-y-auto px-6 py-4">
                    {query.isLoading ? (
                      <div className="space-y-4">
                        <Skeleton className="h-48 w-full rounded-3xl" />
                        <Skeleton className="h-4 w-1/2" />
                        <Skeleton className="h-4 w-2/3" />
                      </div>
                    ) : query.isError ? (
                      <div className="rounded-2xl border border-destructive/40 bg-destructive/10 px-4 py-6 text-sm text-destructive">
                        Не удалось загрузить рецепт. Попробуйте позже.
                      </div>
                    ) : recipe ? (
                      <div className="space-y-6">
                        {recipe.hero_image_url ? (
                          <div className="overflow-hidden rounded-3xl border border-border/40">
                            <img
                              src={recipe.hero_image_url}
                              alt={`Фото блюда ${recipe.title}`}
                              className="h-56 w-full object-cover"
                              loading="lazy"
                            />
                          </div>
                        ) : null}
                        {recipe.summary ? (
                          <p className="text-sm text-muted-foreground">{recipe.summary}</p>
                        ) : null}
                        <div className="grid gap-3 sm:grid-cols-2">
                          <div className="flex items-center gap-2 rounded-2xl border border-border/40 bg-card/70 px-3 py-2 text-sm text-foreground">
                            <FlameKindlingIcon className="h-4 w-4 text-primary" aria-hidden="true" />
                            {formatNutritionValue(recipe.calories, 0)} ккал / порция
                          </div>
                          <div className="flex items-center gap-2 rounded-2xl border border-border/40 bg-card/70 px-3 py-2 text-sm text-foreground">
                            <UtensilsCrossedIcon className="h-4 w-4 text-primary" aria-hidden="true" />
                            {recipe.cooking_time_minutes} минут на приготовление
                          </div>
                          <div className="flex items-center gap-2 rounded-2xl border border-border/40 bg-card/70 px-3 py-2 text-sm text-foreground">
                            <UsersIcon className="h-4 w-4 text-primary" aria-hidden="true" />
                            {recipe.servings} порций
                          </div>
                          {recipe.difficulty ? (
                            <div className="flex items-center gap-2 rounded-2xl border border-border/40 bg-card/70 px-3 py-2 text-sm text-foreground">
                              <ClockIcon className="h-4 w-4 text-primary" aria-hidden="true" />
                              Сложность: {recipe.difficulty}
                            </div>
                          ) : null}
                        </div>
                        <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                          <span>Б {formatNutritionValue(recipe.protein_g, 1)} г</span>
                          <span>Ж {formatNutritionValue(recipe.fat_g, 1)} г</span>
                          <span>У {formatNutritionValue(recipe.carbs_g, 1)} г</span>
                        </div>
                        <section aria-labelledby="ingredients-title" className="space-y-3">
                          <div className="flex items-center justify-between">
                            <h3 id="ingredients-title" className="text-sm font-semibold text-foreground">
                              Ингредиенты
                            </h3>
                            <Badge variant="outline" className="gap-1 text-[11px]">
                              {recipe.ingredients.length} позиций
                            </Badge>
                          </div>
                          <ul className="grid gap-2 md:grid-cols-2">
                            {recipe.ingredients.map(ingredient => (
                              <IngredientRow key={ingredient.id} ingredient={ingredient} />
                            ))}
                          </ul>
                        </section>
                        <section aria-labelledby="steps-title" className="space-y-3">
                          <div className="flex items-center justify-between">
                            <h3 id="steps-title" className="text-sm font-semibold text-foreground">
                              Шаги приготовления
                            </h3>
                            <Badge variant="secondary" className="gap-1 text-[11px]">
                              {recipe.steps.length} шагов
                            </Badge>
                          </div>
                          <ol className="space-y-2">
                            {recipe.steps.map(step => (
                              <StepRow key={step.id} step={step} />
                            ))}
                          </ol>
                        </section>
                        {recipe.description ? (
                          <section aria-labelledby="notes-title" className="space-y-2">
                            <h3 id="notes-title" className="text-sm font-semibold text-foreground">
                              Описание
                            </h3>
                            <p className="whitespace-pre-line text-sm text-muted-foreground">{recipe.description}</p>
                          </section>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                  <div className="flex items-center justify-between gap-4 border-t border-border/40 px-6 py-4">
                    {recipe?.metadata?.dietary_tags && Array.isArray(recipe.metadata.dietary_tags) ? (
                      <div className="hidden flex-wrap items-center gap-2 text-xs text-muted-foreground sm:flex">
                        <LeafIcon className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                        {(recipe.metadata.dietary_tags as string[]).join(' · ')}
                      </div>
                    ) : (
                      <div className="text-xs text-muted-foreground">{recipe?.store_city}</div>
                    )}
                    <div className="flex items-center gap-3">
                      <Dialog.Close asChild>
                        <Button type="button" variant="ghost">
                          Закрыть
                        </Button>
                      </Dialog.Close>
                      <Button type="button" variant="primary" onClick={handleAddToPlan} disabled={!recipe}>
                        Добавить в план
                      </Button>
                    </div>
                  </div>
                </div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        ) : null}
      </AnimatePresence>
    </Dialog.Root>
  )
}

export default RecipeDetailsDialog
