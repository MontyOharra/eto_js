import React from 'react';

interface AddNodeButtonProps {
  side: 'input' | 'output';
  onAdd: () => void;
  disabled?: boolean;
}

export const AddNodeButton: React.FC<AddNodeButtonProps> = ({
  side,
  onAdd,
  disabled = false
}) => {
  const isInput = side === 'input';

  if (isInput) {
    return (
      <div className="flex items-center px-3 py-2 relative">
        {/* Add Input Button */}
        <div
          className="absolute left-0 top-1/2 transform -translate-y-1/2 -translate-x-1/2"
          style={{ zIndex: 10 }}
        >
          <button
            className="w-5 h-5 rounded-full border-2 border-gray-600 bg-gray-700 hover:bg-gray-600 cursor-pointer hover:scale-110 transition-all flex items-center justify-center"
            onClick={(e) => {
              e.stopPropagation();
              onAdd();
            }}
            onMouseDown={(e) => {
              e.stopPropagation();
              e.preventDefault();
            }}
            disabled={disabled}
            title={`Add ${side}`}
          >
            <svg className="w-3 h-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </button>
        </div>

        {/* Add Input Text */}
        <div className="ml-3 text-xs text-gray-500">Add {side}</div>
      </div>
    );
  } else {
    return (
      <div className="flex items-center px-3 py-2 relative">
        {/* Add Output Text */}
        <div className="mr-3 text-xs text-gray-500">Add {side}</div>

        {/* Add Output Button */}
        <div
          className="absolute right-0 top-1/2 transform -translate-y-1/2 translate-x-1/2"
          style={{ zIndex: 10 }}
        >
          <button
            className="w-5 h-5 rounded-full border-2 border-gray-600 bg-gray-700 hover:bg-gray-600 cursor-pointer hover:scale-110 transition-all flex items-center justify-center"
            onClick={(e) => {
              e.stopPropagation();
              onAdd();
            }}
            onMouseDown={(e) => {
              e.stopPropagation();
              e.preventDefault();
            }}
            disabled={disabled}
            title={`Add ${side}`}
          >
            <svg className="w-3 h-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </button>
        </div>
      </div>
    );
  }
};