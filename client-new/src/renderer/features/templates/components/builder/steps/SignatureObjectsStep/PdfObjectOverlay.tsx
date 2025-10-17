/**
 * PdfObjectOverlay
 * Renders bounding box overlays for PDF objects on top of PDF canvas
 * Must be used as a child of PdfViewer.Canvas
 */

import { useMemo, useState } from 'react';
import { usePdfViewer } from '../../../../../../shared/components/pdf/PdfViewer/PdfViewerContext';

// Object type color mappings (with transparency)
const OBJECT_COLORS: Record<string, string> = {
  text_word: 'rgba(255, 0, 0, 0.2)',
  text_line: 'rgba(0, 255, 0, 0.2)',
  graphic_rect: 'rgba(0, 0, 255, 0.2)',
  graphic_line: 'rgba(255, 255, 0, 0.2)',
  graphic_curve: 'rgba(255, 0, 255, 0.2)',
  image: 'rgba(0, 255, 255, 0.2)',
  table: 'rgba(255, 165, 0, 0.3)',
};

// Border colors (more opaque)
const OBJECT_BORDER_COLORS: Record<string, string> = {
  text_word: 'rgba(255, 0, 0, 0.6)',
  text_line: 'rgba(0, 255, 0, 0.6)',
  graphic_rect: 'rgba(0, 0, 255, 0.6)',
  graphic_line: 'rgba(255, 255, 0, 0.6)',
  graphic_curve: 'rgba(255, 0, 255, 0.6)',
  image: 'rgba(0, 255, 255, 0.6)',
  table: 'rgba(255, 165, 0, 0.7)',
};

// Gray colors for hidden selected objects
const HIDDEN_SELECTED_COLOR = 'rgba(128, 128, 128, 0.3)';
const HIDDEN_SELECTED_BORDER = 'rgba(128, 128, 128, 0.7)';

interface PdfObject {
  type: string;
  page: number;
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
  text?: string;
}

interface PdfObjectOverlayProps {
  objects: PdfObject[];
  selectedTypes: Set<string>;
  selectedObjects: Set<string>; // Set of selected object IDs
  onObjectClick: (objectId: string) => void;
}

// Generate unique ID for an object
const getObjectId = (obj: PdfObject, index: number): string => {
  return `${obj.type}-${obj.page}-${obj.bbox.join('-')}-${index}`;
};

export function PdfObjectOverlay({
  objects,
  selectedTypes,
  selectedObjects,
  onObjectClick,
}: PdfObjectOverlayProps) {
  // Get PDF viewer context
  const { scale, currentPage, pdfDimensions } = usePdfViewer();
  const [hoveredObjectId, setHoveredObjectId] = useState<string | null>(null);

  // Objects to render: visible (selected types) + hidden selected
  const objectsToRender = useMemo(() => {
    return objects
      .map((obj, idx) => ({
        obj,
        index: idx,
        id: getObjectId(obj, idx),
      }))
      .filter(({ obj, id }) => {
        // Show if on current page
        if (obj.page !== currentPage) return false;

        // Show if type is selected (visible)
        if (selectedTypes.has(obj.type)) return true;

        // Show if object is selected but type is hidden
        if (selectedObjects.has(id)) return true;

        return false;
      });
  }, [objects, selectedTypes, selectedObjects, currentPage]);

  // Don't render if PDF dimensions aren't loaded yet
  if (!pdfDimensions) {
    return null;
  }

  const pageHeight = pdfDimensions.height;

  const renderObjectBox = (obj: PdfObject, index: number, objectId: string) => {
    const [x0, y0, x1, y1] = obj.bbox;

    // Coordinate transformation
    // Text objects (text_word, text_line) need Y-axis flipping
    // Graphics/tables/curves use direct coordinates
    let screenY0: number, screenY1: number;

    // List of types that need Y-axis flipping (PDF origin is bottom-left)
    const needsFlipping = obj.type === 'text_word' || obj.type === 'text_line';

    if (needsFlipping) {
      // Flip Y coordinates for text objects
      screenY0 = pageHeight - y1;
      screenY1 = pageHeight - y0;
    } else {
      // Don't flip for graphics, tables, curves, images
      screenY0 = y0;
      screenY1 = y1;
    }

    const isSelected = selectedObjects.has(objectId);
    const isHovered = hoveredObjectId === objectId;
    const isTypeVisible = selectedTypes.has(obj.type);
    const isHiddenSelected = isSelected && !isTypeVisible;

    // Determine colors
    let backgroundColor: string;
    let borderColor: string;
    let borderWidth: string;

    if (isHiddenSelected) {
      // Gray for selected objects with hidden type
      backgroundColor = HIDDEN_SELECTED_COLOR;
      borderColor = HIDDEN_SELECTED_BORDER;
      borderWidth = isSelected ? '3px' : '1px';
    } else {
      backgroundColor = OBJECT_COLORS[obj.type] || 'rgba(128, 128, 128, 0.2)';
      borderColor = OBJECT_BORDER_COLORS[obj.type] || 'rgba(128, 128, 128, 0.6)';
      borderWidth = isSelected ? '3px' : '1px';
    }

    // Apply transform for hover effect
    const transform = isHovered ? 'scale(1.05)' : 'scale(1)';

    const style: React.CSSProperties = {
      position: 'absolute',
      left: `${x0 * scale}px`,
      top: `${screenY0 * scale}px`,
      width: `${(x1 - x0) * scale}px`,
      height: `${(screenY1 - screenY0) * scale}px`,
      backgroundColor,
      border: `${borderWidth} solid ${borderColor}`,
      pointerEvents: isHiddenSelected ? 'none' : 'auto', // Hidden selected not clickable
      cursor: isHiddenSelected ? 'default' : 'pointer',
      transition: 'all 0.15s ease-in-out',
      transform,
      zIndex: isSelected ? 10 : 1,
    };

    return (
      <div
        key={objectId}
        style={style}
        onClick={() => !isHiddenSelected && onObjectClick(objectId)}
        onMouseEnter={() => !isHiddenSelected && setHoveredObjectId(objectId)}
        onMouseLeave={() => setHoveredObjectId(null)}
        title={obj.text || obj.type}
      />
    );
  };

  return (
    <>
      {objectsToRender.map(({ obj, index, id }) => renderObjectBox(obj, index, id))}
    </>
  );
}
