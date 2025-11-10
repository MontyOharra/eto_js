/**
 * SignatureObjectsView
 * Read-only view of signature objects overlaid on PDF
 * All signature objects are always visible (no toggle)
 */

import { useMemo } from 'react';
import { PdfViewer, usePdfViewer } from '../../../pdf';
import type { PdfObjects } from '../../types';

interface SignatureObjectsViewProps {
  pdfUrl: string;
  signatureObjects: PdfObjects;
}

export function SignatureObjectsView({
  pdfUrl,
  signatureObjects,
}: SignatureObjectsViewProps) {
  // Count total signature objects by type
  const objectCounts = useMemo(() => {
    return {
      text_words: signatureObjects.text_words?.length || 0,
      graphic_rects: signatureObjects.graphic_rects?.length || 0,
      graphic_lines: signatureObjects.graphic_lines?.length || 0,
      graphic_curves: signatureObjects.graphic_curves?.length || 0,
      images: signatureObjects.images?.length || 0,
      tables: signatureObjects.tables?.length || 0,
    };
  }, [signatureObjects]);

  const totalCount = Object.values(objectCounts).reduce((sum, count) => sum + count, 0);

  // Flatten signature objects for overlay rendering
  const flattenedObjects = useMemo(() => {
    const flat: Array<any> = [];

    const addObjects = (objects: any[] | undefined, type: string, color: string) => {
      if (!objects) return;
      objects.forEach((obj) => {
        flat.push({
          ...obj,
          type,
          color,
          page: obj.page || 1,
        });
      });
    };

    // Add all object types with colors matching TemplateBuilder
    addObjects(signatureObjects.text_words, 'text_word', '#3b82f6');      // blue
    addObjects(signatureObjects.graphic_rects, 'graphic_rect', '#f59e0b'); // amber
    addObjects(signatureObjects.graphic_lines, 'graphic_line', '#ef4444'); // red
    addObjects(signatureObjects.graphic_curves, 'graphic_curve', '#8b5cf6'); // purple
    addObjects(signatureObjects.images, 'image', '#ec4899');              // pink
    addObjects(signatureObjects.tables, 'table', '#06b6d4');              // cyan

    return flat;
  }, [signatureObjects]);

  return (
    <div className="h-full flex">
      {/* Sidebar */}
      <div className="w-80 border-r border-gray-700 bg-gray-800 p-4 overflow-y-auto">
        <h3 className="text-lg font-semibold text-white mb-4">Signature Objects</h3>
        <p className="text-sm text-gray-400 mb-4">
          These objects uniquely identify this template type.
        </p>

        {/* Total count */}
        <div className="mb-4 p-3 bg-gray-700 rounded-lg">
          <div className="text-sm text-gray-400">Total Objects</div>
          <div className="text-2xl font-bold text-white">{totalCount}</div>
        </div>

        {/* Object counts by type */}
        <div className="space-y-2">
          {objectCounts.text_words > 0 && (
            <div className="flex items-center justify-between p-2 bg-gray-700 rounded">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#3b82f6' }}></div>
                <span className="text-sm text-gray-300">Text Words</span>
              </div>
              <span className="text-sm font-medium text-white">{objectCounts.text_words}</span>
            </div>
          )}

          {objectCounts.graphic_rects > 0 && (
            <div className="flex items-center justify-between p-2 bg-gray-700 rounded">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#f59e0b' }}></div>
                <span className="text-sm text-gray-300">Graphic Rects</span>
              </div>
              <span className="text-sm font-medium text-white">{objectCounts.graphic_rects}</span>
            </div>
          )}

          {objectCounts.graphic_lines > 0 && (
            <div className="flex items-center justify-between p-2 bg-gray-700 rounded">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#ef4444' }}></div>
                <span className="text-sm text-gray-300">Graphic Lines</span>
              </div>
              <span className="text-sm font-medium text-white">{objectCounts.graphic_lines}</span>
            </div>
          )}

          {objectCounts.graphic_curves > 0 && (
            <div className="flex items-center justify-between p-2 bg-gray-700 rounded">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#8b5cf6' }}></div>
                <span className="text-sm text-gray-300">Graphic Curves</span>
              </div>
              <span className="text-sm font-medium text-white">{objectCounts.graphic_curves}</span>
            </div>
          )}

          {objectCounts.images > 0 && (
            <div className="flex items-center justify-between p-2 bg-gray-700 rounded">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#ec4899' }}></div>
                <span className="text-sm text-gray-300">Images</span>
              </div>
              <span className="text-sm font-medium text-white">{objectCounts.images}</span>
            </div>
          )}

          {objectCounts.tables > 0 && (
            <div className="flex items-center justify-between p-2 bg-gray-700 rounded">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: '#06b6d4' }}></div>
                <span className="text-sm text-gray-300">Tables</span>
              </div>
              <span className="text-sm font-medium text-white">{objectCounts.tables}</span>
            </div>
          )}
        </div>
      </div>

      {/* PDF Viewer with overlay */}
      <div className="flex-1 bg-gray-900 p-4 overflow-auto">
        <PdfViewer pdfUrl={pdfUrl}>
          <PdfViewer.Canvas pdfUrl={pdfUrl}>
            <SignatureObjectsOverlay objects={flattenedObjects} />
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
  const { renderScale, currentPage } = usePdfViewer();

  // Filter objects for current page
  const pageObjects = useMemo(
    () => objects.filter((obj) => obj.page === currentPage),
    [objects, currentPage]
  );

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
        const width = (x1 - x0) * renderScale;
        const height = (y1 - y0) * renderScale;
        const left = x0 * renderScale;
        const top = y0 * renderScale;

        return (
          <div
            key={idx}
            style={{
              position: 'absolute',
              left: `${left}px`,
              top: `${top}px`,
              width: `${width}px`,
              height: `${height}px`,
              border: `2px solid ${obj.color}`,
              backgroundColor: `${obj.color}15`, // 15 = ~9% opacity
              pointerEvents: 'none',
            }}
          />
        );
      })}
    </div>
  );
}
