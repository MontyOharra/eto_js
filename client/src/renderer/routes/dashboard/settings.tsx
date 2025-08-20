import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/dashboard/settings")({
  component: SettingsPage,
});

function SettingsPage() {
  return (
    <div className="flex-1 p-6">
      <h1 className="text-2xl font-semibold text-blue-300">Settings</h1>
    </div>
  );
}
