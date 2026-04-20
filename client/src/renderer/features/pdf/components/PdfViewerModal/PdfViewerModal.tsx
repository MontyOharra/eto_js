/**
 * PdfViewerModal
 * Full-screen modal for viewing PDF files
 */

import { PdfViewer } from '../PdfViewer';
import { getPdfDownloadUrl } from '../../api/hooks';

interface PdfViewerModalProps {
  isOpen: boolean;
  pdfId: number | null;
  filename?: string;
  onClose: () => void;
}

export function PdfViewerModal({
  isOpen,
  pdfId,
  filename,
  onClose,
}: PdfViewerModalProps) {
  if (!isOpen || !pdfId) return null;

  const pdfUrl = getPdfDownloadUrl(pdfId);

  const handlePdfError = (error: Error) => {
    console.error('PDF load error:', error);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
      <div className="bg-gray-900 rounded-lg shadow-xl w-[95vw] h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700 flex-shrink-0">
          <div>
            <h2 className="text-xl font-bold text-white">
              {filename || 'PDF Viewer'}
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <a
              href={getPdfDownloadUrl(pdfId, true)}
              className="px-3 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-md text-sm transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
              </svg>
              Download
            </a>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* PDF Viewer Content */}
        <div className="flex-1 overflow-hidden p-4">
          <PdfViewer pdfUrl={pdfUrl} onError={handlePdfError} autoFitWidth>
            <PdfViewer.Canvas pdfUrl={pdfUrl} onError={handlePdfError} />
            <PdfViewer.ControlsSidebar position="right" />
          </PdfViewer>
        </div>
      </div>
    </div>
  );
}
