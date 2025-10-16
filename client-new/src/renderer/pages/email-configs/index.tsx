import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/email-configs/')({
  component: EmailConfigsPage,
});

function EmailConfigsPage() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-4">Email Configurations</h1>
      <p className="text-gray-600">
        Manage email ingestion configurations for the ETO system.
      </p>
      {/* TODO: Implement email configs list and CRUD operations */}
    </div>
  );
}
