import { ProductCard } from './ProductCard'
import type { MarketProduct } from '../../../types/market'

const meta = {
  title: 'Market/ProductCard',
  component: ProductCard,
}

export default meta

const sampleProduct: MarketProduct = {
  id: 1,
  title: 'Набор суперфудов',
  subtitle: 'Чиа, киноа, ягоды годжи',
  description: 'Сбалансированный набор для утренних смузи и боулов.',
  price: 1290,
  currency: 'RUB',
  unit: 'упак.',
  price_original: 1590,
  discount_percent: 20,
  image_url: 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80',
  brand: 'NutriFarm',
  badges: ['organic', 'vegan'],
  rating: 4.7,
  rating_count: 132,
  is_in_cart: false,
  available: true,
}

export const Default = () => <ProductCard item={sampleProduct} />

export const OutOfStock = () => (
  <ProductCard
    item={{
      ...sampleProduct,
      id: 2,
      title: 'Протеиновый брауни',
      available: false,
      discount_percent: null,
      price_original: null,
    }}
  />
)