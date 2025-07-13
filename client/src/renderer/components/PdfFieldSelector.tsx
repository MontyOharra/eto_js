import { useRef, useState, useEffect } from "react";
import SelectableBox, { Box } from "./SelectableBox";

interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
}

interface PdfFieldSelectorProps {
  initialBoxes: Box[];
  onBoxesChange?: (boxes: Box[]) => void;
  textRects?: Rect[];
}

export default function PdfFieldSelector({
  initialBoxes,
  onBoxesChange,
  textRects = [],
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
  const initializedRef = useRef(false);
  const [startedInTextRect, setStartedInTextRect] = useState(false);

  const toRelative = (e: React.MouseEvent) => {
    const rect = overlayRef.current!.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  };

  // Check if a point is inside a rectangle
  const isPointInRect = (x: number, y: number, rect: Rect) => {
    return (
      x >= rect.left &&
      x <= rect.left + rect.width &&
      y >= rect.top &&
      y <= rect.top + rect.height
    );
  };

  // Check if two rectangles overlap
  const rectsOverlap = (
    rect1: { left: number; top: number; right: number; bottom: number },
    rect2: Rect
  ) => {
    return !(
      rect1.right < rect2.left ||
      rect1.left > rect2.left + rect2.width ||
      rect1.bottom < rect2.top ||
      rect1.top > rect2.top + rect2.height
    );
  };

  // Find all text rects that overlap with the current draft selection
  const getOverlappingTextRects = (
    draftStart: { x: number; y: number },
    draftEnd: { x: number; y: number }
  ) => {
    const selection = {
      left: Math.min(draftStart.x, draftEnd.x),
      top: Math.min(draftStart.y, draftEnd.y),
      right: Math.max(draftStart.x, draftEnd.x),
      bottom: Math.max(draftStart.y, draftEnd.y),
    };

    return textRects.filter((rect) => rectsOverlap(selection, rect));
  };

  // Calculate snapped bounds from overlapping text rects
  const getSnappedBounds = (
    draftStart: { x: number; y: number },
    draftEnd: { x: number; y: number }
  ) => {
    const overlappingRects = getOverlappingTextRects(draftStart, draftEnd);

    if (overlappingRects.length === 0) {
      return {
        left: Math.min(draftStart.x, draftEnd.x),
        top: Math.min(draftStart.y, draftEnd.y),
        right: Math.max(draftStart.x, draftEnd.x),
        bottom: Math.max(draftStart.y, draftEnd.y),
      };
    }

    // Calculate bounds of all overlapping text rects
    const textBounds = overlappingRects.reduce(
      (bounds, rect) => {
        return {
          left: Math.min(bounds.left, rect.left),
          top: Math.min(bounds.top, rect.top),
          right: Math.max(bounds.right, rect.left + rect.width),
          bottom: Math.max(bounds.bottom, rect.top + rect.height),
        };
      },
      {
        left: Infinity,
        top: Infinity,
        right: -Infinity,
        bottom: -Infinity,
      }
    );

    const currentSelection = {
      left: Math.min(draftStart.x, draftEnd.x),
      top: Math.min(draftStart.y, draftEnd.y),
      right: Math.max(draftStart.x, draftEnd.x),
      bottom: Math.max(draftStart.y, draftEnd.y),
    };

    // Apply snapping logic
    let snappedLeft = currentSelection.left;
    let snappedTop = currentSelection.top;
    let snappedRight = currentSelection.right;
    let snappedBottom = currentSelection.bottom;

    // Snap top-left if text bounds are more top-left than current selection
    // But only if we started in a text rect or the text bounds are more restrictive
    if (startedInTextRect || textBounds.left < currentSelection.left) {
      snappedLeft = textBounds.left;
    }
    if (startedInTextRect || textBounds.top < currentSelection.top) {
      snappedTop = textBounds.top;
    }

    // Snap bottom-right if text bounds are more bottom-right than current selection
    if (textBounds.right > currentSelection.right) {
      snappedRight = textBounds.right;
    }
    if (textBounds.bottom > currentSelection.bottom) {
      snappedBottom = textBounds.bottom;
    }

    return {
      left: snappedLeft,
      top: snappedTop,
      right: snappedRight,
      bottom: snappedBottom,
    };
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();

    const { x, y } = toRelative(e);

    // Check if the drag started within a text rect
    const startedInText = textRects.some((rect) => isPointInRect(x, y, rect));
    setStartedInTextRect(startedInText);

    setDraftStart({ x, y });
    setDraftEnd({ x, y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!draftStart) return;
    e.preventDefault();
    e.stopPropagation();

    const { x: currX, y: currY } = toRelative(e);
    setDraftEnd({ x: currX, y: currY });
  };

  const handleMouseUp = (e: React.MouseEvent) => {
    if (!draftStart || !draftEnd) return;
    e.preventDefault();
    e.stopPropagation();

    // Get snapped bounds
    const snappedBounds = getSnappedBounds(draftStart, draftEnd);

    // Only create a box if the drag has some minimum size
    const minSize = 5;
    if (
      snappedBounds.right - snappedBounds.left < minSize ||
      snappedBounds.bottom - snappedBounds.top < minSize
    ) {
      setDraftStart(null);
      setDraftEnd(null);
      setStartedInTextRect(false);
      return;
    }

    const finalCoords = snappedBounds;

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
    setStartedInTextRect(false);
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

  // Only update boxes when initialBoxes actually contains data, or on first mount
  // This prevents empty arrays from resetting our state on every render
  useEffect(() => {
    if (!initializedRef.current) {
      // First mount - always set the initial boxes
      setBoxes(initialBoxes);
      initializedRef.current = true;
    } else if (initialBoxes.length > 0) {
      // Only update if we actually have boxes to show (e.g., navigating to a page with existing boxes)
      setBoxes(initialBoxes);
    }
    // Don't reset to empty array on subsequent renders
  }, [initialBoxes]);

  // Calculate the current draft bounds (with snapping) for display
  const currentDraftBounds =
    draftStart && draftEnd ? getSnappedBounds(draftStart, draftEnd) : null;

  return (
    <div
      ref={overlayRef}
      className="absolute inset-0 cursor-crosshair z-40"
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

      {currentDraftBounds && (
        <div
          className="absolute border-2 border-red-500 bg-red-500/10 pointer-events-none"
          style={{
            left: currentDraftBounds.left,
            top: currentDraftBounds.top,
            width: currentDraftBounds.right - currentDraftBounds.left,
            height: currentDraftBounds.bottom - currentDraftBounds.top,
          }}
        />
      )}
    </div>
  );
}
