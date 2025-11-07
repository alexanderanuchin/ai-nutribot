import { useEffect, useMemo, useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { AnimatePresence, motion } from 'framer-motion'
import { Loader2Icon, PlusIcon } from 'lucide-react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { Button, useToast } from '../../../components/ui'
import type { MarketRecipe } from '../../../types/market'
import { createRecipe, fetchMarketCollection } from '../../../api/market'

interface CreateRecipeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onRecipeCreated: (recipe: MarketRecipe) => void
}

interface FormState {
  title: string
  description: string
  calories: string
  protein: string
  fat: string
  carbs: string
  ingredients: string
  storeId: string
}

interface FormErrors {
  title?: string
  storeId?: string
  calories?: string
  protein?: string
  fat?: string
  carbs?: string
}

const INITIAL_STATE: FormState = {
  title: '',
  description: '',
  calories: '',
  protein: '',
  fat: '',
  carbs: '',
  ingredients: '',
  storeId: '',
}

function transliterate(value: string): string {
  const map: Record<string, string> = {
    а: 'a',
    б: 'b',
    в: 'v',
    г: 'g',
    д: 'd',
    е: 'e',
    ё: 'e',
    ж: 'zh',
    з: 'z',
    и: 'i',
    й: 'i',
    к: 'k',
    л: 'l',
    м: 'm',
    н: 'n',
    о: 'o',
    п: 'p',
    р: 'r',
    с: 's',
    т: 't',
    у: 'u',
    ф: 'f',
    х: 'h',
    ц: 'ts',
    ч: 'ch',
    ш: 'sh',
    щ: 'sch',
    ъ: '',
    ы: 'y',
    ь: '',
    э: 'e',
    ю: 'yu',
    я: 'ya',
  }
  return Array.from(value)
    .map(char => {
      const lower = char.toLowerCase()
      const replacement = map[lower]
      if (replacement) {
        return char === lower ? replacement : replacement.charAt(0).toUpperCase() + replacement.slice(1)
      }
      return char
    })
    .join('')
}

function slugifyTitle(title: string): string {
  const transliterated = transliterate(title)
  const normalized = transliterated
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
  const slug = normalized.replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
  const base = slug || 'recipe'
  return `${base}-${Date.now()}`
}

function parseNumber(value: string): number | null {
  if (!value.trim()) return 0
  const parsed = Number.parseFloat(value.replace(',', '.'))
  if (Number.isNaN(parsed)) return null
  return parsed
}

function validateForm(state: FormState): FormErrors {
  const errors: FormErrors = {}
  if (!state.title.trim()) {
    errors.title = 'Название обязательно'
  }
  if (!state.storeId) {
    errors.storeId = 'Выберите магазин'
  }
  const calories = parseNumber(state.calories)
  if (calories === null || calories < 0) {
    errors.calories = 'Введите неотрицательное число'
  }
  const protein = parseNumber(state.protein)
  if (protein === null || protein < 0) {
    errors.protein = 'Введите неотрицательное число'
  }
  const fat = parseNumber(state.fat)
  if (fat === null || fat < 0) {
    errors.fat = 'Введите неотрицательное число'
  }
  const carbs = parseNumber(state.carbs)
  if (carbs === null || carbs < 0) {
    errors.carbs = 'Введите неотрицательное число'
  }
  return errors
}

