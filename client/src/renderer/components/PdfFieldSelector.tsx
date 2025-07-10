import { useRef, useState, useEffect } from "react";
import SelectableBox, { Box } from "./SelectableBox";

interface SnapRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

interface PdfFieldSelectorProps {
  initialBoxes: Box[];
  onBoxesChange?: (boxes: Box[]) => void;
  snapRects?: SnapRect[]; // text bounding boxes in screen coords
}

export default function PdfFieldSelector({
  initialBoxes,
  onBoxesChange,
  snapRects = [],
}: PdfFieldSelectorProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const [boxes, setBoxes] = useState<Box[]>(initialBoxes);
  const [editingId, setEditingId] = useState<number | null>(null);
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
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!draftStart) return;
    const { x: currX, y: currY } = toRelative(e);
    if (draftStart) setDraftEnd({ x: currX, y: currY });
  };

  const handleMouseUp = () => {
    if (!draftStart || !draftEnd) return;

    // Build raw rect from drag
    const raw = {
      left: Math.min(draftStart.x, draftEnd.x),
      top: Math.min(draftStart.y, draftEnd.y),
      right: Math.max(draftStart.x, draftEnd.x),
      bottom: Math.max(draftStart.y, draftEnd.y),
    };

    // Pick the single snapRect whose top-left corner is closest to the drag's
    // own top-left corner (raw.left/raw.top).
    const DIST_TOL = 20; // pixels; ignore if farther than this
    let bestRect: SnapRect | null = null;
    let bestDistSq = Infinity;
    for (const r of snapRects) {
      const dx = r.left - raw.left;
      const dy = r.top - raw.top;
      const distSq = dx * dx + dy * dy;
      if (distSq < bestDistSq) {
        bestDistSq = distSq;
        bestRect = r;
      }
    }

    const finalCoords =
      bestRect && bestDistSq <= DIST_TOL * DIST_TOL
        ? {
            left: bestRect.left,
            top: bestRect.top,
            right: bestRect.left + bestRect.width,
            bottom: bestRect.top + bestRect.height,
          }
        : raw;

    setBoxes((prev) => {
      let updated = [...prev];
      // If another box was in unsaved editing state, drop it
      if (editingId !== null) {
        const prevBox = updated.find((b) => b.id === editingId);
        if (prevBox && prevBox.label === undefined) {
          updated = updated.filter((b) => b.id !== editingId);
        }
      }

      const newBox: Box = {
        id: ++boxIdRef.current,
        ...finalCoords,
        label: undefined,
      };

      updated.push(newBox);
      setEditingId(newBox.id);
      return updated;
    });

    setDraftStart(null);
    setDraftEnd(null);
  };

  const handleActivate = (id: number) => {
    if (editingId === id) return;

    setBoxes((prev) => {
      let updated = [...prev];
      if (editingId !== null && editingId !== id) {
        const prevBox = updated.find((b) => b.id === editingId);
        if (prevBox && prevBox.label === undefined) {
          updated = updated.filter((b) => b.id !== editingId);
        }
      }
      return updated;
    });

    setEditingId(id);
  };

  const handleSave = (id: number, label: string) => {
    setBoxes((prev) => {
      const updated = prev.map((b) => (b.id === id ? { ...b, label } : b));
      onBoxesChange?.(updated);
      return updated;
    });
    setEditingId(null);
  };

  const handleCancel = (id: number) => {
    setBoxes((prev) => {
      const target = prev.find((b) => b.id === id);
      if (!target) return prev;
      if (target.label === undefined) {
        // unsaved -> remove completely
        return prev.filter((b) => b.id !== id);
      }
      return prev;
    });
    setEditingId(null);
  };

  const handleDelete = (id: number) => {
    setBoxes((prev) => {
      const filtered = prev.filter((b) => b.id !== id);
      onBoxesChange?.(filtered);
      return filtered;
    });
    if (editingId === id) setEditingId(null);
  };

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
      {boxes.map((b) => (
        <SelectableBox
          key={b.id}
          box={b}
          onSave={handleSave}
          onCancel={handleCancel}
          onDelete={handleDelete}
          isEditing={b.id === editingId}
          onActivate={handleActivate}
        />
      ))}

      {draftStart && draftEnd && (
        <div
          className="absolute border-2 border-red-400 pointer-events-none"
          style={{
            left: Math.min(draftStart.x, draftEnd.x),
            top: Math.min(draftStart.y, draftEnd.y),
            width: Math.abs(draftEnd.x - draftStart.x),
            height: Math.abs(draftEnd.y - draftStart.y),
          }}
        />
      )}
    </div>
  );
}
