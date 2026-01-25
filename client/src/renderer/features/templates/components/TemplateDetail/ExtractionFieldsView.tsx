/**
 * ExtractionFieldsView
 * Read-only view of extraction fields overlaid on PDF
 * All extraction fields are always visible (no toggle)
 */

import { useMemo } from 'react';
import { PdfViewer, usePdfViewer } from '../../../pdf';
import type { ExtractionField } from '../../types';

interface ExtractionFieldsViewProps {
  pdfUrl: string;
  extractionFields: ExtractionField[];
}

export function ExtractionFieldsView({
  pdfUrl,
  extractionFields,
}: ExtractionFieldsViewProps) {
  return (
    <div className="h-full flex">
      {/* Sidebar */}
      <div className="w-80 border-r border-gray-700 bg-gray-900 p-4 overflow-y-auto">
        <h3 className="text-sm font-semibold text-white mb-4">Extraction Fields</h3>
        <p className="text-sm text-gray-400 mb-4">
          Fields to extract from matching documents.
        </p>

        {/* Total count */}
        <div className="mb-4 p-3 bg-gray-800 rounded">
          <div className="text-sm text-gray-400">Total Fields</div>
          <div className="text-2xl font-bold text-white">{extractionFields.length}</div>
        </div>

        {/* Fields list */}
        <div className="space-y-2">
          {extractionFields.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>No extraction fields defined</p>
            </div>
          ) : (
            extractionFields.map((field, idx) => (
              <div key={idx} className="p-3 bg-gray-800 rounded">
                <div className="font-medium text-white text-sm mb-1">
                  {field.name}
                </div>
                {field.description && (
                  <div className="text-xs text-gray-400 mb-2">
                    {field.description}
                  </div>
                )}
                <div className="text-xs text-gray-500">
                  Page {field.page}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* PDF Viewer with overlay */}
      <div className="flex-1 bg-gray-900 p-4 overflow-auto">
        <PdfViewer pdfUrl={pdfUrl} autoFitWidth>
          <PdfViewer.Canvas pdfUrl={pdfUrl}>
            <ExtractionFieldsOverlay fields={extractionFields} />
          </PdfViewer.Canvas>
          <PdfViewer.ControlsSidebar position="right" />
        </PdfViewer>
      </div>
    </div>
  );
}

// Overlay component to render extraction field bounding boxes
interface ExtractionFieldsOverlayProps {
  fields: ExtractionField[];
}

function ExtractionFieldsOverlay({
  fields,
}: ExtractionFieldsOverlayProps) {
  const { renderScale, currentPage } = usePdfViewer();

  // Filter fields for current page
  const pageFields = useMemo(
    () => fields.filter((field) => field.page === currentPage),
    [fields, currentPage]
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
      {pageFields.map((field, idx) => {
        const [x0, y0, x1, y1] = field.bbox;
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
              border: '2px solid rgba(147, 51, 234, 0.8)', // purple (matching TemplateBuilder)
              backgroundColor: 'rgba(147, 51, 234, 0.2)',
              pointerEvents: 'none',
            }}
            title={field.name}
          >
            {/* Field label */}
            <div
              style={{
                position: 'absolute',
                top: '-20px',
                left: '0',
                backgroundColor: '#9333ea', // purple-600
                color: 'white',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: '500',
                whiteSpace: 'nowrap',
                pointerEvents: 'none',
              }}
            >
              {field.name}
            </div>
          </div>
        );
      })}
    </div>
  );
}
