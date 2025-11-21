/**
 * SignatureObjectsView
 * Read-only view of signature objects overlaid on PDF
 * All signature objects are always visible (no toggle)
 */

import { useMemo, useState } from 'react';
import { PdfViewer, usePdfViewer } from '../../../pdf';
import type { PdfObjects } from '../../types';
import { OBJECT_TYPE_COLORS, OBJECT_FILL_COLORS, OBJECT_BORDER_COLORS } from '../../constants';

interface SignatureObjectsViewProps {
  pdfUrl: string;
  signatureObjects: PdfObjects;
}

export function SignatureObjectsView({
  pdfUrl,
  signatureObjects,
}: SignatureObjectsViewProps) {
  // Visibility state for each object type (all visible by default)
  const [visibleTypes, setVisibleTypes] = useState<Set<string>>(
    new Set(['text_word', 'graphic_rect', 'graphic_line', 'graphic_curve', 'image', 'table'])
  );

  // Count total signature objects by type
  const objectCounts = useMemo(() => {
    return {
      text_word: signatureObjects.text_words?.length || 0,
      graphic_rect: signatureObjects.graphic_rects?.length || 0,
      graphic_line: signatureObjects.graphic_lines?.length || 0,
      graphic_curve: signatureObjects.graphic_curves?.length || 0,
      image: signatureObjects.images?.length || 0,
      table: signatureObjects.tables?.length || 0,
    };
  }, [signatureObjects]);

  const totalCount = Object.values(objectCounts).reduce((sum, count) => sum + count, 0);

  // Toggle visibility of a type
  const toggleTypeVisibility = (type: string) => {
    setVisibleTypes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(type)) {
        newSet.delete(type);
      } else {
        newSet.add(type);
      }
      return newSet;
    });
  };

  // Flatten signature objects for overlay rendering
  const flattenedObjects = useMemo(() => {
    const flat: Array<any> = [];

    const addObjects = (objects: any[] | undefined, type: string) => {
      if (!objects) return;
      objects.forEach((obj) => {
        flat.push({
          ...obj,
          type,
          page: obj.page || 1,
        });
      });
    };

    // Add all object types
    addObjects(signatureObjects.text_words, 'text_word');
    addObjects(signatureObjects.graphic_rects, 'graphic_rect');
    addObjects(signatureObjects.graphic_lines, 'graphic_line');
    addObjects(signatureObjects.graphic_curves, 'graphic_curve');
    addObjects(signatureObjects.images, 'image');
    addObjects(signatureObjects.tables, 'table');

    return flat;
  }, [signatureObjects]);

  // Filter objects based on visibility
  const visibleObjects = useMemo(() => {
    return flattenedObjects.filter((obj) => visibleTypes.has(obj.type));
  }, [flattenedObjects, visibleTypes]);

  return (
    <div className="h-full flex">
      {/* Sidebar */}
      <div className="w-80 border-r border-gray-700 bg-gray-900 p-4 overflow-y-auto">
        <h3 className="text-sm font-semibold text-white mb-4">Signature Objects</h3>
        <p className="text-sm text-gray-400 mb-4">
          These objects uniquely identify this template type.
        </p>

        {/* Total count */}
        <div className="mb-4 p-3 bg-gray-800 rounded">
          <div className="text-sm text-gray-400">Total Objects</div>
          <div className="text-2xl font-bold text-white">{totalCount}</div>
        </div>

        {/* Object counts by type */}
        <div className="space-y-2">
          {objectCounts.text_word > 0 && (
            <button
              onClick={() => toggleTypeVisibility('text_word')}
              className={`w-full flex items-center justify-between p-2 rounded transition-colors ${
                visibleTypes.has('text_word')
                  ? 'bg-gray-700 text-white'
                  : 'bg-gray-800 text-gray-500 opacity-60'
              }`}
            >
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: OBJECT_TYPE_COLORS.text_word }}></div>
                <span className="text-sm">Text Words</span>
              </div>
              <span className="text-sm font-medium">{objectCounts.text_word}</span>
            </button>
          )}

          {objectCounts.graphic_rect > 0 && (
            <button
              onClick={() => toggleTypeVisibility('graphic_rect')}
              className={`w-full flex items-center justify-between p-2 rounded transition-colors ${
                visibleTypes.has('graphic_rect')
                  ? 'bg-gray-700 text-white'
                  : 'bg-gray-800 text-gray-500 opacity-60'
              }`}
            >
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: OBJECT_TYPE_COLORS.graphic_rect }}></div>
                <span className="text-sm">Graphic Rects</span>
              </div>
              <span className="text-sm font-medium">{objectCounts.graphic_rect}</span>
            </button>
          )}

          {objectCounts.graphic_line > 0 && (
            <button
              onClick={() => toggleTypeVisibility('graphic_line')}
              className={`w-full flex items-center justify-between p-2 rounded transition-colors ${
                visibleTypes.has('graphic_line')
                  ? 'bg-gray-700 text-white'
                  : 'bg-gray-800 text-gray-500 opacity-60'
              }`}
            >
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: OBJECT_TYPE_COLORS.graphic_line }}></div>
                <span className="text-sm">Graphic Lines</span>
              </div>
              <span className="text-sm font-medium">{objectCounts.graphic_line}</span>
            </button>
          )}

          {objectCounts.graphic_curve > 0 && (
            <button
              onClick={() => toggleTypeVisibility('graphic_curve')}
              className={`w-full flex items-center justify-between p-2 rounded transition-colors ${
                visibleTypes.has('graphic_curve')
                  ? 'bg-gray-700 text-white'
                  : 'bg-gray-800 text-gray-500 opacity-60'
              }`}
            >
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: OBJECT_TYPE_COLORS.graphic_curve }}></div>
                <span className="text-sm">Graphic Curves</span>
              </div>
              <span className="text-sm font-medium">{objectCounts.graphic_curve}</span>
            </button>
          )}

          {objectCounts.image > 0 && (
            <button
              onClick={() => toggleTypeVisibility('image')}
              className={`w-full flex items-center justify-between p-2 rounded transition-colors ${
                visibleTypes.has('image')
                  ? 'bg-gray-700 text-white'
                  : 'bg-gray-800 text-gray-500 opacity-60'
              }`}
            >
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: OBJECT_TYPE_COLORS.image }}></div>
                <span className="text-sm">Images</span>
              </div>
              <span className="text-sm font-medium">{objectCounts.image}</span>
            </button>
          )}

          {objectCounts.table > 0 && (
            <button
              onClick={() => toggleTypeVisibility('table')}
              className={`w-full flex items-center justify-between p-2 rounded transition-colors ${
                visibleTypes.has('table')
                  ? 'bg-gray-700 text-white'
                  : 'bg-gray-800 text-gray-500 opacity-60'
              }`}
            >
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: OBJECT_TYPE_COLORS.table }}></div>
                <span className="text-sm">Tables</span>
              </div>
              <span className="text-sm font-medium">{objectCounts.table}</span>
            </button>
          )}
        </div>
      </div>

      {/* PDF Viewer with overlay */}
      <div className="flex-1 bg-gray-900 p-4 overflow-auto">
        <PdfViewer pdfUrl={pdfUrl}>
          <PdfViewer.Canvas pdfUrl={pdfUrl}>
            <SignatureObjectsOverlay objects={visibleObjects} />
          </PdfViewer.Canvas>
          <PdfViewer.ControlsSidebar position="right" />
        </PdfViewer>
      </div>
    </div>
  );
}

