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
}

export function PdfViewerSection({
  pdfUrl,
  pdfFileId,
  pdfObjects,
  selectedTypes,
}: PdfViewerSectionProps) {
  return (
    <div className="flex-1 overflow-hidden bg-gray-800">
      <PdfViewer pdfUrl={pdfUrl}>
        <PdfViewer.Canvas pdfUrl={pdfUrl}>
          <PdfObjectOverlay objects={pdfObjects} selectedTypes={selectedTypes} />
        </PdfViewer.Canvas>
        <PdfViewer.InfoPanel
          position="top-right"
          filename={`${pdfFileId}.pdf`}
        />
        <PdfViewer.Controls position="bottom-center" />
      </PdfViewer>
    </div>
  );
}
