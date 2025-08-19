import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  loader: () => redirect({ to: "dashboard" as unknown as string }),
  component: () => null,
});
