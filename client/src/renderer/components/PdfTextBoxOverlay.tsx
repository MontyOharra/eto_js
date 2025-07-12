interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
}

interface PdfTextBoxOverlayProps {
  boxes: Rect[];
}

// Debug overlay that draws a border around every text-item rectangle on the PDF page.
// All coordinates are expected to be in *screen* pixels (same scale as the rendered Page).
export default function PdfTextBoxOverlay({ boxes }: PdfTextBoxOverlayProps) {
  if (boxes.length === 0) return null;

  return (
    <div className="absolute inset-0 pointer-events-none z-30">
      {boxes.map((b, idx) => (
        <div
          key={idx}
          className="absolute border border-cyan-500 opacity-70"
          style={{
            left: b.left,
            top: b.top,
            width: b.width,
            height: b.height,
          }}
        />
      ))}
    </div>
  );
}
