import { Outlet, redirect } from "@tanstack/react-router";
import { createFileRoute } from "@tanstack/react-router";
import { isAuthenticated } from "../../helpers/auth";

export const Route = createFileRoute("/transformation_pipeline")({
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