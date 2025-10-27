import { Button } from './Button'

const meta = {
  title: 'UI/Button',
  component: Button,
}

export default meta

export const Variants = () => (
  <div className="flex flex-wrap items-center gap-4">
    <Button>Primary</Button>
    <Button variant="secondary">Secondary</Button>
    <Button variant="outline">Outline</Button>
    <Button variant="ghost">Ghost</Button>
    <Button variant="success">Success</Button>
    <Button variant="destructive">Destructive</Button>
  </div>
)

export const Sizes = () => (
  <div className="flex items-center gap-4">
    <Button size="sm">Small</Button>
    <Button size="md">Medium</Button>
    <Button size="lg">Large</Button>
  </div>
)

export const Loading = () => <Button loading>Загрузка</Button>