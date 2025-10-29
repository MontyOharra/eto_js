/**
 * ExtractionFieldOverlay
 * Renders extraction field bounding boxes on top of PDF canvas
 * Must be used as a child of PdfViewer.Canvas
 */

import { useState } from 'react';
import { usePdfViewer } from '../../../../../../shared/components/pdf/PdfViewer/PdfViewerContext';
import { ExtractionField } from '../../../../types';

interface ExtractionFieldOverlayProps {
  fields: ExtractionField[];
  stagedFieldId: string | null;
  tempFieldData: { bbox: [number, number, number, number]; page: number } | null;
  drawingBox: { x: number; y: number; width: number; height: number } | null;
  onFieldClick: (fieldName: string) => void;
}

export function ExtractionFieldOverlay({
  fields,
  stagedFieldId,
  tempFieldData,
  drawingBox,
  onFieldClick,
}: ExtractionFieldOverlayProps) {
  const { renderScale, currentPage, pdfDimensions } = usePdfViewer();
  const [hoveredFieldName, setHoveredFieldName] = useState<string | null>(null);

  if (!pdfDimensions) {
    return null;
  }

  // Render saved extraction fields
  const renderField = (field: ExtractionField) => {
    // Only show fields on current page (both are 1-indexed now)
    if (field.page !== currentPage) return null;

    const [x0, y0, x1, y1] = field.bbox;

    // Bbox is already in screen coordinates (y=0 at top)
    // No conversion needed - pdfplumber uses same coordinate system
    const isStaged = stagedFieldId === field.name;
    const isHovered = hoveredFieldName === field.name;

    const style: React.CSSProperties = {
      position: 'absolute',
      left: `${x0 * renderScale}px`,
      top: `${y0 * renderScale}px`,
      width: `${(x1 - x0) * renderScale}px`,
      height: `${(y1 - y0) * renderScale}px`,
      backgroundColor: 'rgba(147, 51, 234, 0.2)', // Purple with transparency
      border: `${isStaged ? '3px' : '2px'} ${isStaged ? 'dashed' : 'solid'} rgba(147, 51, 234, 0.8)`,
      cursor: 'pointer',
      transition: 'border-width 0.15s ease-in-out',
      zIndex: isStaged ? 10 : 5,
      pointerEvents: 'auto',
    };

    // Determine label position (above or below box)
    const showLabel = isHovered || isStaged;
    const labelTop = y0 < 50; // Show below if too high on page
    const labelY = labelTop ? y1 + 2 : y0 - 8;

    return (
      <div key={field.name}>
        <div
          style={style}
          onClick={() => onFieldClick(field.name)}
          onMouseEnter={() => setHoveredFieldName(field.name)}
          onMouseLeave={() => setHoveredFieldName(null)}
        />
        {showLabel && (
          <div
            style={{
              position: 'absolute',
              left: `${x0 * renderScale}px`,
              top: `${labelY * renderScale}px`,
              backgroundColor: 'rgba(17, 24, 39, 0.95)',
              border: '1px solid rgba(147, 51, 234, 0.8)',
              borderRadius: '4px',
              padding: '6px 10px',
              fontSize: '14px',
              fontWeight: 500,
              color: 'white',
              whiteSpace: 'nowrap',
              zIndex: 20,
              pointerEvents: 'none',
            }}
          >
            {field.name}
          </div>
        )}
      </div>
    );
  };

  // Render temporary field (after drawing, before saving)
  const renderTempField = () => {
    if (!tempFieldData || tempFieldData.page !== currentPage) return null;

    const [x0, y0, x1, y1] = tempFieldData.bbox;

    // Bbox is already in screen coordinates (y=0 at top)
    // No conversion needed - pdfplumber uses same coordinate system
    const style: React.CSSProperties = {
      position: 'absolute',
      left: `${x0 * renderScale}px`,
      top: `${y0 * renderScale}px`,
      width: `${(x1 - x0) * renderScale}px`,
      height: `${(y1 - y0) * renderScale}px`,
      backgroundColor: 'rgba(147, 51, 234, 0.25)',
      border: '3px dashed rgba(147, 51, 234, 0.9)',
      zIndex: 10,
      pointerEvents: 'none',
    };

    return <div style={style} />;
  };

  // Render drawing box (real-time during mouse drag)
  const renderDrawingBox = () => {
    if (!drawingBox) return null;

    // Handle negative width/height (dragging in any direction)
    const x = drawingBox.width >= 0 ? drawingBox.x : drawingBox.x + drawingBox.width;
    const y = drawingBox.height >= 0 ? drawingBox.y : drawingBox.y + drawingBox.height;
    const width = Math.abs(drawingBox.width);
    const height = Math.abs(drawingBox.height);

    const style: React.CSSProperties = {
      position: 'absolute',
      left: `${x * renderScale}px`,
      top: `${y * renderScale}px`,
      width: `${width * renderScale}px`,
      height: `${height * renderScale}px`,
      backgroundColor: 'rgba(59, 130, 246, 0.1)', // Blue with transparency
      border: '2px dashed rgba(59, 130, 246, 0.8)',
      zIndex: 15,
      pointerEvents: 'none',
    };

    return <div style={style} />;
  };

  return (
    <>
      {/* Render all saved fields */}
      {fields.map(field => renderField(field))}

      {/* Render temporary field (being created) */}
      {renderTempField()}

      {/* Render drawing box (active drawing) */}
      {renderDrawingBox()}
    </>
  );
}
