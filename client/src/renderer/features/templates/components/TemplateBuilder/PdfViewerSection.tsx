/**
 * PdfViewerSection
 * PDF viewer with object overlays on the right side
 */

import { PdfViewer } from '../../../pdf';
import { PdfObjectOverlay } from './PdfObjectOverlay';

interface PdfObject {
  type: string;
  page: number;
  bbox: [number, number, number, number];
  text?: string;
}

interface PdfViewerSectionProps {
  pdfUrl: string;
  pdfObjects: PdfObject[];
  selectedTypes: Set<string>;
  selectedObjects: Set<string>;
  onObjectClick: (objectId: string) => void;
  onBoxSelect?: (objectIds: string[]) => void; // Called when shift+drag selects multiple objects
  selectedPages?: number[]; // 0-indexed page numbers to display
}

export function PdfViewerSection({
  pdfUrl,
  pdfObjects,
  selectedTypes,
  selectedObjects,
  onObjectClick,
  onBoxSelect,
  selectedPages,
}: PdfViewerSectionProps) {
  return (
    <div className="flex-1 overflow-hidden bg-gray-800">
      <PdfViewer pdfUrl={pdfUrl} selectedPages={selectedPages}>
        <PdfViewer.Canvas pdfUrl={pdfUrl}>
          <PdfObjectOverlay
            objects={pdfObjects}
            selectedTypes={selectedTypes}
            selectedObjects={selectedObjects}
            onObjectClick={onObjectClick}
            onBoxSelect={onBoxSelect}
          />
        </PdfViewer.Canvas>
        <PdfViewer.ControlsSidebar position="right" />
      </PdfViewer>
    </div>
  );
}
