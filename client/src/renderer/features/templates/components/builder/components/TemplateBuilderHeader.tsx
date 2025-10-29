/**
 * TemplateBuilderHeader
 * Header section with title, PDF info, and close button
 */

import { PdfFileMetadataDTO } from '../../../../pdf-files/api/types';
import { EmailData } from '../../../../emails/mocks/useMockEmailApi';

interface TemplateBuilderHeaderProps {
  pdfMetadata: PdfFileMetadataDTO | null;
  emailData?: EmailData | null;
  onClose: () => void;
  mode?: 'create' | 'edit';
}

export function TemplateBuilderHeader({
  pdfMetadata,
  emailData,
  onClose,
  mode = 'create',
}: TemplateBuilderHeaderProps) {
  // Format file size
  const formatFileSize = (bytes: number | null): string => {
    if (!bytes) return 'Unknown';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const title = mode === 'edit' ? 'Edit Template' : 'Template Builder';

  return (
    <div className="flex items-center justify-between p-4 border-b border-gray-700 flex-shrink-0">
      <div className="flex items-center space-x-4">
        <h2 className="text-xl font-semibold text-white">{title}</h2>

        {pdfMetadata && (
          <>
            {/* Source */}
            <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
              <span className="text-gray-400">Source:</span>{' '}
              {pdfMetadata.email_id !== null && emailData ? (
                <span className="font-mono">{emailData.sender_email}</span>
              ) : pdfMetadata.email_id !== null ? (
                <span className="font-mono">Email (ID: {pdfMetadata.email_id})</span>
              ) : (
                'Manual Upload'
              )}
            </div>

            {/* PDF Filename */}
            <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
              <span className="text-gray-400">PDF:</span>{' '}
              <span className="font-mono">{pdfMetadata.original_filename}</span>
            </div>

            {/* File Size */}
            <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
              <span className="text-gray-400">Size:</span>{' '}
              <span className="font-mono">{formatFileSize(pdfMetadata.file_size)}</span>
            </div>
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
