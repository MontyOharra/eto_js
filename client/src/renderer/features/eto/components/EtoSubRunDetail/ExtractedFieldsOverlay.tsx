/**
 * ExtractedFieldsOverlay
 * Renders extracted field bounding boxes with values on top of PDF canvas
 * Read-only overlay for viewing extraction results in ETO runs
 * Uses FieldHighlightContext for cross-component highlighting with pipeline entry points
 */

import { usePdfViewer } from '../../../pdf';
import { useFieldHighlight } from '../../../pipelines/contexts';
import { ExtractedFieldWithBox } from '../../types';

interface ExtractedFieldsOverlayProps {
  fields: ExtractedFieldWithBox[];
}

export function ExtractedFieldsOverlay({ fields }: ExtractedFieldsOverlayProps) {
  const { renderScale, currentPage, pdfDimensions } = usePdfViewer();
  const highlightContext = useFieldHighlight();

  if (!pdfDimensions) {
    return null;
  }

  // Render extracted field boxes
  const renderField = (field: ExtractedFieldWithBox) => {
    // Only show fields on current page (both 1-indexed)
    if (field.page !== currentPage) return null;

    const [x0, y0, x1, y1] = field.bbox;

    // Bbox is already in screen coordinates (y=0 at top)
    // No conversion needed - pdfplumber uses same coordinate system
    // Note: field_id contains the field name (set from result.name in PdfViewerPanel)
    const isHighlighted = highlightContext?.highlightedFieldName === field.field_id;

    const boxStyle: React.CSSProperties = {
      position: 'absolute',
      left: `${x0 * renderScale}px`,
      top: `${y0 * renderScale}px`,
      width: `${(x1 - x0) * renderScale}px`,
      height: `${(y1 - y0) * renderScale}px`,
      backgroundColor: isHighlighted ? 'rgba(59, 130, 246, 0.25)' : 'rgba(59, 130, 246, 0.15)',
      border: `2px solid rgba(59, 130, 246, ${isHighlighted ? '1' : '0.6'})`,
      borderRadius: '2px',
      cursor: 'default',
      transition: 'border-color 0.15s ease-in-out, background-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out',
      zIndex: 5,
      pointerEvents: 'auto',
      boxShadow: isHighlighted ? '0 0 12px rgba(59, 130, 246, 0.6)' : undefined,
    };

    // Determine label position (above or below box)
    // Popup height in pixels: 16px (top padding) + 20px (label) + 8px (margin) + 26px (value) + 16px (bottom padding) ≈ 86px
    // Convert to PDF coordinates by dividing by renderScale
    const popupHeightPixels = 90;
    const popupHeightPdfCoords = popupHeightPixels / renderScale;
    const showLabel = isHighlighted;
    const labelAtTop = y0 < 120; // Show below if bbox is near top of page
    const labelY = labelAtTop ? y1 + 8 : y0 - popupHeightPdfCoords; // Position below if at top, otherwise align popup bottom with bbox top

    // Calculate horizontal position with edge detection
    const popupMaxWidth = 400; // max width in pixels
    const popupPadding = 40; // total horizontal padding (20px left + 20px right)
    const edgePadding = 10; // minimum padding from PDF edge

    // PDF width in screen coordinates
    const pdfWidthPixels = pdfDimensions.width * renderScale;

    // Start at field's left edge
    let popupLeftPixels = x0 * renderScale;

    // Check if popup would overflow the right edge
    const popupRightEdge = popupLeftPixels + popupMaxWidth + popupPadding;
    if (popupRightEdge > pdfWidthPixels - edgePadding) {
      // Shift popup left so it stays within bounds
      popupLeftPixels = Math.max(edgePadding, pdfWidthPixels - popupMaxWidth - popupPadding - edgePadding);
    }

    const handleMouseEnter = () => {
      highlightContext?.setHighlightedFieldName(field.field_id);
    };

    const handleMouseLeave = () => {
      highlightContext?.setHighlightedFieldName(null);
    };

    return (
      <div key={field.field_id}>
        <div
          style={boxStyle}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        />
        {showLabel && (
          <div
            style={{
              position: 'absolute',
              left: `${popupLeftPixels}px`,
              top: `${labelY * renderScale}px`,
              maxWidth: `${popupMaxWidth}px`,
              backgroundColor: 'rgba(17, 24, 39, 0.95)',
              border: '2px solid rgba(59, 130, 246, 0.8)',
              borderRadius: '8px',
              padding: '16px 20px',
              fontSize: '24px',
              fontWeight: 500,
              color: 'white',
              zIndex: 20,
              pointerEvents: 'none',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5)',
              wordWrap: 'break-word',
              overflowWrap: 'break-word',
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
