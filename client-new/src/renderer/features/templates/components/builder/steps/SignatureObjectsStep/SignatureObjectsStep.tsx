/**
 * SignatureObjectsStep
 * Step 1: Select PDF objects that uniquely identify this template type
 * Container/orchestrator for object selection UI
 */

import { useState, useEffect } from 'react';
import { SignatureObject } from '../../../../types';
import { useMockPdfApi } from '../../../../../pdf-files/mocks/useMockPdfApi';
import { ObjectTypesSidebar } from './ObjectTypesSidebar';
import { PdfViewerSection } from './PdfViewerSection';

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
  onTemplateNameChange,
  onTemplateDescriptionChange,
}: SignatureObjectsStepProps) {
  const [pdfObjects, setPdfObjects] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [pdfUrl, setPdfUrl] = useState<string>('');

  // Load PDF objects on mount
  useEffect(() => {
    loadPdfObjects();
  }, [pdfFileId]);

  const loadPdfObjects = async () => {
    setLoading(true);
    setError(null);

    try {
      const objectsData = await useMockPdfApi.getPdfObjects(pdfFileId);
      setPdfObjects(objectsData);

      const url = useMockPdfApi.getPdfDownloadUrl(pdfFileId);
      setPdfUrl(url);
    } catch (err) {
      console.error('Failed to load PDF objects:', err);
      setError(err instanceof Error ? err.message : 'Failed to load PDF objects');
    } finally {
      setLoading(false);
    }
  };

  const handleTypeToggle = (type: string) => {
    const newSelected = new Set(selectedTypes);
    if (newSelected.has(type)) {
      newSelected.delete(type);
    } else {
      newSelected.add(type);
    }
    setSelectedTypes(newSelected);
  };

  const handleShowAll = () => {
    if (!pdfObjects) return;
    // Get all types that have objects
    const allTypes = Object.keys(getTypeCounts()).filter(
      (type) => getTypeCounts()[type] > 0
    );
    setSelectedTypes(new Set(allTypes));
  };

  const handleHideAll = () => {
    setSelectedTypes(new Set());
  };

  // Get counts for each type
  const getTypeCounts = (): Record<string, number> => {
    if (!pdfObjects) return {};

    return {
      text_word: pdfObjects.objects.text_words?.length || 0,
      text_line: pdfObjects.objects.text_lines?.length || 0,
      graphic_rect: pdfObjects.objects.graphic_rects?.length || 0,
      graphic_line: pdfObjects.objects.graphic_lines?.length || 0,
      graphic_curve: pdfObjects.objects.graphic_curves?.length || 0,
      image: pdfObjects.objects.images?.length || 0,
      table: pdfObjects.objects.tables?.length || 0,
    };
  };

  // Loading state
  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-white">Loading PDF objects...</div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-400 mb-4">{error}</div>
          <button
            onClick={loadPdfObjects}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Main UI
  return (
    <div className="h-full flex">
      <ObjectTypesSidebar
        templateName={templateName}
        templateDescription={templateDescription}
        onTemplateNameChange={onTemplateNameChange}
        onTemplateDescriptionChange={onTemplateDescriptionChange}
        typeCounts={getTypeCounts()}
        selectedTypes={selectedTypes}
        onTypeToggle={handleTypeToggle}
        onShowAll={handleShowAll}
        onHideAll={handleHideAll}
      />
      <PdfViewerSection pdfUrl={pdfUrl} pdfFileId={pdfFileId} />
    </div>
  );
}
