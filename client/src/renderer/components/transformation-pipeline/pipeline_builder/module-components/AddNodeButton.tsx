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

  return (
    <div className={`flex ${isInput ? 'justify-start' : 'justify-end'} px-3 py-2`}>
      <button
        onClick={onAdd}
        disabled={disabled}
        className={`
          w-6 h-6 rounded-full border-2 border-dashed
          flex items-center justify-center text-xs
          transition-colors
          ${disabled
            ? 'border-gray-600 text-gray-600 cursor-not-allowed'
            : 'border-gray-500 text-gray-400 hover:border-blue-400 hover:text-blue-400 cursor-pointer'
          }
        `}
        title={`Add ${side} node`}
      >
        +
      </button>
    </div>
  );
};