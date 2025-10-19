import { useState } from 'react';

interface EntryPointModalProps {
  onConfirm: (entryPoints: Array<{ name: string }>) => void;
  onCancel: () => void;
}

export const EntryPointModal: React.FC<EntryPointModalProps> = ({ onConfirm, onCancel }) => {
  const [entryPoints, setEntryPoints] = useState<Array<{ id: string; name: string }>>([
    { id: crypto.randomUUID(), name: '' }
  ]);

  const handleAddEntryPoint = () => {
    setEntryPoints([...entryPoints, { id: crypto.randomUUID(), name: '' }]);
  };

  const handleRemoveEntryPoint = (id: string) => {
    if (entryPoints.length === 1) return; // Keep at least one
    setEntryPoints(entryPoints.filter(ep => ep.id !== id));
  };

  const handleNameChange = (id: string, name: string) => {
    setEntryPoints(entryPoints.map(ep =>
      ep.id === id ? { ...ep, name } : ep
    ));
  };

  const handleConfirm = () => {
    // Filter out empty names and confirm
    const validEntryPoints = entryPoints.filter(ep => ep.name.trim() !== '');
    if (validEntryPoints.length === 0) {
      alert('Please provide at least one entry point name');
      return;
    }
    onConfirm(validEntryPoints);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md border border-gray-600">
        <h2 className="text-xl font-semibold text-white mb-4">Define Entry Points</h2>

        <p className="text-sm text-gray-400 mb-4">
          Entry points are the starting inputs for your pipeline. Each entry point will output a string value.
        </p>

        <div className="space-y-3 mb-6">
          {entryPoints.map((ep) => (
            <div key={ep.id} className="flex items-center gap-2">
              <input
                type="text"
                value={ep.name}
                onChange={(e) => handleNameChange(ep.id, e.target.value)}
                placeholder="Entry point name"
                className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-200 text-sm focus:outline-none focus:border-blue-500"
              />
              <button
                onClick={() => handleRemoveEntryPoint(ep.id)}
                disabled={entryPoints.length === 1}
                className="px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 text-gray-300 rounded transition-colors"
                title="Remove entry point"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>

        <button
          onClick={handleAddEntryPoint}
          className="w-full mb-4 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors flex items-center justify-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Entry Point
        </button>

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
          >
            Start Building
          </button>
        </div>
      </div>
    </div>
  );
};
