import { useState } from "react";
import { useLayoutEffect, useRef } from "react";

export interface Box {
  id: number;
  left: number;
  top: number;
  right: number;
  bottom: number;
  label?: string;
}

interface SelectableBoxProps {
  box: Box;
  onSave: (id: number, label: string) => void;
  onCancel: (id: number) => void;
  onDelete: (id: number) => void;
  isEditing: boolean;
  onActivate: (id: number) => void;
}

export default function SelectableBox({
  box,
  onSave,
  onCancel,
  onDelete,
  isEditing,
  onActivate,
}: SelectableBoxProps) {
  const [input, setInput] = useState(box.label ?? "");

  const overlayRef = useRef<HTMLDivElement>(null);
  const [placeLeft, setPlaceLeft] = useState(false);

  useLayoutEffect(() => {
    if (!isEditing) return;
    const overlay = overlayRef.current;
    if (!overlay) return;
    const rect = overlay.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    if (rect.right > viewportWidth) {
      setPlaceLeft(true);
    } else {
      setPlaceLeft(false);
    }
  }, [isEditing]);

  const width = box.right - box.left;
  const height = box.bottom - box.top;

  const handleBoxClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onActivate(box.id);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      // Enter without Shift - save the data
      e.preventDefault();
      if (input.trim()) {
        onSave(box.id, input.trim());
      }
    }
    // Shift+Enter will create a new line (default behavior)
  };

  return (
    <div
      className={`absolute border-2 border-orange-500 transition-colors z-10 ${
        isEditing
          ? "bg-orange-500/30"
          : "bg-orange-500/20 hover:bg-orange-500/40 cursor-pointer"
      }`}
      style={{
        left: box.left,
        top: box.top,
        width,
        height,
      }}
      onClick={handleBoxClick}
      onMouseDown={(e) => e.stopPropagation()}
    >
      {isEditing && (
        <div
          ref={overlayRef}
          className="absolute flex flex-col items-stretch gap-1 z-50 bg-white shadow-lg rounded p-2"
          style={
            placeLeft
              ? { top: 0, right: "100%", marginRight: "4px" }
              : { top: 0, left: "100%", marginLeft: "4px" }
          }
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Text input */}
          <textarea
            className="border rounded px-2 py-1 text-sm resize-none min-w-[140px] min-h-[78px] bg-white focus:outline-none focus:ring-2 focus:ring-orange-500"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            style={{ lineHeight: "1.25rem" }}
            autoFocus
            placeholder="Enter field label..."
          />
          {/* Buttons */}
          <div className="flex gap-1 self-end">
            <button
              className="px-2 py-1 bg-gray-300 hover:bg-gray-400 rounded text-xs transition-colors"
              onClick={() => onCancel(box.id)}
              onMouseDown={(e) => e.stopPropagation()}
            >
              Cancel
            </button>
            {box.label !== undefined && (
              <button
                className="px-2 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700 transition-colors"
                onClick={() => onDelete(box.id)}
                onMouseDown={(e) => e.stopPropagation()}
              >
                Delete
              </button>
            )}
            <button
              className="px-2 py-1 bg-orange-600 text-white rounded text-xs hover:bg-orange-700 disabled:bg-orange-300 transition-colors"
              disabled={!input.trim()}
              onClick={() => onSave(box.id, input.trim())}
              onMouseDown={(e) => e.stopPropagation()}
            >
              Save
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
