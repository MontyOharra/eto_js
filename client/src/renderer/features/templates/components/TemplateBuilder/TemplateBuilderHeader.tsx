/**
 * TemplateBuilderHeader
 * Header section with title, PDF info, and close button
 */

import type { PdfFileMetadata } from '../../../pdf';
import { formatFileSize } from '../../../../shared/utils/formatUtils';

interface TemplateBuilderHeaderProps {
  pdfMetadata: PdfFileMetadata | null;
  onClose: () => void;
}

export function TemplateBuilderHeader({
  pdfMetadata,
  onClose,
}: TemplateBuilderHeaderProps) {
  return (
    <div className="flex items-center justify-between p-4 border-b border-gray-700 flex-shrink-0">
      <div className="flex items-center space-x-4">
        <h2 className="text-xl font-semibold text-white">Template Builder</h2>

        {pdfMetadata && (
          <>
            {/* PDF Filename */}
            <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
              <span className="text-gray-400">PDF:</span>{' '}
              <span className="font-mono">{pdfMetadata.original_filename}</span>
            </div>

            {/* File Size */}
            {pdfMetadata.file_size && (
              <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
                <span className="text-gray-400">Size:</span>{' '}
                <span className="font-mono">{formatFileSize(pdfMetadata.file_size)}</span>
              </div>
            )}

            {/* Page Count */}
            {pdfMetadata.page_count && (
              <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
                <span className="text-gray-400">Pages:</span>{' '}
                <span className="font-mono">{pdfMetadata.page_count}</span>
              </div>
            )}
          </>
        )}
      </div>

      <button
        onClick={onClose}
        className="ml-4 p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-gray-800"
        aria-label="Close"
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
  );
}
