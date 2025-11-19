/**
 * PageSelectionStep
 * First step in template builder (create mode only)
 * Allows user to select which pages from the PDF will become the template
 */

import { useEffect, useState } from 'react';
import { pdfjs, Document } from 'react-pdf';
import { PageListSidebar } from './PageListSidebar';
import { PageCarousel } from './PageCarousel';

// Configure PDF.js worker (same as main PdfViewer)
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

interface PageSelectionStepProps {
  pdfUrl: string;
  selectedPages: number[];
  onPagesChange: (pages: number[]) => void;
}

export function PageSelectionStep({
  pdfUrl,
  selectedPages,
  onPagesChange,
}: PageSelectionStepProps) {
  // Get page count from loaded PDF document
  const [numPages, setNumPages] = useState<number>(0);
  // Track which page is focused in the carousel
  const [focusedPageIndex, setFocusedPageIndex] = useState(0);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    console.log('[PageSelectionStep] PDF loaded, numPages:', numPages);
    setNumPages(numPages);
  };
  const handleTogglePage = (pageIndex: number) => {
    const newSelected = new Set(selectedPages);
    if (newSelected.has(pageIndex)) {
      newSelected.delete(pageIndex);
    } else {
      newSelected.add(pageIndex);
    }
    onPagesChange(Array.from(newSelected).sort((a, b) => a - b));
  };

  const handleSelectAll = () => {
    if (numPages > 0) {
      onPagesChange(Array.from({ length: numPages }, (_, i) => i));
    }
  };

  const handleDeselectAll = () => {
    onPagesChange([]);
  };

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+A / Cmd+A to select all
      if (e.key === 'a' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        handleSelectAll();
      }
      // Escape to deselect all
      else if (e.key === 'Escape') {
        handleDeselectAll();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [numPages]);

  return (
    <div className="h-full w-full overflow-hidden">
      <Document
        file={pdfUrl}
        onLoadSuccess={onDocumentLoadSuccess}
        className="h-full w-full"
        loading={
          <div className="flex items-center justify-center h-full w-full bg-gray-900">
            <p className="text-gray-400">Loading PDF...</p>
          </div>
        }
        error={
          <div className="flex items-center justify-center h-full w-full bg-gray-900">
            <p className="text-red-400">Failed to load PDF</p>
          </div>
        }
      >
        {numPages > 0 ? (
          <div className="flex h-full w-full bg-gray-900 overflow-hidden">
            <PageListSidebar
              totalPages={numPages}
              selectedPages={selectedPages}
              onTogglePage={handleTogglePage}
              onSelectAll={handleSelectAll}
              onDeselectAll={handleDeselectAll}
              onFocusPage={setFocusedPageIndex}
            />

            <PageCarousel
              totalPages={numPages}
              selectedPages={selectedPages}
              onTogglePage={handleTogglePage}
              focusedPageIndex={focusedPageIndex}
              onFocusChange={setFocusedPageIndex}
            />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full w-full bg-gray-900">
            <p className="text-gray-400">Loading pages...</p>
          </div>
        )}
      </Document>
    </div>
  );
}
