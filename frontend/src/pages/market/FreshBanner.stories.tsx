import { FreshBanner } from './MarketCollectionPage'

const meta = {
  title: 'Market/FreshBanner',
  component: FreshBanner,
}

export default meta

export const Default = () => (
  <div className="max-w-xl">
    <FreshBanner
      visible
      count={5}
      resource="products"
      refreshing={false}
      onRefresh={() => undefined}
      onDismiss={() => undefined}
    />
  </div>
)