/**
 * ExtractionFieldsStep
 * Step 2: Define extraction fields by drawing boxes on the PDF
 */

import { useState, useMemo } from 'react';
import { ExtractionField, SignatureObject } from '../../../types';
import type { PipelineState, VisualState } from '../../../../../types/pipelineTypes';
import { PdfViewer } from '../../../../../shared/components/pdf';
import { PdfObjectOverlay } from './SignatureObjectsStep/PdfObjectOverlay';
import { ExtractionFieldsSidebar, SidebarMode } from './ExtractionFieldsStep/ExtractionFieldsSidebar';
import { ExtractionFieldOverlay } from './ExtractionFieldsStep/ExtractionFieldOverlay';

interface ExtractionFieldsStepProps {
  pdfFileId: number | null;
  pdfFile: File | null;
  templateName: string;
  templateDescription: string;
  extractionFields: ExtractionField[];
  signatureObjects: {
    text_words: any[];
    text_lines: any[];
    graphic_rects: any[];
    graphic_lines: any[];
    graphic_curves: any[];
    images: any[];
    tables: any[];
  };
  pdfObjects: any;
  pdfUrl: string;
  pipelineState: PipelineState;
  visualState: VisualState;
  onTemplateNameChange: (name: string) => void;
  onTemplateDescriptionChange: (description: string) => void;
  onExtractionFieldsChange: (fields: ExtractionField[]) => void;
  pdfScale: number;
  pdfCurrentPage: number;
  onPdfScaleChange: (scale: number) => void;
  onPdfCurrentPageChange: (page: number) => void;
}

