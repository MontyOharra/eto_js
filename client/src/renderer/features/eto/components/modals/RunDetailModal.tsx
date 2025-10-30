/**
 * Run Detail Modal
 * Displays detailed information about an ETO run including PDF info,
 * execution details, and allows viewing the PDF and specifics
 */

import { useState, useEffect, useRef } from 'react';
import { PdfViewer, usePdfViewer } from '../../../pdf';
import { useMockEtoApi } from '../../hooks/useMockEtoApi';
import { StatusBadge } from '../ui/StatusBadge';
import { ExtractedFieldsOverlay } from '../overlays/ExtractedFieldsOverlay';
import { ExecutedPipelineViewer, ExecutedPipelineViewerRef } from '../../../pipelines/components/ExecutedPipelineViewer';
import type { EtoRunDetail } from '../../types';

interface RunDetailModalProps {
  isOpen: boolean;
  runId: number | null;
  onClose: () => void;
}

type ViewMode = 'summary' | 'detail';

// Helper component to trigger fit-to-width on resize (only during divider drag)
function AutoFitOnResize({ isDragging }: { isDragging: boolean }) {
  const { fitToWidth, pdfDimensions } = usePdfViewer();
  const pdfViewerRef = useRef<HTMLDivElement>(null);
  const hasAutoFittedOnLoad = useRef(false);

  // Auto-fit when PDF first loads
  useEffect(() => {
    if (!pdfDimensions || !pdfViewerRef.current || hasAutoFittedOnLoad.current) {
      return;
    }

    const pdfViewerContainer = pdfViewerRef.current.parentElement;
    if (!pdfViewerContainer) {
      return;
    }

    // Trigger fit-to-width on initial load
    const containerWidth = pdfViewerContainer.clientWidth;
    const sidebarWidth = 64; // w-16 = 64px
    fitToWidth(containerWidth, sidebarWidth);
    hasAutoFittedOnLoad.current = true;
  }, [pdfDimensions, fitToWidth]);

  // Trigger fit-to-width on resize, but ONLY when dragging the divider
  useEffect(() => {
    if (!isDragging || !pdfViewerRef.current || !pdfDimensions) {
      return;
    }

    // Get the actual PdfViewer container (same element the fit button measures)
    const pdfViewerContainer = pdfViewerRef.current.parentElement;
    if (!pdfViewerContainer) {
      return;
    }

    const resizeObserver = new ResizeObserver(() => {
      if (!pdfViewerContainer || !isDragging) {
        return;
      }

      const containerWidth = pdfViewerContainer.clientWidth;
      const sidebarWidth = 64; // w-16 = 64px
      fitToWidth(containerWidth, sidebarWidth);
    });

    resizeObserver.observe(pdfViewerContainer);

    return () => {
      resizeObserver.disconnect();
    };
  }, [fitToWidth, pdfDimensions, isDragging]);

  return <div ref={pdfViewerRef} style={{ display: 'none' }} />;
}

