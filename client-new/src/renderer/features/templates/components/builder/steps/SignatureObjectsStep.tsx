import { SignatureObject } from '../../../types';

interface SignatureObjectsStepProps {
  pdfFileId: number;
  templateName: string;
  templateDescription: string;
  signatureObjects: SignatureObject[];
  onTemplateNameChange: (name: string) => void;
  onTemplateDescriptionChange: (description: string) => void;
  onSignatureObjectsChange: (objects: SignatureObject[]) => void;
}

export function SignatureObjectsStep({
  pdfFileId,
  templateName,
  templateDescription,
  signatureObjects,
  onTemplateNameChange,
  onTemplateDescriptionChange,
  onSignatureObjectsChange,
}: SignatureObjectsStepProps) {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center">
        <h3 className="text-2xl font-bold text-white mb-2">
          Step 1: Signature Objects
        </h3>
        <p className="text-gray-400 mb-4">
          PDF File ID: {pdfFileId}
        </p>
        <p className="text-sm text-gray-500">
          This is where users will select PDF objects that uniquely identify this template type
        </p>
      </div>
    </div>
  );
}
