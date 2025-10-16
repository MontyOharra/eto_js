import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/eto-runs/')({
  component: EtoRunsPage,
});

function EtoRunsPage() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-4">ETO Runs</h1>
      <p className="text-gray-600">
        View and manage Email-to-Order processing runs and their results.
      </p>
      {/* TODO: Implement ETO runs list with filtering and detail view */}
    </div>
  );
}
