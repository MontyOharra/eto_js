import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  beforeLoad: () => {
    const authed = false // check session/token here
    if (!authed) throw redirect({ to: '/login', replace: true })
  },
  component: () => <HomePage/>,
})


function HomePage() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold">Home</h1>
    </div>
  )
}