import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/dashboard/home")({
  component: Home,
});

function Home() {

  return (
    <main className="min-h-screen bg-gray-100 flex flex-col items-center p-8">
      hi
    </main>
  );
}
