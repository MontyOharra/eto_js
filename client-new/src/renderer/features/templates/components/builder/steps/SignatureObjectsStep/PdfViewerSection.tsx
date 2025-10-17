/**
 * PdfViewerSection
 * PDF viewer with object overlays on the right side
 */

import { PdfViewer } from '../../../../../../shared/components/pdf';

interface PdfViewerSectionProps {
  pdfUrl: string;
  pdfFileId: number;
  // pdfObjects: PdfObjectsByType; // TODO: For overlays
  // selectedTypes: Set<string>; // TODO: For filtering overlays
  // selectedObjects?: Set<string>; // TODO: For click selection
  // onObjectClick?: (obj: any) => void; // TODO: For click handling
}

export function PdfViewerSection({
  pdfUrl,
  pdfFileId,
}: PdfViewerSectionProps) {
  return (
    <div className="flex-1 overflow-hidden bg-gray-800">
      <PdfViewer pdfUrl={pdfUrl}>
        <PdfViewer.Canvas pdfUrl={pdfUrl}>
          {/* TODO: Add object overlays here based on selectedTypes */}
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
