/**
 * PdfInfoPanel
 * Displays PDF metadata (filename, size, pages) with flexible positioning
 */

import { usePdfViewer } from './PdfViewerContext';

export interface PdfInfoPanelProps {
  position?: 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right';
  filename?: string;
  fileSize?: number;
  className?: string;
}

export function PdfInfoPanel({
  position = 'top-right',
  filename,
  fileSize,
  className = '',
}: PdfInfoPanelProps) {
  const { numPages } = usePdfViewer();

  // Position classes mapping
  const positionClasses = {
    'top-left': 'top-2 left-2',
    'top-center': 'top-2 left-1/2 transform -translate-x-1/2',
    'top-right': 'top-2 right-2',
    'bottom-left': 'bottom-2 left-2',
    'bottom-center': 'bottom-2 left-1/2 transform -translate-x-1/2',
    'bottom-right': 'bottom-2 right-2',
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  return (
    <div
      className={`absolute ${positionClasses[position]} bg-gray-900/90 backdrop-blur-sm border border-gray-600 rounded-lg p-2 text-xs z-10 ${className}`}
    >
      {filename && (
        <div
          className="text-gray-300 font-mono mb-1 max-w-[250px] truncate"
          title={filename}
        >
          {filename}
        </div>
      )}
      <div className="flex items-center space-x-3 text-gray-400">
        {fileSize && <span>{formatFileSize(fileSize)}</span>}
        {fileSize && numPages && <span>•</span>}
        {numPages && <span>{numPages} pages</span>}
      </div>
    </div>
  );
}
