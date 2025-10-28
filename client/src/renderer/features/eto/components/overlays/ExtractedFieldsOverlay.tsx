/**
 * ExtractedFieldsOverlay
 * Renders extracted field bounding boxes with values on top of PDF canvas
 * Read-only overlay for viewing extraction results in ETO runs
 */

import { useState } from 'react';
import { usePdfViewer } from '../../../../shared/components/pdf/PdfViewer/PdfViewerContext';
import { ExtractedFieldWithBox } from '../../types';

interface ExtractedFieldsOverlayProps {
  fields: ExtractedFieldWithBox[];
}

export function ExtractedFieldsOverlay({ fields }: ExtractedFieldsOverlayProps) {
  const { renderScale, currentPage, pdfDimensions } = usePdfViewer();
  const [hoveredFieldId, setHoveredFieldId] = useState<string | null>(null);

  if (!pdfDimensions) {
    return null;
  }

  const pageHeight = pdfDimensions.height;

  // Render extracted field boxes
  const renderField = (field: ExtractedFieldWithBox) => {
    // Only show fields on current page (both 1-indexed)
    if (field.page !== currentPage) return null;

    const [x0, y0, x1, y1] = field.bbox;

    // Bbox is already in screen coordinates (y=0 at top)
    // No conversion needed - pdfplumber uses same coordinate system
    const isHovered = hoveredFieldId === field.field_id;

    const boxStyle: React.CSSProperties = {
      position: 'absolute',
      left: `${x0 * renderScale}px`,
      top: `${y0 * renderScale}px`,
      width: `${(x1 - x0) * renderScale}px`,
      height: `${(y1 - y0) * renderScale}px`,
      backgroundColor: 'rgba(59, 130, 246, 0.15)', // Blue with transparency
      border: `2px solid rgba(59, 130, 246, ${isHovered ? '1' : '0.6'})`,
      borderRadius: '2px',
      cursor: 'default',
      transition: 'border-color 0.15s ease-in-out, background-color 0.15s ease-in-out',
      zIndex: 5,
      pointerEvents: 'auto',
    };

    // Determine label position (above or below box)
    const showLabel = isHovered;
    const labelTop = y0 < 60; // Show below if too high on page
    const labelY = labelTop ? y1 + 4 : y0 - 10;

    return (
      <div key={field.field_id}>
        <div
          style={boxStyle}
          onMouseEnter={() => setHoveredFieldId(field.field_id)}
          onMouseLeave={() => setHoveredFieldId(null)}
        />
        {showLabel && (
          <div
            style={{
              position: 'absolute',
              left: `${x0 * renderScale}px`,
              top: `${labelY * renderScale}px`,
              backgroundColor: 'rgba(17, 24, 39, 0.95)',
              border: '2px solid rgba(59, 130, 246, 0.8)',
              borderRadius: '8px',
              padding: '16px 20px',
              fontSize: '24px',
              fontWeight: 500,
              color: 'white',
              whiteSpace: 'nowrap',
              zIndex: 20,
              pointerEvents: 'none',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5)',
            }}
          >
            <div className="text-blue-400 mb-2" style={{ fontSize: '20px' }}>{field.label}</div>
            <div className="text-white" style={{ fontSize: '26px', fontWeight: 700 }}>{field.value}</div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
      }}
    >
      {fields.map(renderField)}
    </div>
  );
}
