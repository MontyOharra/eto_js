/**
 * DebugMatchResultsView
 * Displays template match test results with PDF overlay
 * Shows signature objects colored by match status (green=matched, red=failed)
 */

import { useMemo, useState } from 'react';
import { PdfViewer, usePdfViewer } from '../../../pdf';
import type { DebugMatchResponse, DebugMatchObjectResult } from '../../api/types';

interface DebugMatchResultsViewProps {
  pdfUrl: string;
  results: DebugMatchResponse;
}

export function DebugMatchResultsView({
  pdfUrl,
  results,
}: DebugMatchResultsViewProps) {
  // Visibility state for match status
  const [showMatched, setShowMatched] = useState(true);
  const [showFailed, setShowFailed] = useState(true);

  // Count matched vs failed objects
  const matchCounts = useMemo(() => {
    const matched = results.objects.filter((obj) => obj.matched).length;
    const failed = results.objects.filter((obj) => !obj.matched).length;
    return { matched, failed, total: results.objects.length };
  }, [results.objects]);

  // Count by object type
  const countsByType = useMemo(() => {
    const counts: Record<string, { matched: number; total: number }> = {};
    for (const obj of results.objects) {
      if (!counts[obj.object_type]) {
        counts[obj.object_type] = { matched: 0, total: 0 };
      }
      counts[obj.object_type].total++;
      if (obj.matched) {
        counts[obj.object_type].matched++;
      }
    }
    return counts;
  }, [results.objects]);

  // Filter objects based on visibility
  const visibleObjects = useMemo(() => {
    return results.objects.filter((obj) => {
      if (obj.matched && !showMatched) return false;
      if (!obj.matched && !showFailed) return false;
      return true;
    });
  }, [results.objects, showMatched, showFailed]);

  // Format object type for display
  const formatObjectType = (type: string) => {
    return type
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div className="h-full flex">
      {/* Sidebar */}
      <div className="w-80 border-r border-gray-700 bg-gray-900 p-4 overflow-y-auto">
        <h3 className="text-sm font-semibold text-white mb-4">Match Results</h3>

        {/* Overall status */}
        <div className={`mb-4 p-3 rounded border ${
          results.overall_match
            ? 'bg-green-900/30 border-green-700'
            : 'bg-red-900/30 border-red-700'
        }`}>
          <div className="flex items-center space-x-2">
            {results.overall_match ? (
              <svg className="w-5 h-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
            <span className={`font-medium ${results.overall_match ? 'text-green-400' : 'text-red-400'}`}>
              {results.overall_match ? 'Template Matches' : 'Template Does Not Match'}
            </span>
          </div>
        </div>

        {/* Page count info */}
        <div className={`mb-4 p-3 rounded ${
          results.page_count_match ? 'bg-gray-800' : 'bg-red-900/30 border border-red-700'
        }`}>
          <div className="text-sm text-gray-400 mb-1">Page Count</div>
          <div className="flex items-center justify-between">
            <span className="text-white">Template: {results.template_page_count}</span>
            <span className="text-white">PDF: {results.pdf_page_count}</span>
          </div>
          {!results.page_count_match && (
            <div className="text-sm text-red-400 mt-1">Page counts do not match</div>
          )}
        </div>

        {/* Object counts */}
        <div className="mb-4 p-3 bg-gray-800 rounded">
          <div className="text-sm text-gray-400 mb-2">Signature Objects</div>
          <div className="flex items-center justify-between text-white">
            <span>{matchCounts.matched} matched</span>
            <span>{matchCounts.failed} failed</span>
          </div>
          <div className="text-sm text-gray-400 mt-1">
            {matchCounts.total} total
          </div>
        </div>

        {/* Visibility toggles */}
        <div className="mb-4 space-y-2">
          <button
            onClick={() => setShowMatched(!showMatched)}
            className={`w-full flex items-center justify-between p-2 rounded transition-colors ${
              showMatched ? 'bg-green-900/30 text-green-400' : 'bg-gray-800 text-gray-500'
            }`}
          >
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded bg-green-500"></div>
              <span className="text-sm">Matched</span>
            </div>
            <span className="text-sm font-medium">{matchCounts.matched}</span>
          </button>

          <button
            onClick={() => setShowFailed(!showFailed)}
            className={`w-full flex items-center justify-between p-2 rounded transition-colors ${
              showFailed ? 'bg-red-900/30 text-red-400' : 'bg-gray-800 text-gray-500'
            }`}
          >
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded bg-red-500"></div>
              <span className="text-sm">Failed</span>
            </div>
            <span className="text-sm font-medium">{matchCounts.failed}</span>
          </button>
        </div>

        {/* Breakdown by type */}
        <div className="space-y-2">
          <div className="text-sm text-gray-400 mb-2">By Object Type</div>
          {Object.entries(countsByType).map(([type, counts]) => (
            <div
              key={type}
              className="flex items-center justify-between p-2 bg-gray-800 rounded text-sm"
            >
              <span className="text-white">{formatObjectType(type)}</span>
              <div className="flex items-center space-x-1">
                <span className={counts.matched === counts.total ? 'text-green-400' : 'text-red-400'}>
                  {counts.matched}
                </span>
                <span className="text-gray-500">/</span>
                <span className="text-gray-400">{counts.total}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* PDF Viewer with overlay */}
      <div className="flex-1 bg-gray-900 p-4 overflow-auto">
        <PdfViewer pdfUrl={pdfUrl} autoFitWidth>
          <PdfViewer.Canvas pdfUrl={pdfUrl}>
            <DebugMatchOverlay objects={visibleObjects} />
          </PdfViewer.Canvas>
          <PdfViewer.ControlsSidebar position="right" />
        </PdfViewer>
      </div>
    </div>
  );
}

// Overlay component to render match result bounding boxes
interface DebugMatchOverlayProps {
  objects: DebugMatchObjectResult[];
}

function DebugMatchOverlay({ objects }: DebugMatchOverlayProps) {
  const { renderScale, currentPage, pdfDimensions } = usePdfViewer();
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

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
        // Text objects don't need Y-axis flipping
        // Graphics (rects, lines) and images need flipping
        let screenY0: number, screenY1: number;

        const noFlipping = obj.object_type === 'text_word' ||
                           obj.object_type === 'table' ||
                           obj.object_type === 'graphic_curve';

        if (noFlipping) {
          screenY0 = y0;
          screenY1 = y1;
        } else {
          screenY0 = pageHeight - y1;
          screenY1 = pageHeight - y0;
        }

        const width = (x1 - x0) * renderScale;
        const height = (screenY1 - screenY0) * renderScale;
        const left = x0 * renderScale;
        const top = screenY0 * renderScale;

        // Colors based on match status
        const fillColor = obj.matched
          ? 'rgba(34, 197, 94, 0.2)'   // green-500 with low opacity
          : 'rgba(239, 68, 68, 0.2)';  // red-500 with low opacity
        const borderColor = obj.matched
          ? 'rgba(34, 197, 94, 0.8)'   // green-500
          : 'rgba(239, 68, 68, 0.8)';  // red-500

        const isHovered = hoveredIndex === idx;

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
              backgroundColor: isHovered ? (obj.matched ? 'rgba(34, 197, 94, 0.4)' : 'rgba(239, 68, 68, 0.4)') : fillColor,
              pointerEvents: 'auto',
              cursor: 'pointer',
            }}
            onMouseEnter={() => setHoveredIndex(idx)}
            onMouseLeave={() => setHoveredIndex(null)}
          >
            {/* Tooltip on hover */}
            {isHovered && (
              <div
                style={{
                  position: 'absolute',
                  bottom: '100%',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  marginBottom: '4px',
                  padding: '8px 12px',
                  backgroundColor: 'rgba(0, 0, 0, 0.9)',
                  borderRadius: '6px',
                  whiteSpace: 'nowrap',
                  zIndex: 1000,
                  pointerEvents: 'none',
                }}
              >
                <div className="text-xs text-gray-300">
                  <div className="font-medium text-white mb-1">
                    {obj.object_type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  </div>
                  <div className={obj.matched ? 'text-green-400' : 'text-red-400'}>
                    {obj.matched ? 'Matched' : 'Not Found'}
                  </div>
                  {obj.expected_text && (
                    <div className="mt-1 text-gray-400">
                      Expected: <span className="text-white">"{obj.expected_text}"</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
