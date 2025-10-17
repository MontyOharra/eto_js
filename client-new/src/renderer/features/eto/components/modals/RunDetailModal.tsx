/**
 * Run Detail Modal
 * Displays detailed information about an ETO run including PDF info,
 * execution details, and allows viewing the PDF and specifics
 */

import { useState, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { useMockEtoApi } from '../../hooks/useMockEtoApi';
import { StatusBadge } from '../ui/StatusBadge';
import type { EtoRunDetail } from '../../types';

// Configure PDF.js worker - use local worker from node_modules
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

interface RunDetailModalProps {
  isOpen: boolean;
  runId: number | null;
  onClose: () => void;
}

export function RunDetailModal({ isOpen, runId, onClose }: RunDetailModalProps) {
  const { getEtoRunDetail, getPdfDownloadUrl, isLoading } = useMockEtoApi();
  const [runDetail, setRunDetail] = useState<EtoRunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  // PDF viewer state
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.0);

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
      console.log(url);
      setPdfUrl(url);
      console.log('PDF URL set:', url);
      console.log('Expected file location: client-new/public' + url);

      // Test if file exists by attempting to fetch it
      fetch(url, { method: 'HEAD' })
        .then(response => {
          console.log('PDF file check:', {
            url,
            status: response.status,
            statusText: response.statusText,
            contentType: response.headers.get('Content-Type')
          });
          if (!response.ok) {
            console.error(`PDF file not found at ${url}. Please add a PDF file named "${runDetail.pdf.id}.pdf" to client-new/public/data/pdfs/`);
          }
        })
        .catch(err => console.error('PDF file check failed:', err));
    }
  }, [runDetail?.pdf.id]);

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

  // PDF document handlers
  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setCurrentPage(1);
    console.log('PDF loaded successfully, pages:', numPages);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF load error:', error);
    setError(`Failed to load PDF: ${error.message}`);
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
        <div className="flex items-center justify-between p-4 border-b border-gray-700 flex-shrink-0">
          <div className="flex items-center space-x-3">
            <h2 className="text-xl font-semibold text-white">ETO Run Details</h2>
            {runDetail && <StatusBadge status={runDetail.status} />}
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
            <div className="p-4 flex gap-4 h-full">
              {/* Left Column - Metadata and Specifics */}
              <div className="w-2/5 flex flex-col gap-3">
                {/* Run Metadata Section */}
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-white mb-3">Run Information</h3>

                  <div className="grid grid-cols-2 gap-4">
                    {/* Left Column */}
                    <div className="space-y-3">
                      {/* PDF Info */}
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-1">
                          PDF Filename
                        </label>
                        <p className="text-white font-mono text-sm">
                          {runDetail.pdf.original_filename}
                        </p>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-medium text-gray-400 mb-1">
                            File Size
                          </label>
                          <p className="text-white text-sm">
                            {formatFileSize(runDetail.pdf.file_size)}
                          </p>
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-400 mb-1">
                            Pages
                          </label>
                          <p className="text-white text-sm">
                            {runDetail.pdf.page_count ?? 'Unknown'}
                          </p>
                        </div>
                      </div>

                      {/* Source Info */}
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-1">
                          Source
                        </label>
                        <p className="text-white text-sm">
                          {runDetail.source.type === 'email' ? (
                            <>
                              Email from{' '}
                              <span className="font-mono">
                                {runDetail.source.sender_email || 'Unknown'}
                              </span>
                            </>
                          ) : (
                            'Manual Upload'
                          )}
                        </p>
                      </div>

                      {/* Email-specific fields */}
                      {runDetail.source.type === 'email' && runDetail.source.subject && (
                        <div>
                          <label className="block text-xs font-medium text-gray-400 mb-1">
                            Email Subject
                          </label>
                          <p className="text-white text-sm">{runDetail.source.subject}</p>
                        </div>
                      )}
                    </div>

                    {/* Right Column */}
                    <div className="space-y-3">
                      {/* Execution Times */}
                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-1">
                          Started At
                        </label>
                        <p className="text-white text-sm font-mono">
                          {formatTimestamp(runDetail.started_at)}
                        </p>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-1">
                          Completed At
                        </label>
                        <p className="text-white text-sm font-mono">
                          {formatTimestamp(runDetail.completed_at)}
                        </p>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-400 mb-1">
                          Total Duration
                        </label>
                        <p className="text-white text-sm font-mono">
                          {formatDuration(runDetail.started_at, runDetail.completed_at)}
                        </p>
                      </div>

                      {/* Matched Template */}
                      {runDetail.matched_template && (
                        <div>
                          <label className="block text-xs font-medium text-gray-400 mb-1">
                            Matched Template
                          </label>
                          <p className="text-white text-sm">
                            {runDetail.matched_template.template_name}
                            <span className="text-gray-400 ml-2">
                              (v{runDetail.matched_template.version_num})
                            </span>
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Specifics Section Placeholder */}
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 flex items-center justify-center flex-1">
                  <p className="text-gray-400 text-lg font-medium">SPECIFICS</p>
                </div>
              </div>

              {/* Right Column - PDF Viewer */}
              <div className="w-3/5 flex flex-col gap-3">
                {/* PDF Controls */}
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-2 flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                      disabled={currentPage <= 1}
                      className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 disabled:bg-gray-900 disabled:text-gray-500 disabled:cursor-not-allowed text-white rounded transition-colors"
                    >
                      ← Prev
                    </button>
                    <span className="text-sm text-gray-300">
                      Page {currentPage} of {numPages || '?'}
                    </span>
                    <button
                      onClick={() => setCurrentPage((prev) => Math.min(numPages || prev, prev + 1))}
                      disabled={currentPage >= (numPages || 0)}
                      className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 disabled:bg-gray-900 disabled:text-gray-500 disabled:cursor-not-allowed text-white rounded transition-colors"
                    >
                      Next →
                    </button>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setScale((prev) => Math.max(0.5, prev - 0.25))}
                      className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
                    >
                      Zoom Out
                    </button>
                    <span className="text-sm text-gray-300 min-w-[60px] text-center">
                      {Math.round(scale * 100)}%
                    </span>
                    <button
                      onClick={() => setScale((prev) => Math.min(2.0, prev + 0.25))}
                      className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
                    >
                      Zoom In
                    </button>
                  </div>
                </div>

                {/* PDF Document */}
                <div className="bg-gray-800 border border-gray-700 rounded-lg flex-1 overflow-auto">
                  {pdfUrl ? (
                    <div className="flex justify-center p-2">
                      <Document
                        file={pdfUrl}
                        onLoadSuccess={onDocumentLoadSuccess}
                        onLoadError={onDocumentLoadError}
                        loading={
                          <div className="flex items-center justify-center h-96">
                            <p className="text-gray-400">Loading PDF...</p>
                          </div>
                        }
                        error={
                          <div className="flex items-center justify-center h-96">
                            <p className="text-red-400">Failed to load PDF</p>
                          </div>
                        }
                      >
                        <Page
                          pageNumber={currentPage}
                          scale={scale}
                          renderTextLayer={false}
                          renderAnnotationLayer={false}
                          loading=""
                          error=""
                        />
                      </Document>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-96">
                      <p className="text-gray-400">No PDF available</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-4 border-t border-gray-700 flex-shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-gray-600 text-gray-300 rounded hover:bg-gray-800 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