export function CreateRecipeDialog({ open, onOpenChange, onRecipeCreated }: CreateRecipeDialogProps) {
  const { notify } = useToast()
  const [formState, setFormState] = useState<FormState>(INITIAL_STATE)
  const [formErrors, setFormErrors] = useState<FormErrors>({})

  const storesQuery = useQuery({
    queryKey: ['mealPlans', 'createRecipe', 'stores'],
    queryFn: async () => {
      const { items } = await fetchMarketCollection({
        resource: 'stores',
        filters: { mine: '1' },
        pageSize: 50,
      })
      return items
    },
    enabled: open,
    staleTime: 1000 * 60 * 3,
  })

  useEffect(() => {
    if (!open) {
      setFormState(INITIAL_STATE)
      setFormErrors({})
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    if (formState.storeId) return
    const items = storesQuery.data
    if (!items || items.length === 0) return
    setFormState(prev => ({ ...prev, storeId: String(items[0].id) }))
  }, [open, storesQuery.data, formState.storeId])

  const createRecipeMutation = useMutation({
    mutationFn: async () => {
      const errors = validateForm(formState)
      setFormErrors(errors)
      if (Object.keys(errors).length > 0) {
        throw new Error('validation')
      }
      const payload = {
        store: Number(formState.storeId),
        title: formState.title.trim(),
        slug: slugifyTitle(formState.title),
        summary: formState.description.trim() || undefined,
        cooking_time_minutes: 0,
        servings: 1,
        is_public: false,
        metadata: {
          nutrition: {
            calories: parseNumber(formState.calories) ?? 0,
            protein_g: parseNumber(formState.protein) ?? 0,
            fat_g: parseNumber(formState.fat) ?? 0,
            carbs_g: parseNumber(formState.carbs) ?? 0,
          },
          description: formState.description.trim() || undefined,
          ingredients_text: formState.ingredients.trim() || undefined,
        },
      }
      return createRecipe(payload)
    },
    onSuccess: recipe => {
      notify({
        title: 'Рецепт создан',
        description: 'Новый рецепт добавлен в библиотеку.',
        tone: 'success',
      })
      onRecipeCreated(recipe)
      onOpenChange(false)
    },
    onError: error => {
      if (error instanceof Error && error.message === 'validation') {
        return
      }
      const message = (error as any)?.response?.data?.detail
      if ((error as any)?.response?.status === 403) {
        notify({
          title: 'Нельзя создать рецепт',
          description: 'Учетная запись не привязана к магазину или нет прав оператора.',
          tone: 'destructive',
        })
        return
      }
      notify({
        title: 'Ошибка создания рецепта',
        description: typeof message === 'string' ? message : 'Попробуйте еще раз позже.',
        tone: 'destructive',
      })
    },
  })

  const hasStores = useMemo(() => (storesQuery.data?.length ?? 0) > 0, [storesQuery.data])

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = event.target
    setFormState(prev => ({ ...prev, [name]: value }))
    setFormErrors(prev => ({ ...prev, [name]: undefined }))
  }

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    createRecipeMutation.mutate()
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open ? (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild>
              <motion.div
                className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                aria-hidden="true"
              />
            </Dialog.Overlay>
            <Dialog.Content asChild>
              <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 24 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
                className="fixed inset-x-0 top-[10vh] z-50 mx-auto flex max-h-[80vh] w-[min(640px,92%)] flex-col overflow-y-auto rounded-3xl border border-border/70 bg-background/95 p-6 shadow-2xl backdrop-blur-xl"
                role="dialog"
                aria-modal="true"
              >
                <Dialog.Title className="text-lg font-semibold text-foreground">Новый рецепт</Dialog.Title>
                <Dialog.Description className="mt-1 text-sm text-muted-foreground">
                  Заполните данные, чтобы добавить авторский рецепт в библиотеку и сразу использовать его в плане.
                </Dialog.Description>
                <form className="mt-6 flex flex-col gap-4" onSubmit={handleSubmit}>
                  <div className="flex flex-col gap-2">
                    <label htmlFor="recipe-title" className="text-sm font-medium text-foreground">
                      Название
                    </label>
                    <input
                      id="recipe-title"
                      name="title"
                      type="text"
                      required
                      value={formState.title}
                      onChange={handleInputChange}
                      className="w-full rounded-2xl border border-border/70 bg-muted/20 px-4 py-2.5 text-sm text-foreground shadow-inner focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
                      placeholder="Например, Омлет с зеленью"
                    />
                    {formErrors.title ? (
                      <span className="text-xs text-destructive">{formErrors.title}</span>
                    ) : null}
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="flex flex-col gap-2">
                      <label htmlFor="recipe-store" className="text-sm font-medium text-foreground">
                        Магазин
                      </label>
                      <select
                        id="recipe-store"
                        name="storeId"
                        value={formState.storeId}
                        onChange={handleInputChange}
                        className="w-full rounded-2xl border border-border/70 bg-muted/20 px-4 py-2.5 text-sm text-foreground shadow-inner focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
                      >
                        {!hasStores ? (
                          <option value="" disabled>
                            Нет доступных магазинов
                          </option>
                        ) : null}
                        {storesQuery.data?.map(store => (
                          <option key={store.id} value={store.id}>
                            {store.name}
                          </option>
                        ))}
                      </select>
                      {formErrors.storeId ? (
                        <span className="text-xs text-destructive">{formErrors.storeId}</span>
                      ) : null}
                    </div>
                    <div className="flex flex-col gap-2">
                      <label htmlFor="recipe-calories" className="text-sm font-medium text-foreground">
                        Калории (на порцию)
                      </label>
                      <input
                        id="recipe-calories"
                        name="calories"
                        type="number"
                        min="0"
                        step="1"
                        value={formState.calories}
                        onChange={handleInputChange}
                        className="w-full rounded-2xl border border-border/70 bg-muted/20 px-4 py-2.5 text-sm text-foreground shadow-inner focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
                        placeholder="400"
                      />
                      {formErrors.calories ? (
                        <span className="text-xs text-destructive">{formErrors.calories}</span>
                      ) : null}
                    </div>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div className="flex flex-col gap-2">
                      <label htmlFor="recipe-protein" className="text-sm font-medium text-foreground">
                        Белки, г
                      </label>
                      <input
                        id="recipe-protein"
                        name="protein"
                        type="number"
                        min="0"
                        step="0.1"
                        value={formState.protein}
                        onChange={handleInputChange}
                        className="w-full rounded-2xl border border-border/70 bg-muted/20 px-4 py-2.5 text-sm text-foreground shadow-inner focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
                        placeholder="30"
                      />
                      {formErrors.protein ? (
                        <span className="text-xs text-destructive">{formErrors.protein}</span>
                      ) : null}
                    </div>
                    <div className="flex flex-col gap-2">
                      <label htmlFor="recipe-fat" className="text-sm font-medium text-foreground">
                        Жиры, г
                      </label>
                      <input
                        id="recipe-fat"
                        name="fat"
                        type="number"
                        min="0"
                        step="0.1"
                        value={formState.fat}
                        onChange={handleInputChange}
                        className="w-full rounded-2xl border border-border/70 bg-muted/20 px-4 py-2.5 text-sm text-foreground shadow-inner focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
                        placeholder="20"
                      />
                      {formErrors.fat ? <span className="text-xs text-destructive">{formErrors.fat}</span> : null}
                    </div>
                    <div className="flex flex-col gap-2">
                      <label htmlFor="recipe-carbs" className="text-sm font-medium text-foreground">
                        Углеводы, г
                      </label>
                      <input
                        id="recipe-carbs"
                        name="carbs"
                        type="number"
                        min="0"
                        step="0.1"
                        value={formState.carbs}
                        onChange={handleInputChange}
                        className="w-full rounded-2xl border border-border/70 bg-muted/20 px-4 py-2.5 text-sm text-foreground shadow-inner focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
                        placeholder="35"
                      />
                      {formErrors.carbs ? <span className="text-xs text-destructive">{formErrors.carbs}</span> : null}
                    </div>
                  </div>
                  <div className="flex flex-col gap-2">
                    <label htmlFor="recipe-description" className="text-sm font-medium text-foreground">
                      Описание
                    </label>
                    <textarea
                      id="recipe-description"
                      name="description"
                      value={formState.description}
                      onChange={handleInputChange}
                      className="min-h-[96px] w-full rounded-2xl border border-border/70 bg-muted/20 px-4 py-2.5 text-sm text-foreground shadow-inner focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
                      placeholder="Расскажите коротко о блюде"
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <label htmlFor="recipe-ingredients" className="text-sm font-medium text-foreground">
                      Ингредиенты (произвольный текст)
                    </label>
                    <textarea
                      id="recipe-ingredients"
                      name="ingredients"
                      value={formState.ingredients}
                      onChange={handleInputChange}
                      className="min-h-[96px] w-full rounded-2xl border border-border/70 bg-muted/20 px-4 py-2.5 text-sm text-foreground shadow-inner focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
                      placeholder="Например: 2 яйца, 30 г шпината, 10 г сливочного масла"
                    />
                  </div>
                  {!hasStores ? (
                    <div className="rounded-2xl border border-amber-300 bg-amber-100/40 px-4 py-3 text-sm text-amber-800">
                      Чтобы создавать рецепты, нужна активная витрина магазина. Обратитесь к администратору или создайте магазин в разделе «Маркет».
                    </div>
                  ) : null}
                  <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <Dialog.Close asChild>
                      <Button type="button" variant="ghost" className="sm:w-auto">
                        Отмена
                      </Button>
                    </Dialog.Close>
                    <Button
                      type="submit"
                      disabled={createRecipeMutation.isPending || !hasStores}
                      className="inline-flex items-center justify-center gap-2"
                    >
                      {createRecipeMutation.isPending ? (
                        <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden="true" />
                      ) : (
                        <PlusIcon className="h-4 w-4" aria-hidden="true" />
                      )}
                      Сохранить рецепт
                    </Button>
                  </div>
                </form>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        ) : null}
      </AnimatePresence>
    </Dialog.Root>
  )
}

export default CreateRecipeDialog