export function RunDetailModal({ isOpen, runId, onClose }: RunDetailModalProps) {
  const { getEtoRunDetail, getPdfDownloadUrl, isLoading } = useMockEtoApi();
  const [runDetail, setRunDetail] = useState<EtoRunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('summary');
  const [specificsWidth, setSpecificsWidth] = useState(60); // Percentage
  const [isDragging, setIsDragging] = useState(false);
  const pdfContainerRef = useRef<HTMLDivElement>(null);
  const pipelineViewerRef = useRef<ExecutedPipelineViewerRef>(null);

  // Reset to summary view when modal opens
  useEffect(() => {
    if (isOpen) {
      setViewMode('summary');
    }
  }, [isOpen]);

  // Fetch run details when modal opens
  useEffect(() => {
    if (isOpen && runId) {
      loadRunDetail();
    }
  }, [isOpen, runId]);

  // Set PDF URL when run detail is loaded
  useEffect(() => {
    if (runDetail?.pdf.id) {
      const url = getPdfDownloadUrl(runDetail.pdf.id);
      setPdfUrl(url);
    }
  }, [runDetail?.pdf.id, getPdfDownloadUrl]);

  const loadRunDetail = async () => {
    if (!runId) return;

    setError(null);
    try {
      const detail = await getEtoRunDetail(runId);
      setRunDetail(detail);
    } catch (err) {
      setError('Failed to load run details');
      console.error('Failed to load run details:', err);
    }
  };

  const handlePdfError = (pdfError: Error) => {
    console.error('PDF load error:', pdfError);
    setError(`Failed to load PDF: ${pdfError.message}`);
  };

  // Resizable divider handlers
  const handleMouseDown = () => {
    setIsDragging(true);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging) return;

    const modal = document.querySelector('.resize-container');
    if (!modal) return;

    const rect = modal.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const percentage = (offsetX / rect.width) * 100;

    // Constrain between 20% and 80%
    const constrainedPercentage = Math.min(Math.max(percentage, 20), 80);
    setSpecificsWidth(constrainedPercentage);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Attach/detach mouse event listeners
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging]);

  // Fit pipeline view when switching to detail mode
  useEffect(() => {
    if (viewMode === 'detail' && pipelineViewerRef.current) {
      // Delay to ensure the pipeline is rendered
      setTimeout(() => {
        pipelineViewerRef.current?.fitView();
      }, 100);
    }
  }, [viewMode]);

  // Auto-fit pipeline viewer when its container is resized (e.g., dragging divider)
  useEffect(() => {
    if (viewMode !== 'detail') return;

    const specificsContainer = document.querySelector('.resize-container .specifics-panel');
    if (!specificsContainer) return;

    const resizeObserver = new ResizeObserver(() => {
      if (pipelineViewerRef.current) {
        pipelineViewerRef.current.fitView();
      }
    });

    resizeObserver.observe(specificsContainer);

    return () => {
      resizeObserver.disconnect();
    };
  }, [viewMode]);

  // Format file size
  const formatFileSize = (bytes: number | null): string => {
    if (!bytes) return 'Unknown';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  // Format duration
  const formatDuration = (startedAt: string | null, completedAt: string | null): string => {
    if (!startedAt || !completedAt) return 'N/A';
    const start = new Date(startedAt).getTime();
    const end = new Date(completedAt).getTime();
    const durationMs = end - start;
    const seconds = Math.floor(durationMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;

    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${seconds}s`;
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string | null): string => {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  if (!isOpen || !runId) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-gray-900 rounded-lg shadow-xl w-full max-w-[95vw] h-[95vh] overflow-hidden border border-gray-700 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-gray-700 flex-shrink-0">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-3">
              <h2 className="text-xl font-semibold text-white">ETO Run Details</h2>
              {runDetail && <StatusBadge status={runDetail.status} />}
            </div>

            {/* View Mode Toggle */}
            <div className="flex items-center bg-gray-800 rounded-lg p-1 border-l border-gray-600 ml-4">
              <button
                onClick={() => setViewMode('summary')}
                className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                  viewMode === 'summary'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                Summary
              </button>
              <button
                onClick={() => setViewMode('detail')}
                className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                  viewMode === 'detail'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                Detail
              </button>
            </div>

            {runDetail && (
              <>
                {/* Source */}
                <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
                  <span className="text-gray-400">Source:</span>{' '}
                  {runDetail.source.type === 'email' ? (
                    <span className="font-mono">{runDetail.source.sender_email}</span>
                  ) : (
                    'Manual Upload'
                  )}
                </div>

                {/* Template */}
                {runDetail.matched_template && (
                  <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
                    <span className="text-gray-400">Template:</span>{' '}
                    {runDetail.matched_template.template_name}{' '}
                    <span className="text-gray-500">(v{runDetail.matched_template.version_num})</span>
                  </div>
                )}

                {/* Duration */}
                <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
                  <span className="text-gray-400">Duration:</span>{' '}
                  <span className="font-mono">{formatDuration(runDetail.started_at, runDetail.completed_at)}</span>
                </div>
              </>
            )}
          </div>

          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="text-blue-400">Loading run details...</div>
            </div>
          )}

          {error && (
            <div className="p-6">
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-4">
                <p className="text-red-200">{error}</p>
              </div>
            </div>
          )}

          {!isLoading && !error && runDetail && (
            <div className="pr-4 pl-2 py-4 flex h-full resize-container">
              {/* Left Column - Specifics */}
              <div className="flex flex-col specifics-panel" style={{ width: `${specificsWidth}%` }}>
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 flex flex-col flex-1 overflow-hidden">
                  <h3 className="text-lg font-semibold text-white mb-3">
                    {viewMode === 'summary'
                      ? (runDetail.status === 'success' ? 'Actions Executed' : 'Error Details')
                      : 'Transformation Pipeline'}
                  </h3>

                  {/* Scrollable content area */}
                  <div className="flex-1 overflow-auto bg-gray-900 rounded p-3 relative">
                    {/* Summary View - Actions/Errors (keep mounted, toggle visibility) */}
                    <div
                      className={`font-mono text-xs ${viewMode === 'summary' ? '' : 'hidden'}`}
                    >
                      {runDetail.status === 'success' && runDetail.pipeline_execution?.executed_actions ? (
                        <pre className="text-gray-300 whitespace-pre-wrap break-words">
                          {JSON.stringify(runDetail.pipeline_execution.executed_actions, null, 2)}
                        </pre>
                      ) : runDetail.status === 'failure' ? (
                        <div className="text-red-300">
                          <p className="font-bold mb-2">Error Type: {runDetail.error_type || 'Unknown'}</p>
                          <p className="mb-2">Message: {runDetail.error_message || 'No error message available'}</p>
                          {runDetail.pipeline_execution?.error_message && (
                            <>
                              <p className="font-bold mb-2 mt-4">Pipeline Error:</p>
                              <p>{runDetail.pipeline_execution.error_message}</p>
                            </>
                          )}
                        </div>
                      ) : (
                        <p className="text-gray-400">No details available</p>
                      )}
                    </div>

                    {/* Detail View - Pipeline Visualization (keep mounted, toggle visibility) */}
                    <div
                      className={`absolute inset-0 ${viewMode === 'detail' ? '' : 'hidden'}`}
                    >
                      {runDetail.pipeline_execution?.pipeline_definition_id ? (
                        <ExecutedPipelineViewer
                          ref={pipelineViewerRef}
                          pipelineDefinitionId={runDetail.pipeline_execution.pipeline_definition_id}
                          executionData={{
                            steps: runDetail.pipeline_execution.steps,
                            executed_actions: runDetail.pipeline_execution.executed_actions || undefined,
                          }}
                          extractedData={runDetail.data_extraction?.extracted_data || undefined}
                        />
                      ) : (
                        <div className="flex items-center justify-center h-full">
                          <p className="text-gray-400">No pipeline data available</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Resizable Divider */}
              <div
                className="w-1 bg-gray-700 hover:bg-blue-500 cursor-col-resize transition-colors flex-shrink-0 mx-1"
                onMouseDown={handleMouseDown}
                style={{
                  userSelect: 'none',
                  backgroundColor: isDragging ? '#3B82F6' : undefined,
                }}
              />

              {/* Right Column - PDF Viewer */}
              <div className="flex flex-col" style={{ width: `${100 - specificsWidth}%` }} ref={pdfContainerRef}>
                <div className="bg-gray-800 border border-gray-700 rounded-lg flex-1 overflow-hidden relative pr-4 pl-1 py-4">
                  {pdfUrl ? (
                    <PdfViewer pdfUrl={pdfUrl} onError={handlePdfError}>
                      <AutoFitOnResize isDragging={isDragging} />
                      <PdfViewer.Canvas pdfUrl={pdfUrl} onError={handlePdfError}>
                        {/* Show extraction field overlay in detail view */}
                        {viewMode === 'detail' && runDetail.data_extraction?.extracted_fields_with_boxes && (
                          <ExtractedFieldsOverlay
                            fields={runDetail.data_extraction.extracted_fields_with_boxes}
                          />
                        )}
                      </PdfViewer.Canvas>
                      <PdfViewer.ControlsSidebar position="right" />
                    </PdfViewer>
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <p className="text-gray-400">No PDF available</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-3 border-t border-gray-700 flex-shrink-0">
          {runDetail && (
            <div className="flex items-center space-x-4 text-xs text-gray-400">
              <div>
                <span className="text-gray-500">Started:</span>{' '}
                <span className="font-mono">{formatTimestamp(runDetail.started_at)}</span>
              </div>
              {runDetail.completed_at && (
                <div>
                  <span className="text-gray-500">Completed:</span>{' '}
                  <span className="font-mono">{formatTimestamp(runDetail.completed_at)}</span>
                </div>
              )}
            </div>
          )}
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-gray-600 text-gray-300 rounded hover:bg-gray-800 transition-colors text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
