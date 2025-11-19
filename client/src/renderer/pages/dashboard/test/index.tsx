import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/dashboard/test/')({
  component: TestPage,
});

// Mock data
const mockData = [
  { name: 'test1' },
  { name: 'test2' },
  { name: 'test3' },
  { name: 'test4' },
  { name: 'test5' },
];

interface EtoRunRowProps {
  data: { name: string };
}

function EtoRunRow({ data }: EtoRunRowProps) {
  return (
    <div className="border-b border-gray-700 py-4 hover:bg-gray-800/30 transition-colors cursor-pointer">
      <span className="text-gray-200">{data.name}</span>
    </div>
  );
}

function TestPage() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white">Test Page</h1>
        <p className="text-gray-400 mt-2">
          New ETO dashboard prototyping area
        </p>
      </div>

      <div>
        {/* Header Row */}
        <div className="border-b-2 border-gray-600 pb-3 mb-2">
          <span className="text-gray-400 font-semibold text-sm uppercase">Name</span>
        </div>

        {/* Data Rows */}
        {mockData.map((item, index) => (
          <EtoRunRow key={index} data={item} />
        ))}
      </div>
    </div>
  );
}
