import { createFileRoute } from "@tanstack/react-router";
import { ModuleManagementPage } from "../../components/transformation-pipeline/modules-management/ModuleManagementPage";

export const Route = createFileRoute("/transformation_pipeline/modules")({
  component: ModuleManagement,
});

function ModuleManagement() {
  return <ModuleManagementPage />;
}