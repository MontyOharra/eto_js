/**
 * PdfViewerSection
 * PDF viewer with object overlays on the right side
 */

import { PdfViewer } from '../../../../../../shared/components/pdf';
import { PdfObjectOverlay } from './PdfObjectOverlay';

interface PdfObject {
  type: string;
  page: number;
  bbox: [number, number, number, number];
  text?: string;
}

interface PdfViewerSectionProps {
  pdfUrl: string;
  pdfFileId: number;
  pdfObjects: PdfObject[];
  selectedTypes: Set<string>;
  selectedObjects: Set<string>;
  onObjectClick: (objectId: string) => void;
  pdfScale: number;
  pdfCurrentPage: number;
  onPdfScaleChange: (scale: number) => void;
  onPdfCurrentPageChange: (page: number) => void;
}

export function PdfViewerSection({
  pdfUrl,
  pdfFileId,
  pdfObjects,
  selectedTypes,
  selectedObjects,
  onObjectClick,
  pdfScale,
  pdfCurrentPage,
  onPdfScaleChange,
  onPdfCurrentPageChange,
}: PdfViewerSectionProps) {
  return (
    <div className="flex-1 overflow-hidden bg-gray-800">
      <PdfViewer
        pdfUrl={pdfUrl}
        initialScale={pdfScale}
        initialPage={pdfCurrentPage}
        onScaleChange={onPdfScaleChange}
        onPageChange={onPdfCurrentPageChange}
      >
        <PdfViewer.Canvas pdfUrl={pdfUrl}>
          <PdfObjectOverlay
            objects={pdfObjects}
            selectedTypes={selectedTypes}
            selectedObjects={selectedObjects}
            onObjectClick={onObjectClick}
          />
        </PdfViewer.Canvas>
        <PdfViewer.ControlsSidebar position="right" />
      </PdfViewer>
    </div>
  );
}
