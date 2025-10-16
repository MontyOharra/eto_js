import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/pipelines/')({
  component: PipelinesPage,
});

function PipelinesPage() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-4">Pipelines</h1>
      <p className="text-gray-600">
        Build and test data processing pipelines with modular components.
      </p>
      {/* TODO: Implement pipeline builder with React Flow */}
    </div>
  );
}
