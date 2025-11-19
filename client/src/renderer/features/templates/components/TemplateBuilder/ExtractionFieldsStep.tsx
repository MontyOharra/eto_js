/**
 * ExtractionFieldsStep
 * Step 2: Define extraction fields by drawing boxes on the PDF
 */

import { useState, useMemo, useEffect, useCallback } from 'react';
import type { ExtractionField, PdfObjects } from '../../types';
import type { PipelineState, VisualState, EntryPoint } from '../../../pipelines/types';
import { PdfViewer } from '../../../pdf';
import { PdfObjectOverlay } from './PdfObjectOverlay';
import { ExtractionFieldsSidebar, SidebarMode } from './ExtractionFieldsSidebar';
import { ExtractionFieldOverlay } from './ExtractionFieldOverlay';
import { generateEntryPointId } from '../../../pipelines/utils/idGenerator';
import { createEntryPoint } from '../../../pipelines/utils/moduleFactory';

interface ExtractionFieldsStepProps {
  pdfUrl: string;                     // PDF URL (either blob URL or backend URL)
  templateName: string;
  templateDescription: string;
  extractionFields: ExtractionField[];
  selectedSignatureObjects: PdfObjects;
  selectedPages?: number[];           // Optional 0-indexed page numbers to display
  pipelineState: PipelineState;
  visualState: VisualState;
  onTemplateNameChange: (name: string) => void;
  onTemplateDescriptionChange: (description: string) => void;
  onExtractionFieldsChange: (fields: ExtractionField[]) => void;
  onPipelineStateChange: (state: PipelineState) => void;
  onVisualStateChange: (state: VisualState) => void;
}

// Helper: Convert extraction field to entry point
// Uses the standard createEntryPoint factory to ensure consistency with PipelineBuilderModal
function extractionFieldToEntryPoint(field: ExtractionField): EntryPoint {
  const entryPointId = generateEntryPointId(); // E{xx} format
  return createEntryPoint(entryPointId, field.name);
}

