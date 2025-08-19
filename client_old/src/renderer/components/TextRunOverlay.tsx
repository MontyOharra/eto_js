import React from "react";

interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
}

interface TextRunOverlayProps {
  boxes: Rect[];
}

export default function TextRunOverlay({ boxes }: TextRunOverlayProps) {
  if (boxes.length === 0) return null;

  return (
    <div className="absolute inset-0 pointer-events-none z-30">
      {boxes.map((b, idx) => (
        <div
          key={idx}
          className="absolute border border-red-500 rounded opacity-70"
          style={{ left: b.left, top: b.top, width: b.width, height: b.height }}
        />
      ))}
    </div>
  );
}