// Overlay component to render signature object bounding boxes
interface SignatureObjectsOverlayProps {
  objects: any[];
}

function SignatureObjectsOverlay({
  objects,
}: SignatureObjectsOverlayProps) {
  const { renderScale, currentPage, pdfDimensions } = usePdfViewer();

  // Filter objects for current page
  const pageObjects = useMemo(
    () => objects.filter((obj) => obj.page === currentPage),
    [objects, currentPage]
  );

  // Don't render if PDF dimensions aren't loaded yet
  if (!pdfDimensions) {
    return null;
  }

  const pageHeight = pdfDimensions.height;

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
      {pageObjects.map((obj, idx) => {
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

        const width = (x1 - x0) * renderScale;
        const height = (screenY1 - screenY0) * renderScale;
        const left = x0 * renderScale;
        const top = screenY0 * renderScale;

        // Get colors from centralized constants (matches builder styling)
        const fillColor = OBJECT_FILL_COLORS[obj.type] || 'rgba(128, 128, 128, 0.2)';
        const borderColor = OBJECT_BORDER_COLORS[obj.type] || 'rgba(128, 128, 128, 0.6)';

        return (
          <div
            key={idx}
            style={{
              position: 'absolute',
              left: `${left}px`,
              top: `${top}px`,
              width: `${width}px`,
              height: `${height}px`,
              border: `2px solid ${borderColor}`,
              backgroundColor: fillColor,
              pointerEvents: 'none',
            }}
          />
        );
      })}
    </div>
  );
}
