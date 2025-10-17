/**
 * ObjectTypeButton
 * Individual button for toggling visibility of a PDF object type
 */

interface ObjectTypeButtonProps {
  type: string; // 'text_word', 'graphic_rect', etc.
  label: string; // 'Text Words', 'Rectangles', etc.
  color: string; // '#ff0000'
  count: number;
  isSelected: boolean;
  onToggle: () => void;
}

export function ObjectTypeButton({
  type,
  label,
  color,
  count,
  isSelected,
  onToggle,
}: ObjectTypeButtonProps) {
  return (
    <button
      onClick={onToggle}
      className={`flex-1 flex items-center justify-between p-2 text-xs rounded transition-colors ${
        isSelected
          ? 'bg-gray-700 text-white'
          : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
      }`}
      aria-label={`Toggle ${label}`}
      aria-pressed={isSelected}
    >
      <div className="flex items-center space-x-2">
        <div
          className="w-3 h-3 rounded"
          style={{ backgroundColor: color }}
          aria-hidden="true"
        ></div>
        <span>{label}</span>
      </div>
      <span className="font-medium">{count.toLocaleString()}</span>
    </button>
  );
}