export function ExtractionFieldsStep({
  pdfFileId,
  pdfFile,
  templateName,
  templateDescription,
  extractionFields,
  signatureObjects,
  pdfObjects,
  pdfUrl,
  pipelineState,
  visualState,
  onTemplateNameChange,
  onTemplateDescriptionChange,
  onExtractionFieldsChange,
  pdfScale,
  pdfCurrentPage,
  onPdfScaleChange,
  onPdfCurrentPageChange,
}: ExtractionFieldsStepProps) {
  // Count total signature objects
  const signatureObjectsCount = Object.values(signatureObjects).reduce(
    (sum, arr) => sum + arr.length,
    0
  );
  console.log('[ExtractionFieldsStep] Received signature objects:', signatureObjectsCount, signatureObjects);

  // Drawing state
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawingBox, setDrawingBox] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
  const [didDrag, setDidDrag] = useState(false);

  // Staging state
  const [stagedFieldId, setStagedFieldId] = useState<string | null>(null);
  const [tempFieldData, setTempFieldData] = useState<{ bbox: [number, number, number, number]; page: number } | null>(null);

  // Form state for create/edit
  const [fieldName, setFieldName] = useState('');
  const [fieldDescription, setFieldDescription] = useState('');

  // Signature objects visibility
  const [showSignatureObjects, setShowSignatureObjects] = useState(true);

  // Determine sidebar mode
  const sidebarMode: SidebarMode = tempFieldData ? 'create' : stagedFieldId ? 'detail' : 'list';

  // Flatten signature objects for overlay rendering
  const flatSignatureObjects = useMemo(() => {
    return [
      ...signatureObjects.text_words,
      ...signatureObjects.text_lines,
      ...signatureObjects.graphic_rects,
      ...signatureObjects.graphic_lines,
      ...signatureObjects.graphic_curves,
      ...signatureObjects.images,
      ...signatureObjects.tables,
    ];
  }, [signatureObjects]);

  // Get unique object types from signature objects
  const signatureObjectTypes = useMemo(() => {
    const types = new Set<string>();

    flatSignatureObjects.forEach((obj: any) => {
      types.add(obj.type); // Signature objects already have 'type', not 'object_type'
    });

    console.log('[ExtractionFieldsStep] Signature objects count:', flatSignatureObjects.length);
    console.log('[ExtractionFieldsStep] Signature object types:', Array.from(types));
    return types;
  }, [flatSignatureObjects]);

  // Mouse Handlers for Drawing
  const handleMouseDown = (
    e: React.MouseEvent,
    pageElement: HTMLElement,
    currentPage: number,
    scale: number,
    pageHeight: number
  ) => {
    // Only allow drawing when not viewing/editing fields
    if (stagedFieldId || tempFieldData) return;

    e.preventDefault();
    const rect = pageElement.getBoundingClientRect();
    const anchorX = (e.clientX - rect.left) / scale;
    const anchorY = (e.clientY - rect.top) / scale;

    setIsDrawing(true);
    setDidDrag(false); // Reset drag flag
    setDrawingBox({ x: anchorX, y: anchorY, width: 0, height: 0 });
  };

  const handleMouseMove = (
    e: React.MouseEvent,
    pageElement: HTMLElement,
    currentPage: number,
    scale: number,
    pageHeight: number
  ) => {
    if (!isDrawing || !drawingBox) return;

    e.preventDefault();
    setDidDrag(true); // Mark that we're dragging
    const rect = pageElement.getBoundingClientRect();
    const currentX = (e.clientX - rect.left) / scale;
    const currentY = (e.clientY - rect.top) / scale;

    // Keep anchor point fixed, width/height can be positive or negative
    setDrawingBox({
      x: drawingBox.x,
      y: drawingBox.y,
      width: currentX - drawingBox.x,
      height: currentY - drawingBox.y,
    });
  };

  const handleMouseUp = (
    e: React.MouseEvent,
    pageElement: HTMLElement,
    currentPage: number,
    scale: number,
    pageHeight: number
  ) => {
    if (!isDrawing || !drawingBox) return;

    e.preventDefault();

    // Only create field if box has meaningful size (check absolute values)
    if (Math.abs(drawingBox.width) > 3 && Math.abs(drawingBox.height) > 3) {
      // Calculate actual box coordinates handling negative width/height
      const screenX0 = drawingBox.x;
      const screenY0 = drawingBox.y;
      const screenX1 = drawingBox.x + drawingBox.width;
      const screenY1 = drawingBox.y + drawingBox.height;

      // Normalize coordinates so x0,y0 is always top-left
      const normalizedX0 = Math.min(screenX0, screenX1);
      const normalizedY0 = Math.min(screenY0, screenY1);
      const normalizedX1 = Math.max(screenX0, screenX1);
      const normalizedY1 = Math.max(screenY0, screenY1);

      // Store coordinates as-is (no Y-axis flip)
      // Backend text_words use pdfplumber coordinates (y=0 at top)
      // which matches screen coordinates, so no conversion needed
      setTempFieldData({
        bbox: [normalizedX0, normalizedY0, normalizedX1, normalizedY1],
        page: currentPage, // Keep 1-indexed (currentPage is already 1-indexed)
      });

      // Reset form fields
      setFieldName('');
      setFieldDescription('');
    }

    setIsDrawing(false);
    setDrawingBox(null);
  };

  // Field Management Handlers
  const handleSaveField = () => {
    if (!tempFieldData || !fieldName.trim()) return;

    const newField: ExtractionField = {
      name: fieldName,
      description: fieldDescription || null,
      page: tempFieldData.page,
      bbox: tempFieldData.bbox,
    };

    onExtractionFieldsChange([...extractionFields, newField]);

    // Clear temp state
    setTempFieldData(null);
    setFieldName('');
    setFieldDescription('');
  };

  const handleCancelField = () => {
    setTempFieldData(null);
    setFieldName('');
    setFieldDescription('');
  };

  const handleDeleteField = (fieldName: string) => {
    onExtractionFieldsChange(extractionFields.filter(f => f.name !== fieldName));
    setStagedFieldId(null);
  };

  const handleSelectField = (fieldName: string) => {
    setStagedFieldId(fieldName);
  };

  const handleBackToList = () => {
    setStagedFieldId(null);
  };

  const handleFieldClick = (fieldName: string) => {
    // Clicking a field selects it
    setStagedFieldId(fieldName);
  };

  const handleCanvasClick = () => {
    // Only handle clicks, not drag completions
    // If didDrag is true, this click came from a drag operation, so ignore it
    if (didDrag) {
      setDidDrag(false); // Reset for next interaction
      return;
    }

    // If there's a temporary field, cancel it when clicking anywhere on the PDF
    if (tempFieldData) {
      handleCancelField();
    }

    // If there's a staged field, deselect it when clicking anywhere on the PDF
    if (stagedFieldId) {
      setStagedFieldId(null);
    }
  };

  const handleUpdateField = (fieldName: string, updates: Partial<ExtractionField>) => {
    const updatedFields = extractionFields.map(field =>
      field.name === fieldName ? { ...field, ...updates } : field
    );
    onExtractionFieldsChange(updatedFields);
  };

  return (
    <div className="h-full w-full flex">
      {/* Sidebar - Field Management */}
      <div className="w-80 flex-shrink-0 bg-gray-900 border-r border-gray-700 p-4 overflow-y-auto">
        <ExtractionFieldsSidebar
          pdfFileId={pdfFileId}
          pdfFile={pdfFile}
          templateName={templateName}
          templateDescription={templateDescription}
          extractionFields={extractionFields}
          signatureObjects={signatureObjects}
          pipelineState={pipelineState}
          visualState={visualState}
          mode={sidebarMode}
          selectedFieldId={stagedFieldId}
          showSignatureObjects={showSignatureObjects}
          fieldName={fieldName}
          fieldDescription={fieldDescription}
          tempFieldData={tempFieldData}
          onTemplateNameChange={onTemplateNameChange}
          onTemplateDescriptionChange={onTemplateDescriptionChange}
          onShowSignatureObjectsChange={setShowSignatureObjects}
          onFieldNameChange={setFieldName}
          onFieldDescriptionChange={setFieldDescription}
          onSaveField={handleSaveField}
          onCancelField={handleCancelField}
          onDeleteField={handleDeleteField}
          onSelectField={handleSelectField}
          onBackToList={handleBackToList}
          onUpdateField={handleUpdateField}
        />
      </div>

      {/* PDF Viewer */}
      <div className="flex-1 overflow-hidden bg-gray-800">
        <PdfViewer
          pdfUrl={pdfUrl}
          initialScale={pdfScale}
          initialPage={pdfCurrentPage}
          onScaleChange={onPdfScaleChange}
          onPageChange={onPdfCurrentPageChange}
        >
          <PdfViewer.Canvas
            pdfUrl={pdfUrl}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onClick={handleCanvasClick}
          >
            {/* Show signature objects in original colors when checkbox is checked */}
            {showSignatureObjects && (
              <PdfObjectOverlay
                objects={flatSignatureObjects}
                selectedTypes={signatureObjectTypes} // Show all selected types
                selectedObjects={new Set()} // No selected objects (show in original colors)
                onObjectClick={() => {}} // Non-interactive
              />
            )}

            {/* Show extraction field overlays */}
            <ExtractionFieldOverlay
              fields={extractionFields}
              stagedFieldId={stagedFieldId}
              tempFieldData={tempFieldData}
              drawingBox={drawingBox}
              onFieldClick={handleFieldClick}
            />
          </PdfViewer.Canvas>
          <PdfViewer.ControlsSidebar position="right" />
        </PdfViewer>
      </div>
    </div>
  );
}
