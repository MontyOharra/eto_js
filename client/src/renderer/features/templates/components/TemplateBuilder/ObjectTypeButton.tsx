/**
 * ObjectTypeButton
 * Individual button for toggling visibility of a PDF object type
 */

interface ObjectTypeButtonProps {
  label: string; // 'Text Words', 'Rectangles', etc.
  color: string; // '#ff0000'
  count: number;
  isSelected: boolean;
  onToggle: () => void;
}

export function ObjectTypeButton({
  label,
  color,
  count,
  isSelected,
  onToggle,
}: ObjectTypeButtonProps) {
  return (
    <button
      onClick={onToggle}
      className={`w-full flex items-center justify-between p-2.5 text-xs rounded transition-colors ${
        isSelected
          ? 'bg-gray-700 text-white'
          : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
      }`}
      aria-label={`Toggle ${label}`}
      aria-pressed={isSelected}
    >
      <div className="flex items-center space-x-2.5">
        <div
          className="w-3 h-3 rounded flex-shrink-0"
          style={{ backgroundColor: color }}
          aria-hidden="true"
        ></div>
        <span className="text-left">{label}</span>
      </div>
      <span className="font-medium ml-2">{count.toLocaleString()}</span>
    </button>
  );
}
