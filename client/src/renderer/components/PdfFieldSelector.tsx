import { useRef, useState, useEffect } from "react";

interface Box {
  id: number;
  left: number;
  top: number;
  right: number;
  bottom: number;
}

interface PdfFieldSelectorProps {
  initialBoxes: Box[];
  onBoxesChange?: (boxes: Box[]) => void;
}

// Renders an overlay that lets the user drag-to-draw selection rectangles.
// Only the visual selection is handled for now.
export default function PdfFieldSelector({
  initialBoxes,
  onBoxesChange,
}: PdfFieldSelectorProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const [boxes, setBoxes] = useState<Box[]>(initialBoxes);
  const [draftStart, setDraftStart] = useState<{ x: number; y: number } | null>(
    null
  );
  const [draftEnd, setDraftEnd] = useState<{ x: number; y: number } | null>(
    null
  );
  const boxIdRef = useRef(0);

  const toRelative = (e: React.MouseEvent) => {
    const rect = overlayRef.current!.getBoundingClientRect();
    const borderX = overlayRef.current!.clientLeft; // left border width
    const borderY = overlayRef.current!.clientTop; // top border width
    return {
      x: e.clientX - rect.left - borderX / 2,
      y: e.clientY - rect.top - borderY / 2,
    };
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    let { x, y } = toRelative(e);
    x -= 4;
    y -= 4;
    setDraftStart({ x, y });
    setDraftEnd({ x, y });
    console.log(boxes);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!draftStart) return;
    const { x: currX, y: currY } = toRelative(e);
    if (draftStart) setDraftEnd({ x: currX, y: currY });
  };

  const handleMouseUp = () => {
    if (!draftStart || !draftEnd) return;
    const final: Box = {
      id: ++boxIdRef.current,
      left: Math.min(draftStart.x, draftEnd.x),
      top: Math.min(draftStart.y, draftEnd.y),
      right: Math.max(draftStart.x, draftEnd.x),
      bottom: Math.max(draftStart.y, draftEnd.y),
    };
    setBoxes((b) => {
      const updated = [...b, final];
      onBoxesChange?.(updated);
      return updated;
    });
    setDraftStart(null);
    setDraftEnd(null);
  };

  const renderRect = (box: Box, color = "border-blue-500") => (
    <div
      key={box.id}
      className={`absolute border-2 ${color} pointer-events-none`}
      style={{
        left: box.left,
        top: box.top,
        width: box.right - box.left,
        height: box.bottom - box.top,
      }}
    />
  );

  // Keep local state in sync if parent provides new initialBoxes (e.g., when user navigates back to this page).
  // Only overwrite when the array reference actually changes to avoid clobbering ongoing edits.
  useEffect(() => {
    setBoxes(initialBoxes);
  }, [initialBoxes]);

  return (
    <div
      ref={overlayRef}
      className="absolute inset-0 cursor-crosshair z-50 border-4"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    >
      {boxes.map((b) => renderRect(b))}
      {draftStart &&
        draftEnd &&
        renderRect(
          {
            id: -1,
            left: Math.min(draftStart.x, draftEnd.x),
            top: Math.min(draftStart.y, draftEnd.y),
            right: Math.max(draftStart.x, draftEnd.x),
            bottom: Math.max(draftStart.y, draftEnd.y),
          },
          "border-red-400"
        )}
    </div>
  );
}
