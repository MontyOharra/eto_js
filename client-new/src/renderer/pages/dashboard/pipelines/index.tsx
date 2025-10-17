import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/dashboard/pipelines/')({
  component: RouteComponent,
})

function RouteComponent() {
  return <div>Hello "/dashboard/pipelines/"!</div>
}
