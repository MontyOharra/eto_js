import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { PdfViewer } from '../pdf/PdfViewer';
import { apiClient } from '../../services/api';
import { EtoDataTransforms } from '../../types/eto';

interface TemplateBuilderModalProps {
  runId: string | null;
  onClose: () => void;
  onSave: (templateData: any) => void;
}

interface EtoRunPdfData {
  eto_run_id: number;
  pdf_id: number;
  filename: string;
  page_count: number;
  object_count: number;
  file_size: number;
  pdf_objects: any[];  // PDF objects from pdf_files table (new workflow)
  status: "not_started" | "processing" | "success" | "failure" | "needs_template";
  processing_step?: "template_matching" | "extracting_data" | "transforming_data";
  matched_template_id?: number;
  extracted_data?: any;  // Structured extracted field data
  transformation_audit?: any;  // Transformation audit trail
  target_data?: any;  // Final transformed data
  email: {
    subject: string;
    sender_email: string;
    received_date: string;
  };
  timestamps: {
    created_at?: string;
    started_at?: string;
    completed_at?: string;
  };
  error_info: {
    error_type?: string;
    error_message?: string;
  };
}

const OBJECT_TYPE_NAMES = {
  word: 'Words',
  text_line: 'Text Lines',
  rect: 'Rectangles', 
  graphic_line: 'Lines',
  curve: 'Curves',
  image: 'Images',
  table: 'Tables'
};

const OBJECT_TYPE_COLORS = {
  word: '#ff0000',
  text_line: '#00ff00',
  rect: '#0000ff',
  graphic_line: '#ffff00',
  curve: '#ff00ff',
  image: '#00ffff',
  table: '#ffa500'
};

type TemplateBuilderStep = 'object-selection' | 'field-labels';

