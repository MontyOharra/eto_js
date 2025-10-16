import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/templates/')({
  component: TemplatesPage,
});

function TemplatesPage() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-4">PDF Templates</h1>
      <p className="text-gray-600">
        Create and manage PDF extraction templates for order processing.
      </p>
      {/* TODO: Implement template builder and template list */}
    </div>
  );
}
