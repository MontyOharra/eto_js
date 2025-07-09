import { useRef, useState } from "react";

interface Box {
  id: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

// Renders an overlay that lets the user drag-to-draw selection rectangles.
// Only the visual selection is handled for now.
export default function PdfFieldSelector() {
  const overlayRef = useRef<HTMLDivElement>(null);
  const [boxes, setBoxes] = useState<Box[]>([]);
  const [draft, setDraft] = useState<Box | null>(null);
  const boxIdRef = useRef(0);

  const toRelative = (e: React.MouseEvent) => {
    const rect = overlayRef.current!.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    const { x, y } = toRelative(e);
    setDraft({ id: -1, x, y, width: 0, height: 0 });
    console.log(boxes);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!draft) return;
    const { x, y } = toRelative(e);
    setDraft(
      (prev) => prev && { ...prev, width: x - prev.x, height: y - prev.y }
    );
  };

  const handleMouseUp = () => {
    if (!draft) return;
    const final = { ...draft, id: ++boxIdRef.current };
    // Normalize width/height to positive values
    if (final.width < 0) {
      final.x += final.width;
      final.width = Math.abs(final.width);
    }
    if (final.height < 0) {
      final.y += final.height;
      final.height = Math.abs(final.height);
    }
    setBoxes((b) => [...b, final]);
    setDraft(null);
  };

  const renderRect = (box: Box, color = "border-blue-500") => (
    <div
      key={box.id}
      className={`absolute border-2 ${color} pointer-events-none`}
      style={{
        left: box.x,
        top: box.y,
        width: box.width,
        height: box.height,
      }}
    />
  );

  return (
    <div
      ref={overlayRef}
      className="absolute inset-0 cursor-crosshair z-50 border-4 border-red-500/80 bg-red-500/5"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    >
      {boxes.map((b) => renderRect(b))}
      {draft && renderRect(draft, "border-red-400")}
    </div>
  );
}
