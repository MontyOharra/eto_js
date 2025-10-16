import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/')({
  component: HomePage,
});

function HomePage() {
  return (
    <div className="text-center py-12">
      <h2 className="text-4xl font-bold text-gray-900 mb-4">
        Hello World!
      </h2>
      <p className="text-xl text-gray-600 mb-8">
        Welcome to the ETO Client Application
      </p>
      <div className="bg-white rounded-lg shadow p-6 max-w-md mx-auto">
        <p className="text-gray-700">
          This is a new Electron + React application built with:
        </p>
        <ul className="mt-4 text-left space-y-2 text-gray-600">
          <li>✓ Electron</li>
          <li>✓ React 19</li>
          <li>✓ TypeScript</li>
          <li>✓ TanStack Router</li>
          <li>✓ Tailwind CSS</li>
          <li>✓ Vite</li>
        </ul>
      </div>
    </div>
  );
}
