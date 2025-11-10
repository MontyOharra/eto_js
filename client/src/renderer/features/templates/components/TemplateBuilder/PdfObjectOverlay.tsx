/**
 * PdfObjectOverlay
 * Renders bounding box overlays for PDF objects on top of PDF canvas
 * Must be used as a child of PdfViewer.Canvas
 */

import { useMemo, useState } from 'react';
import { usePdfViewer } from '../../../pdf';
import { OBJECT_FILL_COLORS, OBJECT_BORDER_COLORS } from '../../constants';

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
  const { renderScale, currentPage, pdfDimensions } = usePdfViewer();
  const [hoveredObjectId, setHoveredObjectId] = useState<string | null>(null);

  // Objects to render: visible (selected types) + hidden selected
  const objectsToRender = useMemo(() => {
    return objects
      .map((obj, idx) => {
        const [x0, y0, x1, y1] = obj.bbox;
        const area = (x1 - x0) * (y1 - y0);
        return {
          obj,
          index: idx,
          id: getObjectId(obj, idx),
          area,
        };
      })
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

  const renderObjectBox = (obj: PdfObject, index: number, objectId: string, renderIndex: number) => {
    const [x0, y0, x1, y1] = obj.bbox;

    // Coordinate transformation
    // Text objects, tables, and curves don't need Y-axis flipping
    // Graphics (rects, lines) and images need flipping
    let screenY0: number, screenY1: number;

    // List of types that DON'T need Y-axis flipping
    const noFlipping = obj.type === 'text_word' ||
                       obj.type === 'table' ||
                       obj.type === 'graphic_curve';

    if (noFlipping) {
      // Don't flip Y coordinates for text, table, and curve objects
      screenY0 = y0;
      screenY1 = y1;
    } else {
      // Flip Y coordinates for graphic objects (rects, lines) and images
      screenY0 = pageHeight - y1;
      screenY1 = pageHeight - y0;
    }

    const isSelected = selectedObjects.has(objectId);
    const isHovered = hoveredObjectId === objectId;
    const isTypeVisible = selectedTypes.has(obj.type);
    const isHiddenSelected = isSelected && !isTypeVisible;

    // Helper function to increase opacity of rgba color
    const increaseOpacity = (rgbaColor: string): string => {
      const match = rgbaColor.match(/rgba?\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)/);
      if (!match) return rgbaColor;
      const [, r, g, b, a] = match;
      const newAlpha = Math.min(parseFloat(a) + 0.15, 0.6); // Increase by 0.15, max 0.6
      return `rgba(${r}, ${g}, ${b}, ${newAlpha})`;
    };

    // Determine colors
    let backgroundColor: string;
    let borderColor: string;
    let borderWidth: string;

    if (isHiddenSelected) {
      // Gray for selected objects with hidden type
      backgroundColor = HIDDEN_SELECTED_COLOR;
      borderColor = HIDDEN_SELECTED_BORDER;
      borderWidth = '3px';
    } else {
      const baseColor = OBJECT_FILL_COLORS[obj.type] || 'rgba(128, 128, 128, 0.2)';
      backgroundColor = isSelected ? increaseOpacity(baseColor) : baseColor;
      borderColor = OBJECT_BORDER_COLORS[obj.type] || 'rgba(128, 128, 128, 0.6)';
      borderWidth = isSelected ? '3px' : '1px';
    }

    // Apply transform for hover effect
    const transform = isHovered ? 'scale(1.05)' : 'scale(1)';

    // Calculate dimensions
    const objectWidth = (x1 - x0) * renderScale;
    const objectHeight = (screenY1 - screenY0) * renderScale;

    // Minimum hitbox size in pixels (makes thin lines easier to click)
    const MIN_HITBOX_SIZE = 8;

    // Expand hitbox for small objects
    const hitboxWidth = Math.max(objectWidth, MIN_HITBOX_SIZE);
    const hitboxHeight = Math.max(objectHeight, MIN_HITBOX_SIZE);

    // Center the visual element within the hitbox
    const hitboxOffsetX = (hitboxWidth - objectWidth) / 2;
    const hitboxOffsetY = (hitboxHeight - objectHeight) / 2;

    // Z-index: Calculate based on inverse of area (smaller area = higher z-index)
    // Use a large number divided by area to get inverse relationship
    // Add 1 to area to avoid division by zero
    const { area } = objectsToRender[renderIndex];
    const baseZIndex = Math.floor(1000000 / (area + 1));
    const zIndex = isSelected ? baseZIndex + 10000000 : baseZIndex;

    const style: React.CSSProperties = {
      position: 'absolute',
      left: `${x0 * renderScale - hitboxOffsetX}px`,
      top: `${screenY0 * renderScale - hitboxOffsetY}px`,
      width: `${hitboxWidth}px`,
      height: `${hitboxHeight}px`,
      pointerEvents: isHiddenSelected ? 'none' : 'auto',
      cursor: isHiddenSelected ? 'default' : 'pointer',
      zIndex,
      // Use padding to create visual element centered in hitbox
      padding: `${hitboxOffsetY}px ${hitboxOffsetX}px`,
      boxSizing: 'border-box',
    };

    const visualStyle: React.CSSProperties = {
      width: '100%',
      height: '100%',
      backgroundColor,
      border: `${borderWidth} solid ${borderColor}`,
      transition: 'transform 0.15s ease-in-out',
      transform,
    };

    return (
      <div
        key={objectId}
        style={style}
        onClick={() => !isHiddenSelected && onObjectClick(objectId)}
        onMouseEnter={() => !isHiddenSelected && setHoveredObjectId(objectId)}
        onMouseLeave={() => setHoveredObjectId(null)}
        title={obj.text || obj.type}
      >
        <div style={visualStyle} />
      </div>
    );
  };

  return (
    <>
      {objectsToRender.map(({ obj, index, id }, renderIndex) =>
        renderObjectBox(obj, index, id, renderIndex)
      )}
    </>
  );
}
