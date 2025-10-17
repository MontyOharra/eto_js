/**
 * PdfObjectOverlay
 * Renders bounding box overlays for PDF objects on top of PDF canvas
 * Must be used as a child of PdfViewer.Canvas
 */

import { useMemo } from 'react';
import { usePdfViewer } from '../../../../../shared/components/pdf/PdfViewer/PdfViewerContext';

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

interface PdfObject {
  type: string;
  page: number;
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
  text?: string;
}

interface PdfObjectOverlayProps {
  objects: PdfObject[];
  selectedTypes: Set<string>;
}

export function PdfObjectOverlay({
  objects,
  selectedTypes,
}: PdfObjectOverlayProps) {
  // Get PDF viewer context
  const { scale, currentPage, pdfDimensions } = usePdfViewer();

  // Filter objects for current page and selected types
  const visibleObjects = useMemo(() => {
    return objects.filter(
      (obj) => obj.page === currentPage && selectedTypes.has(obj.type)
    );
  }, [objects, selectedTypes, currentPage]);

  // Don't render if PDF dimensions aren't loaded yet
  if (!pdfDimensions) {
    return null;
  }

  const pageHeight = pdfDimensions.height;

  const renderObjectBox = (obj: PdfObject, index: number) => {
    const [x0, y0, x1, y1] = obj.bbox;

    // Coordinate transformation
    // Text objects need Y-axis flipping (PDF origin is bottom-left, screen is top-left)
    // Graphics/tables/curves use direct coordinates
    let screenY0: number, screenY1: number;

    if (obj.type === 'table' || obj.type === 'graphic_curve') {
      // Don't flip Y coordinates for table and curve objects
      screenY0 = y0;
      screenY1 = y1;
    } else {
      // Flip Y coordinates for text and other object types
      screenY0 = pageHeight - y1;
      screenY1 = pageHeight - y0;
    }

    const backgroundColor = OBJECT_COLORS[obj.type] || 'rgba(128, 128, 128, 0.2)';
    const borderColor = OBJECT_BORDER_COLORS[obj.type] || 'rgba(128, 128, 128, 0.6)';

    const style: React.CSSProperties = {
      position: 'absolute',
      left: `${x0 * scale}px`,
      top: `${screenY0 * scale}px`,
      width: `${(x1 - x0) * scale}px`,
      height: `${(screenY1 - screenY0) * scale}px`,
      backgroundColor,
      border: `1px solid ${borderColor}`,
      pointerEvents: 'none', // Allow clicks to pass through
      transition: 'all 0.15s ease-in-out',
    };

    return (
      <div
        key={`${obj.type}-${index}-${obj.bbox.join('-')}`}
        style={style}
        aria-hidden="true"
      />
    );
  };

  return (
    <>
      {visibleObjects.map((obj, index) => renderObjectBox(obj, index))}
    </>
  );
}
