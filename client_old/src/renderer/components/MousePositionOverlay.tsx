import { useState } from "react";

interface MousePosProps {
  active: boolean;
  scale: number;
  border: number;
}

export default function MousePositionOverlay({
  active,
  scale,
  border,
}: MousePosProps) {
  const [pos, setPos] = useState<{
    x: number;
    y: number;
    screenX: number;
    screenY: number;
  } | null>(null);

  if (!active) return null;

  const handleMove = (e: React.MouseEvent) => {
    const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
    const relX = e.clientX - rect.left - border; // screen px inside pdf canvas
    const relY = e.clientY - rect.top - border;

    // convert to pdf user-space
    const pdfX = relX / scale;
    const pdfY = relY / scale; // distance from top in PDF user-space

    setPos({
      x: Math.round(pdfX),
      y: Math.round(pdfY),
      screenX: e.clientX,
      screenY: e.clientY,
    });
  };

  return (
    <div className="absolute inset-0 z-60" onMouseMove={handleMove}>
      {pos && (
        <div
          style={{
            position: "fixed",
            left: pos.screenX + 12,
            top: pos.screenY + 12,
          }}
          className="pointer-events-none bg-black bg-opacity-80 text-white text-xs px-1 rounded"
        >
          {pos.x}, {pos.y}
        </div>
      )}
    </div>
  );
}
