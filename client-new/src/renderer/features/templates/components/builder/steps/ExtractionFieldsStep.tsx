/**
 * ExtractionFieldsStep
 * Step 2: Define extraction fields by drawing boxes on the PDF
 */

import { useState } from 'react';
import { ExtractionField } from '../../../types';
import { PdfViewer } from '../../../../shared/components/pdf';

interface ExtractionFieldsStepProps {
  pdfFileId: number;
  extractionFields: ExtractionField[];
  pdfObjects: any;
  pdfUrl: string;
  onExtractionFieldsChange: (fields: ExtractionField[]) => void;
}

export function ExtractionFieldsStep({
  pdfFileId,
  extractionFields,
  pdfObjects,
  pdfUrl,
  onExtractionFieldsChange,
}: ExtractionFieldsStepProps) {
  return (
    <div className="h-full flex">
      {/* Sidebar - Field Management */}
      <div className="w-80 flex-shrink-0 bg-gray-900 border-r border-gray-700 p-4 overflow-y-auto">
        <h3 className="text-sm font-semibold text-white mb-3">Extraction Fields</h3>
        <p className="text-xs text-gray-400 mb-4">
          Draw boxes on the PDF to define fields you want to extract
        </p>

        {/* TODO: Field list and form */}
        <div className="text-sm text-gray-500">
          {extractionFields.length === 0 ? (
            <p>No fields defined yet. Draw a box on the PDF to start.</p>
          ) : (
            <p>{extractionFields.length} field(s) defined</p>
          )}
        </div>
      </div>

      {/* PDF Viewer */}
      <div className="flex-1 overflow-hidden bg-gray-800">
        <PdfViewer pdfUrl={pdfUrl}>
          <PdfViewer.Canvas pdfUrl={pdfUrl}>
            {/* TODO: Add field overlays and drawing capability */}
          </PdfViewer.Canvas>
          <PdfViewer.InfoPanel
            position="top-right"
            filename={`${pdfFileId}.pdf`}
          />
          <PdfViewer.Controls position="bottom-center" />
        </PdfViewer>
      </div>
    </div>
  );
}
