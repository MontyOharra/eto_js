import { ExtractionField } from '../../../types';

interface ExtractionFieldsStepProps {
  pdfFileId: number;
  extractionFields: ExtractionField[];
  onExtractionFieldsChange: (fields: ExtractionField[]) => void;
}

export function ExtractionFieldsStep({
  pdfFileId,
  extractionFields,
  onExtractionFieldsChange,
}: ExtractionFieldsStepProps) {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center">
        <h3 className="text-2xl font-bold text-white mb-2">
          Step 2: Extraction Fields
        </h3>
        <p className="text-gray-400 mb-4">
          PDF File ID: {pdfFileId}
        </p>
        <p className="text-sm text-gray-500">
          This is where users will draw boxes on the PDF to define data extraction fields
        </p>
      </div>
    </div>
  );
}
