/**
 * SignatureObjectsStep
 * Step 1: Select PDF objects that uniquely identify this template type
 * Supports two modes:
 * - Create mode: Processes local PDF file without storing
 * - Edit mode: Fetches PDF from existing ID
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { ObjectTypesSidebar } from './ObjectTypesSidebar';
import { PdfViewerSection } from './PdfViewerSection';
import type { PdfObjects } from '../../types';

interface SignatureObjectsStepProps {
  pdfUrl: string;                // PDF URL (either blob URL or backend URL)
  pdfObjects: PdfObjects;        // PDF objects (fetched by parent)
  templateName: string;
  templateDescription: string;
  selectedSignatureObjects: PdfObjects;
  onTemplateNameChange: (name: string) => void;
  onTemplateDescriptionChange: (description: string) => void;
  onSignatureObjectsChange: (objects: PdfObjects) => void;
}

export function SignatureObjectsStep({
  pdfUrl,
  pdfObjects,
  templateName,
  templateDescription,
  selectedSignatureObjects,
  onTemplateNameChange,
  onTemplateDescriptionChange,
  onSignatureObjectsChange,
}: SignatureObjectsStepProps) {

  // Local state for UI
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [selectedObjectIds, setSelectedObjectIds] = useState<Set<string>>(new Set());


  // Flatten PDF objects for overlay rendering
  const getFlattenedObjects = useCallback((): Array<any> => {
    const flatObjects: Array<any> = [];

    // Helper to add objects with their type (preserving all original fields)
    const addObjects = (objects: any[] | undefined, type: string) => {
      if (!objects) return;
      objects.forEach((obj) => {
        flatObjects.push({
          ...obj, // Preserve all original fields
          type,
          page: obj.page || 1,
        });
      });
    };

    // Add all object types
    addObjects(pdfObjects.text_words, 'text_word');
    addObjects(pdfObjects.graphic_rects, 'graphic_rect');
    addObjects(pdfObjects.graphic_lines, 'graphic_line');
    addObjects(pdfObjects.graphic_curves, 'graphic_curve');
    addObjects(pdfObjects.images, 'image');
    addObjects(pdfObjects.tables, 'table');

    return flatObjects;
  }, [pdfObjects]);

  // Initialize selectedObjectIds from selectedSignatureObjects when component mounts
  useEffect(() => {

    // Count total signature objects
    const totalSignatureObjects = Object.values(selectedSignatureObjects).reduce(
      (sum, arr) => sum + arr.length,
      0
    );

    if (totalSignatureObjects === 0) {
      setSelectedObjectIds(new Set());
      return;
    }

    const flatObjects = getFlattenedObjects();
    const idsToSelect = new Set<string>();

    // Flatten signature objects to match against
    const flatSignatureObjects: any[] = [
      ...selectedSignatureObjects.text_words,
      ...selectedSignatureObjects.graphic_rects,
      ...selectedSignatureObjects.graphic_lines,
      ...selectedSignatureObjects.graphic_curves,
      ...selectedSignatureObjects.images,
      ...selectedSignatureObjects.tables,
    ];

    // Find IDs that match the selectedSignatureObjects
    flatSignatureObjects.forEach((sigObj) => {
      flatObjects.forEach((obj, idx) => {
        if (
          obj.type === getTypeFromObject(sigObj) &&
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
  }, [pdfObjects, selectedSignatureObjects, getFlattenedObjects]);

  // Helper: Determine type from object (check which array it came from)
  const getTypeFromObject = (obj: any): string => {
    if ('text' in obj && 'fontname' in obj && 'fontsize' in obj) {
      return 'text_word';
    }
    if ('linewidth' in obj && 'points' in obj) return 'graphic_curve';
    // Check for both vertical lines (width < 2) and horizontal lines (height < 2)
    if ('linewidth' in obj && (obj.bbox[2] - obj.bbox[0] < 2 || obj.bbox[3] - obj.bbox[1] < 2)) {
      return 'graphic_line';
    }
    if ('linewidth' in obj) return 'graphic_rect';
    if ('format' in obj) return 'image';
    if ('rows' in obj && 'cols' in obj) return 'table';
    return 'text_word'; // fallback
  };

  // Get counts for each type
  const typeCounts = useMemo((): Record<string, number> => {
    return {
      text_word: pdfObjects.text_words?.length || 0,
      graphic_rect: pdfObjects.graphic_rects?.length || 0,
      graphic_line: pdfObjects.graphic_lines?.length || 0,
      graphic_curve: pdfObjects.graphic_curves?.length || 0,
      image: pdfObjects.images?.length || 0,
      table: pdfObjects.tables?.length || 0,
    };
  }, [pdfObjects]);

  // Get selected counts for each type
  const selectedTypeCounts = useMemo((): Record<string, number> => {
    return {
      text_word: selectedSignatureObjects.text_words?.length || 0,
      graphic_rect: selectedSignatureObjects.graphic_rects?.length || 0,
      graphic_line: selectedSignatureObjects.graphic_lines?.length || 0,
      graphic_curve: selectedSignatureObjects.graphic_curves?.length || 0,
      image: selectedSignatureObjects.images?.length || 0,
      table: selectedSignatureObjects.tables?.length || 0,
    };
  }, [selectedSignatureObjects]);

  // Group objects by type with IDs for accordion display
  const objectsByType = useMemo(() => {
    const flatObjects = getFlattenedObjects();
    const grouped: Record<string, any[]> = {
      text_word: [],
      graphic_rect: [],
      graphic_line: [],
      graphic_curve: [],
      image: [],
      table: [],
    };

    flatObjects.forEach((obj, idx) => {
      const id = `${obj.type}-${obj.page}-${obj.bbox.join('-')}-${idx}`;
      const objectWithId = { ...obj, id };

      if (grouped[obj.type]) {
        grouped[obj.type].push(objectWithId);
      }
    });

    return grouped;
  }, [getFlattenedObjects]);

  // Handlers
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
    // Get all types that have objects
    const allTypes = Object.keys(typeCounts).filter(
      (type) => typeCounts[type] > 0
    );
    setSelectedTypes(new Set(allTypes));
  };

  const handleHideAll = () => {
    setSelectedTypes(new Set());
  };

  const handleObjectClick = (objectId: string) => {
    setSelectedObjectIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(objectId)) {
        newSet.delete(objectId);
      } else {
        newSet.add(objectId);
      }

      // Convert selected IDs to PdfObjects format (grouped by type)
      const flatObjects = getFlattenedObjects();
      const pdfObjectsFormat: PdfObjects = {
        text_words: [],
        graphic_rects: [],
        graphic_lines: [],
        graphic_curves: [],
        images: [],
        tables: [],
      };

      // Group selected objects by type (preserving all fields)
      flatObjects.forEach((obj, idx) => {
        const id = `${obj.type}-${obj.page}-${obj.bbox.join('-')}-${idx}`;
        if (newSet.has(id)) {
          // Remove 'type' field before storing (it's not in the PdfObjects schema)
          const { type, ...objWithoutType } = obj;

          // Map type names to PdfObjects field names
          if (type === 'text_word') {
            pdfObjectsFormat.text_words.push(objWithoutType);
          } else if (type === 'graphic_rect') {
            pdfObjectsFormat.graphic_rects.push(objWithoutType);
          } else if (type === 'graphic_line') {
            pdfObjectsFormat.graphic_lines.push(objWithoutType);
          } else if (type === 'graphic_curve') {
            pdfObjectsFormat.graphic_curves.push(objWithoutType);
          } else if (type === 'image') {
            pdfObjectsFormat.images.push(objWithoutType);
          } else if (type === 'table') {
            pdfObjectsFormat.tables.push(objWithoutType);
          }
        }
      });

      onSignatureObjectsChange(pdfObjectsFormat);

      return newSet;
    });
  };

  return (
    <div className="h-full w-full flex">
      <ObjectTypesSidebar
        templateName={templateName}
        templateDescription={templateDescription}
        onTemplateNameChange={onTemplateNameChange}
        onTemplateDescriptionChange={onTemplateDescriptionChange}
        typeCounts={typeCounts}
        selectedTypeCounts={selectedTypeCounts}
        objectsByType={objectsByType}
        selectedObjectIds={selectedObjectIds}
        visibleTypes={selectedTypes}
        onObjectToggle={handleObjectClick}
        onTypeToggle={handleTypeToggle}
        onShowAll={handleShowAll}
        onHideAll={handleHideAll}
      />
      <PdfViewerSection
        pdfUrl={pdfUrl}
        pdfFileId={0}
        pdfObjects={getFlattenedObjects()}
        selectedTypes={selectedTypes}
        selectedObjects={selectedObjectIds}
        onObjectClick={handleObjectClick}
      />
    </div>
  );
}
