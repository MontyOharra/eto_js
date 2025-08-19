import type { PdfObject } from "../../@types/global";

interface PdfObjectOverlayProps {
  objects: PdfObject[];
}

// Object type colors matching the Python viewer
const OBJECT_COLORS = {
  word: "#ADD8E6",
  text_line: "#90EE90",
  table: "#FFB6C1",
  rect: "#FFA07A",
  curve: "#DDA0DD",
  graphic_line: "#B0C4DE",
  image: "#FFD700",
} as const;

// Debug overlay that draws colored borders around PDF objects based on their type.
// All coordinates are expected to be in *screen* pixels (same scale as the rendered Page).
export default function PdfObjectOverlay({ objects }: PdfObjectOverlayProps) {
  if (objects.length === 0) return null;

  return (
    <div className="absolute inset-0 pointer-events-none z-30">
      {objects.map((obj, idx) => {
        const [x0, y0, x1, y1] = obj.bbox;
        const color = OBJECT_COLORS[obj.type] || "#D3D3D3";

        return (
          <div
            key={idx}
            className="absolute border-2 opacity-70"
            style={{
              left: x0,
              top: y0,
              width: x1 - x0,
              height: y1 - y0,
              borderColor: color,
              backgroundColor: `${color}20`, // Add slight background transparency
            }}
            title={`${obj.type}${obj.text ? `: ${obj.text}` : ""}`}
          />
        );
      })}
    </div>
  );
}
