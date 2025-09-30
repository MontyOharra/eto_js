import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/transformation_pipeline/graph")({
  beforeLoad: () => {
    // Redirect to the new implementation
    throw redirect({ to: "/transformation_pipeline/graphNew" });
  }
});