export function ExtractionFieldsStep({
  pdfUrl,
  templateName,
  templateDescription,
  extractionFields,
  selectedSignatureObjects,
  selectedPages,
  pipelineState,
  visualState,
  onTemplateNameChange,
  onTemplateDescriptionChange,
  onExtractionFieldsChange,
  onPipelineStateChange,
  onVisualStateChange,
}: ExtractionFieldsStepProps) {

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
  const [fieldNameError, setFieldNameError] = useState<string | null>(null);

  // Signature objects visibility
  const [showSignatureObjects, setShowSignatureObjects] = useState(true);

  // Determine sidebar mode
  const sidebarMode: SidebarMode = tempFieldData ? 'create' : stagedFieldId ? 'detail' : 'list';

  // Flatten signature objects for overlay rendering
  const flatSignatureObjects = useMemo(() => {
    const flat: any[] = [];

    selectedSignatureObjects.text_words.forEach(obj => flat.push({ ...obj, type: 'text_word' }));
    selectedSignatureObjects.graphic_rects.forEach(obj => flat.push({ ...obj, type: 'graphic_rect' }));
    selectedSignatureObjects.graphic_lines.forEach(obj => flat.push({ ...obj, type: 'graphic_line' }));
    selectedSignatureObjects.graphic_curves.forEach(obj => flat.push({ ...obj, type: 'graphic_curve' }));
    selectedSignatureObjects.images.forEach(obj => flat.push({ ...obj, type: 'image' }));
    selectedSignatureObjects.tables.forEach(obj => flat.push({ ...obj, type: 'table' }));

    return flat;
  }, [selectedSignatureObjects]);

  // Get unique object types from signature objects
  const signatureObjectTypes = useMemo(() => {
    const types = new Set<string>();
    flatSignatureObjects.forEach((obj: any) => {
      types.add(obj.type);
    });
    return types;
  }, [flatSignatureObjects]);

  // Delete field handler (defined early so it can be used in keyboard handler)
  const handleDeleteField = useCallback((fieldName: string) => {
    console.log('[ExtractionFieldsStep] Deleting field:', fieldName);

    // Remove from extraction fields
    const updatedFields = extractionFields.filter(f => f.name !== fieldName);
    onExtractionFieldsChange(updatedFields);

    // Remove from pipeline state entry points (match by name)
    const updatedEntryPoints = pipelineState.entry_points.filter(ep => ep.name !== fieldName);

    // Clean up orphaned connections from removed entry point
    // Entry point output node_ids have format: E{xx}_out
    const entryPointOutputIds = new Set(
      updatedEntryPoints.flatMap(ep => ep.outputs.map(output => output.node_id))
    );
    const cleanedConnections = pipelineState.connections.filter(
      conn => !conn.from_node_id.endsWith('_out') || entryPointOutputIds.has(conn.from_node_id)
    );

    // Clean up orphaned visual state entries for the removed entry point
    const entryPointIds = new Set(updatedEntryPoints.map(ep => ep.entry_point_id));
    const cleanedVisualState = Object.fromEntries(
      Object.entries(visualState).filter(
        ([nodeId]) => !nodeId.startsWith('E') || entryPointIds.has(nodeId)
      )
    );

    console.log('[ExtractionFieldsStep] Updating pipeline state:', {
      oldEntryPoints: pipelineState.entry_points.map(ep => ep.name),
      newEntryPoints: updatedEntryPoints.map(ep => ep.name),
      removedName: fieldName,
      cleanedConnections: cleanedConnections.length,
      cleanedVisualState: Object.keys(cleanedVisualState).length,
    });

    // Update both pipeline state and visual state
    onPipelineStateChange({
      ...pipelineState,
      entry_points: updatedEntryPoints,
      connections: cleanedConnections,
    });

    // Update visual state if entries were removed
    if (Object.keys(cleanedVisualState).length !== Object.keys(visualState).length) {
      onVisualStateChange(cleanedVisualState);
    }

    setStagedFieldId(null);
  }, [extractionFields, pipelineState, visualState, onExtractionFieldsChange, onPipelineStateChange, onVisualStateChange]);

  // Keyboard handler for Delete key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle Delete key when a field is selected and not in create mode
      if (e.key === 'Delete' && stagedFieldId && !tempFieldData) {
        // Don't delete if user is typing in an input or textarea
        const target = e.target as HTMLElement;
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
          return;
        }

        // Delete the selected field (this also removes from pipeline state entry points)
        handleDeleteField(stagedFieldId);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [stagedFieldId, tempFieldData, handleDeleteField]);

  // Mouse Handlers for Drawing
  const handleMouseDown = (
    e: React.MouseEvent,
    pageElement: HTMLElement,
    currentPage: number,
    scale: number
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
    scale: number
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
    currentPage: number
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

    // Check for duplicate field names
    const isDuplicate = extractionFields.some(field => field.name === fieldName.trim());
    if (isDuplicate) {
      setFieldNameError(`A field named "${fieldName.trim()}" already exists. Please choose a different name.`);
      return;
    }

    const newField: ExtractionField = {
      name: fieldName.trim(),
      description: fieldDescription || null,
      page: tempFieldData.page,
      bbox: tempFieldData.bbox,
    };

    // Update extraction fields
    const updatedFields = [...extractionFields, newField];
    onExtractionFieldsChange(updatedFields);

    // Also update pipeline state entry points
    const newEntryPoint = extractionFieldToEntryPoint(newField);
    const updatedPipelineState = {
      ...pipelineState,
      entry_points: [...pipelineState.entry_points, newEntryPoint],
    };
    console.log('[ExtractionFieldsStep] Adding entry point:', {
      newEntryPoint,
      totalEntryPoints: updatedPipelineState.entry_points.length,
      entryPoints: updatedPipelineState.entry_points,
    });
    onPipelineStateChange(updatedPipelineState);

    // Clear temp state
    setTempFieldData(null);
    setFieldName('');
    setFieldDescription('');
    setFieldNameError(null);
  };

  const handleCancelField = () => {
    setTempFieldData(null);
    setFieldName('');
    setFieldDescription('');
    setFieldNameError(null);
  };

  const handleFieldNameChange = (name: string) => {
    setFieldName(name);
    // Clear error as user types
    if (fieldNameError) {
      setFieldNameError(null);
    }
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
    // If updating the name, check for duplicates
    if (updates.name && updates.name !== fieldName) {
      const isDuplicate = extractionFields.some(
        field => field.name !== fieldName && field.name === updates.name.trim()
      );
      if (isDuplicate) {
        // Validation error will be handled by the sidebar component
        console.error(`Cannot rename to "${updates.name}": name already exists`);
        return;
      }
    }

    // Update extraction fields
    const updatedFields = extractionFields.map(field =>
      field.name === fieldName ? { ...field, ...updates } : field
    );
    onExtractionFieldsChange(updatedFields);

    // If name changed, also update entry point
    if (updates.name) {
      onPipelineStateChange({
        ...pipelineState,
        entry_points: pipelineState.entry_points.map(ep =>
          ep.name === fieldName
            ? { ...ep, name: updates.name }
            : ep
        ),
      });
    }
  };

  return (
    <div className="h-full w-full flex">
      {/* Sidebar - Field Management */}
      <ExtractionFieldsSidebar
        templateName={templateName}
        templateDescription={templateDescription}
        extractionFields={extractionFields}
        mode={sidebarMode}
        selectedFieldId={stagedFieldId}
        showSignatureObjects={showSignatureObjects}
        fieldName={fieldName}
        fieldDescription={fieldDescription}
        fieldNameError={fieldNameError}
        tempFieldData={tempFieldData}
        onTemplateNameChange={onTemplateNameChange}
        onTemplateDescriptionChange={onTemplateDescriptionChange}
        onShowSignatureObjectsChange={setShowSignatureObjects}
        onFieldNameChange={handleFieldNameChange}
        onFieldDescriptionChange={setFieldDescription}
        onSaveField={handleSaveField}
        onCancelField={handleCancelField}
        onDeleteField={handleDeleteField}
        onSelectField={handleSelectField}
        onBackToList={handleBackToList}
        onUpdateField={handleUpdateField}
      />

      {/* PDF Viewer */}
      <div className="flex-1 overflow-hidden bg-gray-800">
        <PdfViewer pdfUrl={pdfUrl} selectedPages={selectedPages}>
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
