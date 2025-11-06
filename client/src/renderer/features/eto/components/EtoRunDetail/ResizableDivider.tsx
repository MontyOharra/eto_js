/**
 * ResizableDivider
 * Visual divider for resizable panel layouts with drag interaction
 */

interface ResizableDividerProps {
  onMouseDown: () => void;
  isDragging: boolean;
}

export function ResizableDivider({ onMouseDown, isDragging }: ResizableDividerProps) {
  return (
    <div
      className="w-1 bg-gray-700 hover:bg-blue-500 cursor-col-resize transition-colors flex-shrink-0 mx-1"
      onMouseDown={onMouseDown}
      style={{
        userSelect: "none",
        backgroundColor: isDragging ? "#3B82F6" : undefined,
      }}
    />
  );
}
