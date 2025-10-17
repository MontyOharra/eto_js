/**
 * Run Detail Modal
 * Displays detailed information about an ETO run including PDF info,
 * execution details, and allows viewing the PDF and specifics
 */

import { useState, useEffect } from 'react';
import { PdfViewer } from '../../../../shared/components/pdf';
import { useMockEtoApi } from '../../hooks/useMockEtoApi';
import { StatusBadge } from '../ui/StatusBadge';
import type { EtoRunDetail } from '../../types';

interface RunDetailModalProps {
  isOpen: boolean;
  runId: number | null;
  onClose: () => void;
}

type ViewMode = 'summary' | 'detail';

export function RunDetailModal({ isOpen, runId, onClose }: RunDetailModalProps) {
  const { getEtoRunDetail, getPdfDownloadUrl, isLoading } = useMockEtoApi();
  const [runDetail, setRunDetail] = useState<EtoRunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('summary');

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
            <>
              {viewMode === 'summary' ? (
                /* Summary View */
                <div className="p-4 flex gap-4 h-full">
                  {/* Left Column - Specifics Only */}
                  <div className="w-2/5 flex flex-col">
                    {/* Specifics Section - Full Height */}
                    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 flex flex-col flex-1 overflow-hidden">
                      <h3 className="text-lg font-semibold text-white mb-3">
                        {runDetail.status === 'success' ? 'Actions Executed' : 'Error Details'}
                      </h3>

                      {/* Scrollable content area */}
                      <div className="flex-1 overflow-auto bg-gray-900 rounded p-3 font-mono text-xs">
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
                    </div>
                  </div>

                  {/* Right Column - PDF Viewer */}
                  <div className="w-3/5 flex flex-col">
                    <div className="bg-gray-800 border border-gray-700 rounded-lg flex-1 overflow-hidden relative p-4">
                      {pdfUrl ? (
                        <PdfViewer pdfUrl={pdfUrl} onError={handlePdfError}>
                          <PdfViewer.Canvas pdfUrl={pdfUrl} onError={handlePdfError} />
                          <PdfViewer.InfoPanel
                            position="top-right"
                            filename={runDetail.pdf.original_filename}
                            fileSize={runDetail.pdf.file_size}
                          />
                          <PdfViewer.Controls position="bottom-center" />
                        </PdfViewer>
                      ) : (
                        <div className="flex items-center justify-center h-full">
                          <p className="text-gray-400">No PDF available</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                /* Detail View - Placeholder */
                <div className="p-4 h-full flex items-center justify-center">
                  <div className="text-center">
                    <h3 className="text-xl font-semibold text-white mb-2">Detail View</h3>
                    <p className="text-gray-400">Coming soon: Extraction & Transformation details</p>
                  </div>
                </div>
              )}
            </>
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
