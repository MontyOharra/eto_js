import { Outlet, redirect } from "@tanstack/react-router";
import { createFileRoute } from "@tanstack/react-router";
import { isAuthenticated } from "../../../helpers/auth";

export const Route = createFileRoute("/dashboard/pipelines")({
  loader: async () => {
    if (!isAuthenticated()) {
      throw redirect({ to: "/login" });
    }
  },
  component: TransformationPipelineLayout,
});

function TransformationPipelineLayout() {
  return <Outlet />;
}