/**
 * SignatureObjectsStep
 * Step 1: Select PDF objects that uniquely identify this template type
 * Container/orchestrator for object selection UI
 */

import { useState, useEffect } from 'react';
import { SignatureObject } from '../../../../types';
import { ObjectTypesSidebar } from './ObjectTypesSidebar';
import { PdfViewerSection } from './PdfViewerSection';

interface SignatureObjectsStepProps {
  pdfFileId: number;
  templateName: string;
  templateDescription: string;
  signatureObjects: SignatureObject[];
  selectedObjectTypes?: string[]; // Persisted visible types
  pdfObjects: any; // PDF objects data (loaded by parent)
  pdfUrl: string; // PDF URL (loaded by parent)
  onTemplateNameChange: (name: string) => void;
  onTemplateDescriptionChange: (description: string) => void;
  onSignatureObjectsChange: (objects: SignatureObject[]) => void;
  onSelectedTypesChange?: (types: string[]) => void; // Save visible types
  pdfScale: number; // Persisted PDF zoom level
  pdfCurrentPage: number; // Persisted PDF page number
  onPdfScaleChange: (scale: number) => void;
  onPdfCurrentPageChange: (page: number) => void;
}

export function SignatureObjectsStep({
  pdfFileId,
  templateName,
  templateDescription,
  onTemplateNameChange,
  onTemplateDescriptionChange,
  signatureObjects,
  onSignatureObjectsChange,
  selectedObjectTypes = [],
  onSelectedTypesChange,
  pdfObjects,
  pdfUrl,
  pdfScale,
  pdfCurrentPage,
  onPdfScaleChange,
  onPdfCurrentPageChange,
}: SignatureObjectsStepProps) {
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(
    new Set(selectedObjectTypes)
  );
  const [selectedObjectIds, setSelectedObjectIds] = useState<Set<string>>(new Set());

  // Sync selectedObjectIds from signatureObjects when they change (e.g., navigating back to this step)
  useEffect(() => {
    if (!pdfObjects || signatureObjects.length === 0) {
      setSelectedObjectIds(new Set());
      return;
    }

    const flatObjects = getFlattenedObjects();
    const idsToSelect = new Set<string>();

    // Find IDs that match the signatureObjects
    signatureObjects.forEach((sigObj) => {
      flatObjects.forEach((obj, idx) => {
        if (
          obj.type === sigObj.type &&
          obj.page === sigObj.page &&
          obj.bbox[0] === sigObj.bbox[0] &&
          obj.bbox[1] === sigObj.bbox[1] &&
          obj.bbox[2] === sigObj.bbox[2] &&
          obj.bbox[3] === sigObj.bbox[3]
        ) {
          const id = `${obj.type}-${obj.page}-${obj.bbox.join('-')}-${idx}`;
          idsToSelect.add(id);
        }
      });
    });

    setSelectedObjectIds(idsToSelect);
  }, [signatureObjects, pdfObjects]);

  const handleTypeToggle = (type: string) => {
    const newSelected = new Set(selectedTypes);
    if (newSelected.has(type)) {
      newSelected.delete(type);
    } else {
      newSelected.add(type);
    }
    setSelectedTypes(newSelected);
    onSelectedTypesChange?.(Array.from(newSelected));
  };

  const handleShowAll = () => {
    if (!pdfObjects) return;
    // Get all types that have objects
    const allTypes = Object.keys(getTypeCounts()).filter(
      (type) => getTypeCounts()[type] > 0
    );
    const newSelected = new Set(allTypes);
    setSelectedTypes(newSelected);
    onSelectedTypesChange?.(Array.from(newSelected));
  };

  const handleHideAll = () => {
    setSelectedTypes(new Set());
    onSelectedTypesChange?.([]);
  };

  const handleObjectClick = (objectId: string) => {
    setSelectedObjectIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(objectId)) {
        newSet.delete(objectId);
      } else {
        newSet.add(objectId);
      }

      // Convert selected IDs to SignatureObject format
      const flatObjects = getFlattenedObjects();
      const selectedSignatureObjects = flatObjects
        .map((obj, idx) => {
          const id = `${obj.type}-${obj.page}-${obj.bbox.join('-')}-${idx}`;
          if (newSet.has(id)) {
            return {
              type: obj.type,
              page: obj.page,
              bbox: obj.bbox,
              text: obj.text,
            };
          }
          return null;
        })
        .filter((obj): obj is SignatureObject => obj !== null);

      onSignatureObjectsChange(selectedSignatureObjects);

      return newSet;
    });
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

  // Flatten PDF objects for overlay rendering
  const getFlattenedObjects = () => {
    if (!pdfObjects) return [];

    const flatObjects: Array<{
      type: string;
      page: number;
      bbox: [number, number, number, number];
      text?: string;
    }> = [];

    // Helper to add objects with their type
    const addObjects = (objects: any[] | undefined, type: string) => {
      if (!objects) return;
      objects.forEach((obj) => {
        flatObjects.push({
          type,
          page: obj.page || 1,
          bbox: obj.bbox,
          text: obj.text,
        });
      });
    };

    // Add all object types
    addObjects(pdfObjects.objects.text_words, 'text_word');
    addObjects(pdfObjects.objects.text_lines, 'text_line');
    addObjects(pdfObjects.objects.graphic_rects, 'graphic_rect');
    addObjects(pdfObjects.objects.graphic_lines, 'graphic_line');
    addObjects(pdfObjects.objects.graphic_curves, 'graphic_curve');
    addObjects(pdfObjects.objects.images, 'image');
    addObjects(pdfObjects.objects.tables, 'table');

    return flatObjects;
  };

  // Main UI
  return (
    <div className="h-full w-full flex">
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
      <PdfViewerSection
        pdfUrl={pdfUrl}
        pdfFileId={pdfFileId}
        pdfObjects={getFlattenedObjects()}
        selectedTypes={selectedTypes}
        selectedObjects={selectedObjectIds}
        onObjectClick={handleObjectClick}
        pdfScale={pdfScale}
        pdfCurrentPage={pdfCurrentPage}
        onPdfScaleChange={onPdfScaleChange}
        onPdfCurrentPageChange={onPdfCurrentPageChange}
      />
    </div>
  );
}
