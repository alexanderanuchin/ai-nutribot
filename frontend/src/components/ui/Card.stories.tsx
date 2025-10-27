import { Card } from './Card'

const meta = {
  title: 'UI/Card',
  component: Card,
}

export default meta

export const Elevations = () => (
  <div className="grid gap-4 md:grid-cols-3">
    <Card elevation={1}>Card elevation 1</Card>
    <Card elevation={2}>Card elevation 2</Card>
    <Card elevation={3}>Card elevation 3</Card>
  </div>
)

export const Interactive = () => (
  <Card interactive elevation={2} className="w-72">
    <h3 className="text-title font-semibold">Интерактивная карточка</h3>
    <p className="text-sm text-muted-foreground">Наведи курсор, чтобы увидеть анимацию.</p>
  </Card>
)