export function TemplateBuilderModal({ runId, onClose, onSave }: TemplateBuilderModalProps) {
  const [pdfData, setPdfData] = useState<EtoRunPdfData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<TemplateBuilderStep>('object-selection');
  const [selectedObjectTypes, setSelectedObjectTypes] = useState<Set<string>>(new Set());
  const [selectedObjects, setSelectedObjects] = useState<Set<string>>(new Set());
  const [templateName, setTemplateName] = useState<string>('');
  const [templateDescription, setTemplateDescription] = useState<string>('');
  const [fieldLabels, setFieldLabels] = useState<Record<string, string>>({}); 
  const [extractionFields, setExtractionFields] = useState<Array<{
    id: string;
    boundingBox: [number, number, number, number]; // [x0, y0, x1, y1] in PDF coordinates
    page: number;
    label: string;
    description: string;
    required: boolean;
    validationRegex?: string;
  }>>([]);
  const [selectedExtractionField, setSelectedExtractionField] = useState<string | null>(null);
  const [editingField, setEditingField] = useState<string | null>(null); // For editing/creating extraction fields
  // Box drawing state
  const [isDrawingMode, setIsDrawingMode] = useState(false);
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawingBox, setDrawingBox] = useState<{x: number, y: number, width: number, height: number} | null>(null);
  const [tempFieldData, setTempFieldData] = useState<{id: string, boundingBox: [number, number, number, number], page: number} | null>(null);
  const [saving, setSaving] = useState(false);
  // Field editor form state - must be at component level to follow Rules of Hooks
  const [fieldLabel, setFieldLabel] = useState('');
  const [fieldDescription, setFieldDescription] = useState('');
  const [fieldRequired, setFieldRequired] = useState(false);
  const [fieldValidationRegex, setFieldValidationRegex] = useState('');
  
  // Ref for auto-focusing field label input
  const fieldLabelInputRef = useRef<HTMLInputElement>(null);
  
  // Auto-focus field label input when editing starts
  useEffect(() => {
    if (editingField && fieldLabelInputRef.current) {
      fieldLabelInputRef.current.focus();
      fieldLabelInputRef.current.select();
    }
  }, [editingField]);
  
  // Confirmation dialog state
  const [showCloseConfirmation, setShowCloseConfirmation] = useState(false);

  // Check if there's unsaved work that should trigger confirmation
  const hasUnsavedWork = () => {
    return (
      selectedObjects.size > 0 || // Has selected static objects
      extractionFields.length > 0 || // Has created extraction fields
      templateName.trim() !== '' || // Has template name
      templateDescription.trim() !== '' // Has template description
    );
  };

  useEffect(() => {
    if (runId) {
      // Clear all drawing/field state when switching to a new PDF document
      clearAllModalState();
      
      const timeoutId = setTimeout(() => {
        fetchPdfData();
      }, 100);
      
      return () => {
        clearTimeout(timeoutId);
      };
    }
  }, [runId]);

  useEffect(() => {
    return () => {
      if (pdfData) {
        console.log('TemplateBuilderModal unmounting, cleaning up PDF data');
        // Clear all drawing/field state when modal unmounts
        clearAllModalState();
      }
    };
  }, [pdfData]);

  // Clear drawing state when switching steps (but preserve selected objects)
  useEffect(() => {
    clearStepTransitionState();
  }, [currentStep]);

  const clearStepTransitionState = () => {
    console.log('Clearing step transition state');
    
    // Clear drawing mode and drawing state
    setIsDrawingMode(false);
    setIsDrawing(false);
    setDrawingBox(null);
    
    // Clear temporary field data
    setTempFieldData(null);
    setEditingField(null);
    
    // Clear field form state
    setFieldLabel('');
    setFieldDescription('');
    setFieldRequired(false);
    setFieldValidationRegex('');
    
    // Clear selection state
    setSelectedExtractionField(null);
    
    // NOTE: Do NOT clear selectedObjects - they should persist across steps
  };

  const clearAllModalState = () => {
    console.log('Clearing all modal state');
    
    // Clear all step transition state
    clearStepTransitionState();
    
    // Also clear selected objects, extraction fields, template info, reset step, and hide all object types
    setSelectedObjects(new Set());
    setExtractionFields([]);
    setTemplateName('');
    setTemplateDescription('');
    setCurrentStep('object-selection');
    setSelectedObjectTypes(new Set());
  };

  const handleModalClose = () => {
    // Check if there's unsaved work before closing
    if (hasUnsavedWork()) {
      setShowCloseConfirmation(true);
      return;
    }
    
    // No unsaved work, close immediately
    console.log('Modal closing - clearing all state');
    clearAllModalState();
    onClose();
  };

  const handleConfirmClose = () => {
    console.log('Modal closing confirmed - clearing all state');
    setShowCloseConfirmation(false);
    clearAllModalState();
    onClose();
  };

  const handleCancelClose = () => {
    setShowCloseConfirmation(false);
  };

  const fetchPdfData = async () => {
    if (!runId) return;

    setLoading(true);
    setError(null);
    
    // Clear drawing state when loading new PDF data
    clearAllModalState();

    try {
      console.log('Fetching PDF data for run:', runId);
      const rawData = await apiClient.getEtoRunPdfData(runId);
      console.log('Raw PDF data loaded:', rawData);
      
      // PDF objects are now directly available in rawData.pdf_objects (new workflow)
      const objects = rawData.pdf_objects || [];
      const objectCount = objects.length;
      
      console.log('PDF objects loaded:', objectCount, 'objects found');
      console.log('Processing status:', rawData.status, rawData.processing_step);
      
      // Create the expected data structure (rawData already matches our interface)
      const pdfData: EtoRunPdfData = {
        ...rawData,
        object_count: objectCount  // Ensure object_count matches actual array length
      };
      
      console.log('Processed PDF data:', pdfData);
      setPdfData(pdfData);
    } catch (err: any) {
      console.error('Error loading PDF data:', err);
      setError(err.message || 'Failed to load PDF data');
    } finally {
      setLoading(false);
    }
  };

  const handleObjectTypeToggle = (type: string) => {
    const newSelected = new Set(selectedObjectTypes);
    if (newSelected.has(type)) {
      newSelected.delete(type);
    } else {
      newSelected.add(type);
    }
    setSelectedObjectTypes(newSelected);
  };

  const handleShowAllTypes = () => {
    if (!pdfData) return;
    const allTypes = new Set(Object.keys(getObjectTypeCounts()));
    setSelectedObjectTypes(allTypes);
  };

  const handleHideAllTypes = () => {
    setSelectedObjectTypes(new Set());
  };

  const handleObjectClick = (obj: any) => {
    if (currentStep === 'object-selection') {
      // Handle object selection for template building
      const objectId = `${obj.type}-${obj.page}-${obj.bbox.join('-')}`;
      console.log('Object clicked:', objectId, obj);
      const newSelected = new Set(selectedObjects);
      
      if (newSelected.has(objectId)) {
        newSelected.delete(objectId);
      } else {
        newSelected.add(objectId);
      }
      
      setSelectedObjects(newSelected);
      console.log('Selected objects updated:', {
        objectId,
        wasSelected: selectedObjects.has(objectId),
        totalSelected: newSelected.size
      });
    } else if (currentStep === 'field-labels') {
      // In field-labels step, check if clicking on an existing extraction field
      const clickX = obj.bbox[0];
      const clickY = obj.bbox[1];
      const clickPage = obj.page;
      
      const existingField = extractionFields.find(field => {
        if (field.page !== clickPage) return false;
        const [x0, y0, x1, y1] = field.boundingBox;
        return clickX >= x0 && clickX <= x1 && clickY >= y0 && clickY <= y1;
      });
      
      if (existingField) {
        setSelectedExtractionField(existingField.id);
        setEditingField(null);
        setIsDrawingMode(false);
        console.log('Showing extraction field:', existingField);
      }
    }
  };

  const handleStartDrawing = () => {
    if (currentStep === 'field-labels' && !editingField && !selectedExtractionField) {
      setIsDrawingMode(true);
      setSelectedExtractionField(null);
      setEditingField(null);
    }
  };

  const handleObjectDoubleClick = () => {
    // Double-click now just starts drawing mode instead of creating fields directly
    if (currentStep === 'field-labels') {
      handleStartDrawing();
    }
  };

  // Box drawing handlers
  const handleMouseDown = (e: React.MouseEvent, pageElement: HTMLElement, currentPage: number, scale: number, pageHeight: number) => {
    // Enable drawing in field-labels step when not viewing/editing fields
    const canDraw = currentStep === 'field-labels' && !editingField && !selectedExtractionField;
    if (!canDraw) return;
    
    e.preventDefault();
    const rect = pageElement.getBoundingClientRect();
    const anchorX = (e.clientX - rect.left) / scale;
    const anchorY = (e.clientY - rect.top) / scale;
    
    setIsDrawing(true);
    // Store the anchor point and start with zero width/height
    setDrawingBox({ x: anchorX, y: anchorY, width: 0, height: 0 });
  };

  const handleMouseMove = (e: React.MouseEvent, pageElement: HTMLElement, _currentPage: number, scale: number, _pageHeight: number) => {
    if (!isDrawing || !drawingBox) return;
    
    e.preventDefault();
    const rect = pageElement.getBoundingClientRect();
    const currentX = (e.clientX - rect.left) / scale;
    const currentY = (e.clientY - rect.top) / scale;
    
    // Keep the original anchor point fixed and calculate width/height from there
    // The anchor point is stored in drawingBox.x and drawingBox.y
    const anchorX = drawingBox.x;
    const anchorY = drawingBox.y;
    
    setDrawingBox({
      x: anchorX, // Keep anchor X fixed
      y: anchorY, // Keep anchor Y fixed  
      width: currentX - anchorX,  // Width can be positive or negative
      height: currentY - anchorY  // Height can be positive or negative
    });
  };

  const handleMouseUp = (e: React.MouseEvent, _pageElement: HTMLElement, currentPage: number, _scale: number, pageHeight: number) => {
    if (!isDrawing || !drawingBox) return;
    
    e.preventDefault();
    
    // Only create field if the drawn box has meaningful size (check absolute values since width/height can be negative)
    if (Math.abs(drawingBox.width) > 10 && Math.abs(drawingBox.height) > 10) {
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
      
      // Convert screen coordinates to PDF coordinates (flip Y axis)
      const pdfX0 = normalizedX0;
      const pdfY0 = pageHeight - normalizedY1; // Flip Y coordinate
      const pdfX1 = normalizedX1;
      const pdfY1 = pageHeight - normalizedY0;
      
      const newFieldId = `field_${Date.now()}`;
      setTempFieldData({
        id: newFieldId,
        boundingBox: [pdfX0, pdfY0, pdfX1, pdfY1],
        page: currentPage - 1 // Convert to 0-based
      });
      
      setEditingField(newFieldId);
      setIsDrawingMode(false);
      
      // Reset form fields
      setFieldLabel('');
      setFieldDescription('');
      setFieldRequired(false);
      setFieldValidationRegex('');
      
      console.log('Created extraction field with bounding box:', {
        boundingBox: [pdfX0, pdfY0, pdfX1, pdfY1],
        page: currentPage - 1
      });
    }
    
    setIsDrawing(false);
    setDrawingBox(null);
  };

  const handleNextStep = () => {
    if (currentStep === 'object-selection') {
      if (!templateName.trim()) {
        setError('Template name is required');
        return;
      }

      if (selectedObjects.size === 0) {
        setError('Please select at least one object for the template');
        return;
      }

      // Initialize field labels for word objects
      const wordObjects = pdfData?.pdf_objects?.filter(obj => {
        const objectId = `${obj.type}-${obj.page}-${obj.bbox.join('-')}`;
        return selectedObjects.has(objectId) && obj.type === 'word';
      }) || [];
      
      const initialLabels: Record<string, string> = {};
      wordObjects.forEach(obj => {
        const objectId = `${obj.type}-${obj.page}-${obj.bbox.join('-')}`;
        if (!fieldLabels[objectId]) {
          initialLabels[objectId] = '';
        }
      });
      
      setFieldLabels(prev => ({ ...prev, ...initialLabels }));
      setCurrentStep('field-labels');
      setError(null);
    }
  };

  const handlePreviousStep = () => {
    if (currentStep === 'field-labels') {
      setCurrentStep('object-selection');
      setError(null);
    }
  };

  const handleSave = async () => {
    if (!pdfData) return;
    
    setSaving(true);
    setError(null);
    
    try {
      const selectedObjectData = pdfData.pdf_objects.filter(obj => {
        const objectId = `${obj.type}-${obj.page}-${obj.bbox.join('-')}`;
        return selectedObjects.has(objectId);
      });

      const objectsWithLabels = selectedObjectData.map(obj => {
        const objectId = `${obj.type}-${obj.page}-${obj.bbox.join('-')}`;
        return {
          ...obj,
          field_label: fieldLabels[objectId] || null
        };
      });
      
      const templateData = {
        name: templateName,
        description: templateDescription,
        source_pdf_id: pdfData.pdf_id,
        source_eto_run_id: pdfData.eto_run_id,
        filename: pdfData.filename,
        selected_objects: objectsWithLabels,
        extraction_fields: extractionFields.map(field => ({
          id: field.id,
          label: field.label,
          description: field.description,
          required: field.required,
          validationRegex: field.validationRegex,
          boundingBox: field.boundingBox,
          page: field.page
        }))
      };
      
      console.log('Template Builder - Saving template:', {
        selectedCount: objectsWithLabels.length,
        labeledFields: Object.keys(fieldLabels).filter(k => fieldLabels[k]).length,
        extractionFields: extractionFields.length
      });
      
      const result = await apiClient.createTemplate(templateData);
      
      console.log('Template created successfully:', result);
      
      if (result.reprocessing) {
        console.log('Reprocessing triggered:', result.reprocessing);
        if (result.reprocessing.reprocessed > 0) {
          alert(`Template created successfully!\\n\\nReprocessing ${result.reprocessing.reprocessed} previously unrecognized PDFs...`);
        }
      } else if (result.reprocessing_error) {
        console.warn('Reprocessing failed:', result.reprocessing_error);
        alert(`Template created successfully!\\n\\nWarning: Automatic reprocessing failed: ${result.reprocessing_error}`);
      }
      
      onSave(templateData);
      
    } catch (err: any) {
      console.error('Error saving template:', err);
      setError(err.response?.data?.error || err.message || 'Failed to save template');
    } finally {
      setSaving(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleFieldLabelChange = (objectId: string, label: string) => {
    setFieldLabels(prev => ({
      ...prev,
      [objectId]: label
    }));
  };

  const handleSaveExtractionField = () => {
    if (!editingField || !tempFieldData || !fieldLabel.trim()) return;

    const newField = {
      id: editingField,
      boundingBox: tempFieldData.boundingBox,
      page: tempFieldData.page,
      label: fieldLabel,
      description: fieldDescription,
      required: fieldRequired,
      validationRegex: fieldValidationRegex || undefined
    };

    console.log('Saving new extraction field:', newField);

    setExtractionFields(prev => [...prev, newField]);
    setEditingField(null);
    setTempFieldData(null);
    setSelectedExtractionField(null); // Return to main field creation mode, don't view the new field
    
    // Reset form fields
    setFieldLabel('');
    setFieldDescription('');
    setFieldRequired(false);
    setFieldValidationRegex('');
  };
  
  // Handle Enter key press in field form
  const handleFieldFormKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSaveExtractionField();
    }
  };

  const handleDeleteExtractionField = (fieldId: string) => {
    setExtractionFields(prev => prev.filter(field => field.id !== fieldId));
    if (selectedExtractionField === fieldId) {
      setSelectedExtractionField(null);
    }
    console.log('Deleted extraction field:', fieldId);
  };

  const handleCancelFieldEdit = () => {
    setEditingField(null);
    setTempFieldData(null);
    // Reset form fields
    setFieldLabel('');
    setFieldDescription('');
    setFieldRequired(false);
    setFieldValidationRegex('');
    console.log('Cancelled field editing');
  };

  const renderSidebarContent = () => {
    if (editingField) {
      return renderFieldEditor();
    } else if (selectedExtractionField) {
      return renderFieldViewer();
    } else {
      return renderTemplateInfo();
    }
  };

  const renderTemplateInfo = () => (
    <div>
      <h3 className="text-sm font-semibold text-white mb-3">Template Information</h3>
      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-gray-300 mb-1">Template Name</label>
          <input
            type="text"
            value={templateName}
            onChange={(e) => setTemplateName(e.target.value)}
            disabled={currentStep === 'field-labels'}
            className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none disabled:opacity-50"
            placeholder="Enter template name"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-300 mb-1">Description</label>
          <textarea
            value={templateDescription}
            onChange={(e) => setTemplateDescription(e.target.value)}
            disabled={currentStep === 'field-labels'}
            rows={2}
            className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none resize-none disabled:opacity-50"
            placeholder="Describe this template..."
          />
        </div>
      </div>
    </div>
  );

  const renderFieldEditor = () => {
    return (
      <div>
        <div className="flex items-center mb-4">
          <button
            onClick={handleCancelFieldEdit}
            className="mr-3 p-1 text-gray-400 hover:text-white"
          >
            ← Back
          </button>
          <h3 className="text-sm font-semibold text-white">Create Extraction Field</h3>
        </div>
        
        {/* Show the drawn area information */}
        {tempFieldData && (
          <div className="mb-4 p-3 bg-gray-800 border border-gray-600 rounded">
            <div className="text-xs text-gray-400 mb-1">Extraction Area:</div>
            <div className="text-sm text-white">
              Page {tempFieldData.page + 1}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Box: {tempFieldData.boundingBox.map(n => Math.round(n)).join(', ')}
            </div>
          </div>
        )}
        
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Field Label</label>
            <input
              ref={fieldLabelInputRef}
              type="text"
              value={fieldLabel}
              onChange={(e) => setFieldLabel(e.target.value)}
              onKeyDown={handleFieldFormKeyDown}
              placeholder="e.g., hawb, carrier-name"
              className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Description</label>
            <textarea
              value={fieldDescription}
              onChange={(e) => setFieldDescription(e.target.value)}
              rows={2}
              placeholder="Describe what this field contains..."
              className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none resize-none"
            />
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              id="required"
              checked={fieldRequired}
              onChange={(e) => setFieldRequired(e.target.checked)}
              className="mr-2"
            />
            <label htmlFor="required" className="text-xs text-gray-300">Required field</label>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Validation Regex (Optional)</label>
            <input
              type="text"
              value={fieldValidationRegex}
              onChange={(e) => setFieldValidationRegex(e.target.value)}
              onKeyDown={handleFieldFormKeyDown}
              placeholder="^[A-Z0-9]+$"
              className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div className="flex space-x-2">
            <button
              onClick={handleSaveExtractionField}
              disabled={!fieldLabel.trim()}
              className="flex-1 px-3 py-2 text-sm bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white rounded"
            >
              Save Field
            </button>
            <button
              onClick={handleCancelFieldEdit}
              className="px-3 py-2 text-sm bg-gray-600 hover:bg-gray-700 text-white rounded"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    );
  };

  const renderFieldViewer = () => {
    const field = extractionFields.find(f => f.id === selectedExtractionField);
    if (!field) return null;

    return (
      <div>
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={() => setSelectedExtractionField(null)}
            className="p-1 text-gray-400 hover:text-white"
          >
            ← Back
          </button>
          <h3 className="text-sm font-semibold text-white flex-1 text-center">Extraction Field</h3>
          <button
            onClick={() => handleDeleteExtractionField(field.id)}
            className="w-8 h-8 bg-red-600 hover:bg-red-700 hover:scale-105 rounded text-white transition-all duration-200 flex items-center justify-center"
            title="Delete field"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
        
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1">Label</label>
            <div className="text-sm text-white">{field.label}</div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1">Description</label>
            <div className="text-sm text-gray-300">{field.description || 'No description'}</div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1">Required</label>
            <div className="text-sm text-gray-300">{field.required ? 'Yes' : 'No'}</div>
          </div>
          {field.validationRegex && (
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Validation</label>
              <div className="text-sm text-gray-300 font-mono">{field.validationRegex}</div>
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1">Extraction Area</label>
            <div className="text-sm text-gray-300">
              Page {field.page + 1}<br/>
              Box: {field.boundingBox.map(n => Math.round(n)).join(', ')}
            </div>
          </div>
        </div>

        {/* Rules Pipeline Section */}
        <div className="mt-6 pt-4 border-t border-gray-600">
          <h4 className="text-sm font-semibold text-white mb-3">Rules Pipeline</h4>
          <div className="text-xs text-gray-400 mb-3">
            Transform extracted text before final output
          </div>
          
          {/* TODO: Add rules list here when rules are implemented */}
          <div className="bg-gray-800 rounded p-3 mb-3">
            <div className="text-sm text-gray-400 text-center">No transformation rules defined</div>
          </div>
          
          <button
            onClick={() => {
              // TODO: Implement rule creation
              console.log('Create new transformation rule for field:', field.id);
            }}
            className="w-full px-3 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
          >
            + Add Transformation Step
          </button>
        </div>
      </div>
    );
  };

  const getObjectTypeCounts = () => {
    if (!pdfData || !pdfData.pdf_objects) return {};
    const counts: { [key: string]: number } = {};
    
    pdfData.pdf_objects.forEach(obj => {
      counts[obj.type] = (counts[obj.type] || 0) + 1;
    });
    
    return counts;
  };

  const objectCounts = getObjectTypeCounts();
  const pdfUrl = pdfData ? apiClient.getPdfFileUrl(pdfData.pdf_id) : '';

  if (!runId) return null;

  const modalContent = (
    <div 
      className="fixed inset-0 flex items-center justify-center z-[9999] p-4"
      style={{ 
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
        backdropFilter: 'blur(1px)'
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          handleModalClose();
        }
      }}
    >
      <div className="bg-gray-800 rounded-lg w-full h-full max-w-7xl max-h-[90vh] flex flex-col shadow-2xl border border-gray-600">
        {/* Header */}
        <div className="flex items-start justify-between p-3 border-b border-gray-700">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-lg font-semibold text-white truncate">
                Template Builder - {pdfData?.filename || 'Loading...'}
              </h2>
              <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-900 text-blue-300">
                {currentStep === 'object-selection' ? 'Step 1: Select Objects' : 'Step 2: Assign Field Labels'}
              </span>
            </div>
            {pdfData && (
              <div className="text-xs text-gray-400 grid grid-cols-1 lg:grid-cols-2 gap-x-6">
                <div>From: <span className="text-gray-300">{pdfData.email.sender_email}</span></div>
                <div>Size: <span className="text-gray-300">{formatFileSize(pdfData.file_size)}</span></div>
                <div className="truncate" title={pdfData.email.subject}>Subject: <span className="text-gray-300">{pdfData.email.subject}</span></div>
                <div>{pdfData.page_count} pages • {pdfData.object_count} objects</div>
              </div>
            )}
          </div>
          <button
            onClick={handleModalClose}
            className="ml-4 text-gray-400 hover:text-white p-1"
            aria-label="Close modal"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden" style={{ minHeight: 0, minWidth: 0 }}>
          {/* Left Sidebar - Dynamic Content */}
          <div className="w-80 flex-shrink-0 bg-gray-900 border-r border-gray-700 p-4 overflow-y-auto">
            {currentStep === 'object-selection' && (
              <>
                {/* Template Information */}
                <div className="mb-6">
                  {renderTemplateInfo()}
                </div>

                {/* Selection Summary */}
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-white mb-2">Selection Summary</h3>
                  <div className="bg-gray-800 rounded p-3">
                    <div className="text-lg font-semibold text-blue-300">{selectedObjects.size}</div>
                    <div className="text-xs text-gray-400">Objects Selected</div>
                  </div>
                </div>
              </>
            )}

            {currentStep === 'field-labels' && (
              <>
                {/* Dynamic Content Based on State */}
                <div className="mb-6">
                  {renderSidebarContent()}
                </div>

                {/* Extraction Fields List - Only show when not viewing or editing field details */}
                {!selectedExtractionField && !editingField && (
                  <div className="mb-6">
                    <h3 className="text-sm font-semibold text-white mb-2">Extraction Fields ({extractionFields.length})</h3>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {extractionFields.length === 0 ? (
                        <div className="bg-gray-800 rounded p-3 text-center">
                          <div className="text-sm text-gray-400">No fields defined yet</div>
                          <div className="text-xs text-gray-500 mt-1">Draw areas on the PDF to create fields</div>
                        </div>
                      ) : (
                        extractionFields.map((field) => (
                          <button
                            key={field.id}
                            onClick={() => setSelectedExtractionField(field.id)}
                            className="w-full text-left px-3 py-2 rounded text-sm bg-gray-800 hover:bg-gray-700 text-gray-300 transition-colors"
                          >
                            <div className="font-medium truncate">{field.label}</div>
                            <div className="text-xs text-gray-400 truncate mt-1">
                              Page {field.page + 1}{field.required && " • Required"}
                            </div>
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                )}


              </>
            )}

            {/* Object Type Visibility Controls - Only shown in object selection step */}
            {currentStep === 'object-selection' && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-white mb-3">Object Visibility</h3>
                
                <div className="space-y-2 mb-4">
                  <button
                    onClick={handleShowAllTypes}
                    className="w-full px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded"
                  >
                    Show All Types
                  </button>
                  <button
                    onClick={handleHideAllTypes}
                    className="w-full px-3 py-1 text-xs bg-gray-600 hover:bg-gray-700 text-white rounded"
                  >
                    Hide All Types
                  </button>
                </div>

                <div className="space-y-2">
                  {Object.entries(OBJECT_TYPE_NAMES).map(([type, label]) => {
                    const count = objectCounts[type] || 0;
                    const isSelected = selectedObjectTypes.has(type);
                    
                    if (count === 0) return null;
                    
                    return (
                      <div key={type} className="flex items-center">
                        <button
                          onClick={() => handleObjectTypeToggle(type)}
                          className={`flex-1 flex items-center justify-between p-2 text-xs rounded transition-colors ${
                            isSelected ? 'bg-gray-700 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                          }`}
                        >
                          <div className="flex items-center space-x-2">
                            <div
                              className="w-3 h-3 rounded"
                              style={{ backgroundColor: OBJECT_TYPE_COLORS[type as keyof typeof OBJECT_TYPE_COLORS] }}
                            ></div>
                            <span>{label}</span>
                          </div>
                          <span className="font-medium">{count}</span>
                        </button>
                      </div>
                    );
                  })}
                </div>

                {pdfData?.error_info?.error_message && (
                  <div className="mt-4 p-3 bg-red-900 border border-red-700 rounded">
                    <h4 className="text-sm font-semibold text-red-300 mb-1">
                      {pdfData.error_info.error_type || 'Error Details'}
                    </h4>
                    <p className="text-xs text-red-200">{pdfData.error_info.error_message}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Main Content - PDF Viewer (Object Selection Step) or Field Labels */}
          <div className="flex-1 flex flex-col overflow-hidden" style={{ minWidth: 0 }}>
            {currentStep === 'object-selection' && (
              <>
                {loading && (
                  <div className="flex-1 flex items-center justify-center">
                    <div className="text-white">Loading PDF data...</div>
                  </div>
                )}

                {error && (
                  <div className="flex-1 flex items-center justify-center">
                    <div className="text-center text-red-400">
                      <div className="text-xl mb-2">❌ Error</div>
                      <div>{error}</div>
                      <button
                        onClick={fetchPdfData}
                        className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
                      >
                        Retry
                      </button>
                    </div>
                  </div>
                )}

                {pdfData && pdfUrl && (
                  <PdfViewer
                    key={`pdf-${pdfData.pdf_id}-${pdfData.eto_run_id}`}
                    pdfUrl={pdfUrl}
                    objects={pdfData.pdf_objects}
                    showObjectOverlays={selectedObjectTypes.size > 0 || selectedObjects.size > 0}
                    selectedObjectTypes={selectedObjectTypes}
                    selectedObjects={selectedObjects}
                    className="flex-1"
                    onObjectClick={handleObjectClick}
                  />
                )}
              </>
            )}

            {currentStep === 'field-labels' && (
              <>  
                {pdfData && pdfUrl && (
                  <PdfViewer
                    key={`pdf-labels-${pdfData.pdf_id}-${pdfData.eto_run_id}`}
                    pdfUrl={pdfUrl}
                    objects={pdfData.pdf_objects} // Show all objects for reference
                    showObjectOverlays={false} // Don't show object overlays - box overlays are the primary visual
                    selectedObjectTypes={new Set(['word', 'text_line'])} // Show text for context
                    selectedObjects={new Set()}
                    extractionFields={extractionFields}
                    isDrawingMode={currentStep === 'field-labels' && !editingField && !selectedExtractionField}
                    drawingBox={drawingBox}
                    tempFieldData={tempFieldData}
                    className="flex-1"
                    onObjectClick={handleObjectClick}
                    onObjectDoubleClick={handleObjectDoubleClick}
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                  />
                )}
              </>
            )}
          </div>
        </div>

        {/* Footer - Action Buttons */}
        <div className="flex items-center justify-between p-4 border-t border-gray-700">
          <div className="text-sm text-gray-400">
            {currentStep === 'object-selection' 
              ? `Click on objects in the PDF to select them for your template. Selected: ${selectedObjects.size} objects`
              : `Draw areas on the PDF to create extraction fields. Click existing purple fields to view/edit. Fields defined: ${extractionFields.length}`
            }
          </div>
          <div className="flex space-x-3">
            {currentStep === 'field-labels' && (
              <button
                onClick={handlePreviousStep}
                disabled={saving}
                className="px-4 py-2 text-sm bg-gray-600 hover:bg-gray-700 disabled:bg-gray-500 disabled:cursor-not-allowed text-white rounded"
              >
                ← Back to Object Selection
              </button>
            )}
            <button
              onClick={handleModalClose}
              disabled={saving}
              className="px-4 py-2 text-sm bg-gray-600 hover:bg-gray-700 disabled:bg-gray-500 disabled:cursor-not-allowed text-white rounded"
            >
              Cancel
            </button>
            {currentStep === 'object-selection' ? (
              <div className="relative group">
                {/* Warning Speech Bubble - only show on hover when button is disabled */}
                {(!templateName.trim() || selectedObjects.size === 0) && (
                  <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none">
                    <div className="bg-amber-100 border border-amber-300 text-amber-800 px-3 py-2 rounded-lg shadow-lg text-xs font-medium whitespace-nowrap relative">
                      {/* Speech bubble arrow */}
                      <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-amber-300"></div>
                      <div className="absolute top-full left-1/2 transform -translate-x-1/2 translate-y-[-1px] w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-amber-100"></div>
                      
                      {/* Warning icon and message */}
                      <div className="flex items-center space-x-1">
                        <svg className="w-4 h-4 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                        <span>
                          {!templateName.trim() ? "Template name is required" : "Please select at least one object"}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
                
                <button
                  onClick={handleNextStep}
                  disabled={!templateName.trim() || selectedObjects.size === 0}
                  className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded"
                >
                  Next: Assign Labels →
                </button>
              </div>
            ) : (
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 text-sm bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded"
              >
                {saving ? 'Saving Template...' : 'Save Template'}
              </button>
            )}
          </div>
        </div>
      </div>

    </div>
  );

  // Confirmation Dialog Component - rendered as separate modal
  const confirmationDialog = showCloseConfirmation && (
    <div 
      className="fixed inset-0 flex items-center justify-center"
      style={{ 
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(2px)',
        zIndex: 10000 // Higher z-index to appear above template builder modal (which uses z-[9999])
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          handleCancelClose();
        }
      }}
    >
      <div className="bg-gray-800 border border-gray-600 rounded-lg p-6 max-w-md mx-4 shadow-xl">
        <div className="flex items-center mb-4">
          <svg className="w-6 h-6 text-amber-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <h3 className="text-lg font-semibold text-white">Unsaved Changes</h3>
        </div>
        
        <p className="text-gray-300 mb-6">
          You have unsaved changes to your template. Are you sure you want to close and lose this work?
        </p>

        <div className="flex space-x-3 justify-end">
          <button
            onClick={handleCancelClose}
            className="px-4 py-2 text-sm bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirmClose}
            className="px-4 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
          >
            Close & Lose Changes
          </button>
        </div>
      </div>
    </div>
  );

  // Use portal to render at the root level
  const rootElement = document.getElementById('root');
  if (!rootElement) return null;
  
  return (
    <>
      {createPortal(modalContent, rootElement)}
      {confirmationDialog && createPortal(confirmationDialog, rootElement)}
    </>
  );
}