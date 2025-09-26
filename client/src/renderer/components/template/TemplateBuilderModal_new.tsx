import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { PdfViewer_new } from '../pdf/PdfViewer_new';
import { apiClient } from '../../services/api';

interface TemplateBuilderModalProps {
  runId: string | null;
  onClose: () => void;
  onSave: (templateData: any) => void;
}

// ===== NESTED PDF OBJECT INTERFACES =====

interface BasePdfObject {
  page: number;
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
}

interface TextWordPdfObject extends BasePdfObject {
  text: string;
  fontname: string;
  fontsize: number;
}

interface TextLinePdfObject extends BasePdfObject {
  // Only has base fields
}

interface GraphicRectPdfObject extends BasePdfObject {
  linewidth: number;
}

interface GraphicLinePdfObject extends BasePdfObject {
  linewidth: number;
}

interface GraphicCurvePdfObject extends BasePdfObject {
  points: number[][];
  linewidth: number;
}

interface ImagePdfObject extends BasePdfObject {
  format: string;
  colorspace: string;
  bits: number;
}

interface TablePdfObject extends BasePdfObject {
  rows: number;
  cols: number;
}

interface PdfObjects {
  text_words: TextWordPdfObject[];
  text_lines: TextLinePdfObject[];
  graphic_rects: GraphicRectPdfObject[];
  graphic_lines: GraphicLinePdfObject[];
  graphic_curves: GraphicCurvePdfObject[];
  images: ImagePdfObject[];
  tables: TablePdfObject[];
}

interface EtoRunPdfData {
  run_id: number;
  pdf_id: number;
  filename: string;
  original_filename: string;
  page_count: number;
  object_count: number;
  file_size: number;
  sha256_hash: string;
  pdf_objects: PdfObjects;  // New nested structure

  // Email context (flat)
  email_subject: string;
  sender_email: string;
  received_date: string;

  // ETO run status and processing info
  status: "not_started" | "processing" | "success" | "failure" | "needs_template" | "skipped";
  processing_step?: "template_matching" | "extracting_data" | "transforming_data";
  matched_template_id?: number;

  // Processing data
  extracted_data?: any;  // Structured extracted field data
  transformation_audit?: any;  // Transformation audit trail
  target_data?: any;  // Final transformed data

  // Timestamps (flat)
  created_at?: string;
  started_at?: string;
  completed_at?: string;

  // Error info (flat)
  error_type?: string;
  error_message?: string;
}

// ===== OBJECT TYPE CONFIGURATIONS =====

type ObjectType = 'text_words' | 'text_lines' | 'graphic_rects' | 'graphic_lines' | 'graphic_curves' | 'images' | 'tables';

const OBJECT_TYPE_CONFIGS = {
  text_words: {
    label: 'Text Words',
    color: '#dc2626', // Red-600 - good contrast on white
    needsCoordinateFlip: true, // Text objects need Y coordinate flipping
    displayType: 'text_word' // For backwards compatibility with existing templates
  },
  text_lines: {
    label: 'Text Lines',
    color: '#059669', // Emerald-600 - darker green, much more visible
    needsCoordinateFlip: true,
    displayType: 'text_line'
  },
  graphic_rects: {
    label: 'Rectangles',
    color: '#2563eb', // Blue-600 - good contrast
    needsCoordinateFlip: false, // Graphics use direct coordinates
    displayType: 'graphic_rect'
  },
  graphic_lines: {
    label: 'Lines',
    color: '#d97706', // Amber-600 - much more visible than bright yellow
    needsCoordinateFlip: false,
    displayType: 'graphic_line'
  },
  graphic_curves: {
    label: 'Curves',
    color: '#c026d3', // Fuchsia-600 - good contrast
    needsCoordinateFlip: false,
    displayType: 'graphic_curve'
  },
  images: {
    label: 'Images',
    color: '#0891b2', // Cyan-600 - better than bright cyan
    needsCoordinateFlip: false, // Images use direct coordinates
    displayType: 'image'
  },
  tables: {
    label: 'Tables',
    color: '#ea580c', // Orange-600 - good contrast
    needsCoordinateFlip: false,
    displayType: 'table'
  }
} as const;

type TemplateBuilderStep = 'object-selection' | 'field-labels';

export function TemplateBuilderModal_new({ runId, onClose, onSave }: TemplateBuilderModalProps) {
  const [pdfData, setPdfData] = useState<EtoRunPdfData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<TemplateBuilderStep>('object-selection');
  const [selectedObjectTypes, setSelectedObjectTypes] = useState<Set<ObjectType>>(new Set());
  const [selectedObjects, setSelectedObjects] = useState<Set<string>>(new Set());
  const [selectedSignatureObjects, setSelectedSignatureObjects] = useState<PdfObjects>({
    text_words: [],
    text_lines: [],
    graphic_rects: [],
    graphic_lines: [],
    graphic_curves: [],
    images: [],
    tables: []
  });
  const [templateName, setTemplateName] = useState<string>('');
  const [templateDescription, setTemplateDescription] = useState<string>('');
  const [fieldLabels, setFieldLabels] = useState<Record<string, string>>({});
  const [showSignatureObjects, setShowSignatureObjects] = useState<boolean>(false);
  const [extractionFields, setExtractionFields] = useState<Array<{
    id: string;
    boundingBox: [number, number, number, number]; // [x0, y0, x1, y1] in PDF coordinates (Y-flipped)
    page: number;
    label: string;
    description: string;
    required: boolean;
  }>>([]);
  const [selectedExtractionField, setSelectedExtractionField] = useState<string | null>(null);
  const [editingField, setEditingField] = useState<string | null>(null);

  // Box drawing state
  const [isDrawingMode, setIsDrawingMode] = useState(false);
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawingBox, setDrawingBox] = useState<{x: number, y: number, width: number, height: number} | null>(null);
  const [tempFieldData, setTempFieldData] = useState<{id: string, boundingBox: [number, number, number, number], page: number} | null>(null);
  const [saving, setSaving] = useState(false);

  // Field editor form state
  const [fieldLabel, setFieldLabel] = useState('');
  const [fieldDescription, setFieldDescription] = useState('');
  const [fieldRequired, setFieldRequired] = useState(false);

  const fieldLabelInputRef = useRef<HTMLInputElement>(null);

  // Confirmation dialog state
  const [showCloseConfirmation, setShowCloseConfirmation] = useState(false);

  // Auto-focus field label input when editing starts
  useEffect(() => {
    if (editingField && fieldLabelInputRef.current) {
      fieldLabelInputRef.current.focus();
      fieldLabelInputRef.current.select();
    }
  }, [editingField]);

  // Check if there's unsaved work that should trigger confirmation
  const hasUnsavedWork = () => {
    return (
      selectedObjects.size > 0 ||
      extractionFields.length > 0 ||
      templateName.trim() !== '' ||
      templateDescription.trim() !== ''
    );
  };

  useEffect(() => {
    if (runId) {
      clearAllModalState();
      const timeoutId = setTimeout(() => {
        fetchPdfData();
      }, 100);
      return () => clearTimeout(timeoutId);
    }
  }, [runId]);

  useEffect(() => {
    return () => {
      if (pdfData) {
        clearAllModalState();
      }
    };
  }, [pdfData]);

  useEffect(() => {
    clearStepTransitionState();
  }, [currentStep]);

  const clearStepTransitionState = () => {
    setIsDrawingMode(false);
    setIsDrawing(false);
    setDrawingBox(null);
    setTempFieldData(null);
    setEditingField(null);
    setFieldLabel('');
    setFieldDescription('');
    setFieldRequired(false);
    setSelectedExtractionField(null);
  };

  const clearAllModalState = () => {
    clearStepTransitionState();
    setSelectedObjects(new Set());
    setExtractionFields([]);
    setTemplateName('');
    setTemplateDescription('');
    setCurrentStep('object-selection');
    setSelectedObjectTypes(new Set());
  };

  const handleModalClose = () => {
    if (hasUnsavedWork()) {
      setShowCloseConfirmation(true);
      return;
    }
    clearAllModalState();
    onClose();
  };

  const handleConfirmClose = () => {
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
    clearAllModalState();

    try {
      const rawData = await apiClient.getEtoRunPdfData(runId);

      // Calculate total object count from nested structure
      const objectCount = getTotalObjectCount(rawData.pdf_objects);

      const pdfData: EtoRunPdfData = {
        ...rawData,
        object_count: objectCount
      };

      setPdfData(pdfData);
    } catch (err: any) {
      setError(err.message || 'Failed to load PDF data');
    } finally {
      setLoading(false);
    }
  };

  // ===== HELPER FUNCTIONS FOR NESTED STRUCTURE =====

  const getTotalObjectCount = (objects: PdfObjects): number => {
    return (
      (objects.text_words?.length || 0) +
      (objects.text_lines?.length || 0) +
      (objects.graphic_rects?.length || 0) +
      (objects.graphic_lines?.length || 0) +
      (objects.graphic_curves?.length || 0) +
      (objects.images?.length || 0) +
      (objects.tables?.length || 0)
    );
  };

  const getObjectTypeCounts = (): Record<ObjectType, number> => {
    if (!pdfData?.pdf_objects) {
      return {
        text_words: 0,
        text_lines: 0,
        graphic_rects: 0,
        graphic_lines: 0,
        graphic_curves: 0,
        images: 0,
        tables: 0
      };
    }

    return {
      text_words: pdfData.pdf_objects.text_words?.length || 0,
      text_lines: pdfData.pdf_objects.text_lines?.length || 0,
      graphic_rects: pdfData.pdf_objects.graphic_rects?.length || 0,
      graphic_lines: pdfData.pdf_objects.graphic_lines?.length || 0,
      graphic_curves: pdfData.pdf_objects.graphic_curves?.length || 0,
      images: pdfData.pdf_objects.images?.length || 0,
      tables: pdfData.pdf_objects.tables?.length || 0
    };
  };

  // Generate unique ID for any object based on type, page, and bbox
  const generateObjectId = (type: string, page: number, bbox: [number, number, number, number]): string => {
    return `${type}-${page}-${bbox.join('-')}`;
  };

  const handleObjectTypeToggle = (type: ObjectType) => {
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
    const counts = getObjectTypeCounts();
    const typesWithObjects = (Object.keys(counts) as ObjectType[]).filter(type => counts[type] > 0);
    setSelectedObjectTypes(new Set(typesWithObjects));
  };

  const handleHideAllTypes = () => {
    setSelectedObjectTypes(new Set());
  };

  const handleObjectClick = (obj: any) => {
    if (currentStep === 'object-selection') {
      const objectId = generateObjectId(obj.type, obj.page, obj.bbox);
      const newSelected = new Set(selectedObjects);

      // Find the actual object from pdfData to get full object data
      let actualObject = null;
      const objectTypeKey = obj.objectType as ObjectType; // obj.objectType is the key like 'text_words'

      if (pdfData && pdfData.pdf_objects[objectTypeKey]) {
        actualObject = pdfData.pdf_objects[objectTypeKey].find((pdfObj: any) => {
          const pdfObjId = generateObjectId(OBJECT_TYPE_CONFIGS[objectTypeKey].displayType, pdfObj.page, pdfObj.bbox);
          return pdfObjId === objectId;
        });
      }

      if (newSelected.has(objectId)) {
        // Remove object
        newSelected.delete(objectId);

        // Remove from selectedSignatureObjects
        if (actualObject) {
          setSelectedSignatureObjects(prev => ({
            ...prev,
            [objectTypeKey]: prev[objectTypeKey].filter((sigObj: any) => {
              const sigObjId = generateObjectId(OBJECT_TYPE_CONFIGS[objectTypeKey].displayType, sigObj.page, sigObj.bbox);
              return sigObjId !== objectId;
            })
          }));
        }
      } else {
        // Add object
        newSelected.add(objectId);

        // Add to selectedSignatureObjects
        if (actualObject) {
          setSelectedSignatureObjects(prev => ({
            ...prev,
            [objectTypeKey]: [...prev[objectTypeKey], actualObject]
          }));
        }
      }

      setSelectedObjects(newSelected);
    } else if (currentStep === 'field-labels') {
      // Handle extraction field interaction
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
      }
    }
  };

  const handleStartDrawing = () => {
    if (currentStep === 'field-labels') {
      // If currently editing a field, cancel the edit (equivalent to clicking cancel)
      if (editingField) {
        handleCancelFieldEdit();
      }

      setIsDrawingMode(true);
      setSelectedExtractionField(null); // Clear any selected field when starting to draw
      setEditingField(null);
    }
  };

  const handleObjectDoubleClick = () => {
    if (currentStep === 'field-labels') {
      handleStartDrawing();
    }
  };

  const handleExtractionFieldClick = (field: {
    id: string;
    boundingBox: [number, number, number, number];
    page: number;
    label: string;
    description: string;
    required: boolean;
  }) => {
    if (currentStep === 'field-labels') {
      setSelectedExtractionField(field.id);
      setEditingField(field.id);

      // Populate form fields with existing data
      setFieldLabel(field.label);
      setFieldDescription(field.description);
      setFieldRequired(field.required);
    }
  };

  // Box drawing handlers
  const handleMouseDown = (e: React.MouseEvent, pageElement: HTMLElement, currentPage: number, scale: number, pageHeight: number) => {
    if (currentStep !== 'field-labels') return;

    // If currently editing a field, cancel the edit (equivalent to clicking cancel)
    if (editingField) {
      handleCancelFieldEdit();
    }

    // Clear any selected field when starting to draw
    if (selectedExtractionField) {
      setSelectedExtractionField(null);
    }

    e.preventDefault();
    const rect = pageElement.getBoundingClientRect();
    const anchorX = (e.clientX - rect.left) / scale;
    const anchorY = (e.clientY - rect.top) / scale;

    setIsDrawing(true);
    setDrawingBox({ x: anchorX, y: anchorY, width: 0, height: 0 });
  };

  const handleMouseMove = (e: React.MouseEvent, pageElement: HTMLElement, _currentPage: number, scale: number, _pageHeight: number) => {
    if (!isDrawing || !drawingBox) return;

    e.preventDefault();
    const rect = pageElement.getBoundingClientRect();
    const currentX = (e.clientX - rect.left) / scale;
    const currentY = (e.clientY - rect.top) / scale;

    const anchorX = drawingBox.x;
    const anchorY = drawingBox.y;

    setDrawingBox({
      x: anchorX,
      y: anchorY,
      width: currentX - anchorX,
      height: currentY - anchorY
    });
  };

  const handleMouseUp = (e: React.MouseEvent, _pageElement: HTMLElement, currentPage: number, _scale: number, pageHeight: number) => {
    if (!isDrawing || !drawingBox) return;

    e.preventDefault();

    if (Math.abs(drawingBox.width) > 10 && Math.abs(drawingBox.height) > 10) {
      const screenX0 = drawingBox.x;
      const screenY0 = drawingBox.y;
      const screenX1 = drawingBox.x + drawingBox.width;
      const screenY1 = drawingBox.y + drawingBox.height;

      const normalizedX0 = Math.min(screenX0, screenX1);
      const normalizedY0 = Math.min(screenY0, screenY1);
      const normalizedX1 = Math.max(screenX0, screenX1);
      const normalizedY1 = Math.max(screenY0, screenY1);

      // Keep screen coordinates as-is (no Y-flipping needed since PDF text_words use same coordinate system)
      const newFieldId = `field_${Date.now()}`;
      setTempFieldData({
        id: newFieldId,
        boundingBox: [normalizedX0, normalizedY0, normalizedX1, normalizedY1],
        page: currentPage - 1 // Convert to 0-based
      });

      setEditingField(newFieldId);
      setIsDrawingMode(false);

      // Reset form fields
      setFieldLabel('');
      setFieldDescription('');
      setFieldRequired(false);
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

      // Log selected signature objects in PdfObjects format
      console.log('=== SELECTED SIGNATURE OBJECTS ===');
      console.log('PdfObjects format (native metadata preserved):', selectedSignatureObjects);
      console.log('Selected Object Types:', Array.from(selectedObjectTypes));
      console.log('Selected Object IDs:', Array.from(selectedObjects));
      console.log('Object counts by type:', {
        text_words: selectedSignatureObjects.text_words.length,
        text_lines: selectedSignatureObjects.text_lines.length,
        graphic_rects: selectedSignatureObjects.graphic_rects.length,
        graphic_lines: selectedSignatureObjects.graphic_lines.length,
        graphic_curves: selectedSignatureObjects.graphic_curves.length,
        images: selectedSignatureObjects.images.length,
        tables: selectedSignatureObjects.tables.length
      });

      // Verify native metadata preservation - log first object of each type that has selections
      Object.entries(selectedSignatureObjects).forEach(([key, objects]) => {
        if (objects.length > 0) {
          console.log(`Sample ${key} object with native metadata:`, objects[0]);
        }
      });

      // Initialize field labels for selected text objects
      const initialLabels: Record<string, string> = {};

      if (pdfData?.pdf_objects.text_words) {
        pdfData.pdf_objects.text_words.forEach(obj => {
          const objectId = generateObjectId('text_word', obj.page, obj.bbox);
          if (selectedObjects.has(objectId) && !fieldLabels[objectId]) {
            initialLabels[objectId] = '';
          }
        });
      }

      setFieldLabels(prev => ({ ...prev, ...initialLabels }));

      // Hide all object types when moving to extraction definitions
      setSelectedObjectTypes(new Set());
      setShowSignatureObjects(false);

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
      // Create the nested PdfObjects structure expected by backend
      const initial_signature_objects = {
        text_words: [] as any[],
        text_lines: [] as any[],
        graphic_rects: [] as any[],
        graphic_lines: [] as any[],
        graphic_curves: [] as any[],
        images: [] as any[],
        tables: [] as any[]
      };

      // Process each object type and transform selected objects
      Object.entries(pdfData.pdf_objects).forEach(([objectType, objects]) => {
        if (!objects || !Array.isArray(objects)) return;

        const config = OBJECT_TYPE_CONFIGS[objectType as ObjectType];
        if (!config) return;

        objects.forEach(obj => {
          const objectId = generateObjectId(config.displayType, obj.page, obj.bbox);
          if (selectedObjects.has(objectId)) {
            // Create object in backend format (note: page is already 1-based in pdfData)
            const backendObj: any = {
              page: obj.page, // Keep 1-based indexing for backend
              bbox: obj.bbox
            };

            // Add type-specific properties
            switch (objectType as ObjectType) {
              case 'text_words':
                const textWord = obj as TextWordPdfObject;
                backendObj.text = textWord.text;
                backendObj.fontname = textWord.fontname;
                backendObj.fontsize = textWord.fontsize;
                initial_signature_objects.text_words.push(backendObj);
                break;
              case 'text_lines':
                initial_signature_objects.text_lines.push(backendObj);
                break;
              case 'graphic_rects':
                const rect = obj as GraphicRectPdfObject;
                backendObj.linewidth = rect.linewidth;
                initial_signature_objects.graphic_rects.push(backendObj);
                break;
              case 'graphic_lines':
                const line = obj as GraphicLinePdfObject;
                backendObj.linewidth = line.linewidth;
                initial_signature_objects.graphic_lines.push(backendObj);
                break;
              case 'graphic_curves':
                const curve = obj as GraphicCurvePdfObject;
                backendObj.points = curve.points;
                backendObj.linewidth = curve.linewidth;
                initial_signature_objects.graphic_curves.push(backendObj);
                break;
              case 'images':
                const image = obj as ImagePdfObject;
                backendObj.format = image.format;
                backendObj.colorspace = image.colorspace;
                backendObj.bits = image.bits;
                initial_signature_objects.images.push(backendObj);
                break;
              case 'tables':
                const table = obj as TablePdfObject;
                backendObj.rows = table.rows;
                backendObj.cols = table.cols;
                initial_signature_objects.tables.push(backendObj);
                break;
            }
          }
        });
      });

      // Transform extraction fields to backend format
      // Note: Keep coordinates as-is since PDF text_words use the same coordinate system
      const initial_extraction_fields = extractionFields.map(field => ({
        label: field.label,
        bounding_box: field.boundingBox, // Change from boundingBox to bounding_box, keep coordinates as-is
        page: field.page + 1, // Convert from 0-based to 1-based for backend
        required: field.required,
        description: field.description || undefined,
        validation_regex: undefined // We removed this from frontend, set as undefined
      }));

      const templateData = {
        name: templateName,
        description: templateDescription,
        source_pdf_id: pdfData.pdf_id,
        initial_signature_objects,
        initial_extraction_fields
      };

      const result = await apiClient.createTemplate(templateData);

      alert(`Template "${result.name}" created successfully with ID: ${result.id}`);
      onSave(result);

    } catch (err: any) {
      console.error('Template creation error:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to save template');
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
      required: fieldRequired
    };

    setExtractionFields(prev => [...prev, newField]);
    setEditingField(null);
    setTempFieldData(null);
    setSelectedExtractionField(null);

    // Reset form fields
    setFieldLabel('');
    setFieldDescription('');
    setFieldRequired(false);
  };

  const handleUpdateExtractionField = () => {
    if (!editingField || !fieldLabel.trim()) return;

    setExtractionFields(prev =>
      prev.map(field =>
        field.id === editingField
          ? {
              ...field,
              label: fieldLabel,
              description: fieldDescription,
              required: fieldRequired
            }
          : field
      )
    );

    setEditingField(null);
    setSelectedExtractionField(null);

    // Reset form fields
    setFieldLabel('');
    setFieldDescription('');
    setFieldRequired(false);
  };

  const handleSaveField = () => {
    // If we have tempFieldData, we're creating a new field
    // If we don't, we're editing an existing field
    if (tempFieldData) {
      handleSaveExtractionField();
    } else {
      handleUpdateExtractionField();
    }
  };

  const handleFieldFormKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSaveField();
    }
  };

  const handleDeleteExtractionField = (fieldId: string) => {
    setExtractionFields(prev => prev.filter(field => field.id !== fieldId));
    if (selectedExtractionField === fieldId) {
      setSelectedExtractionField(null);
    }
  };

  const handleCancelFieldEdit = () => {
    setEditingField(null);
    setTempFieldData(null);
    setSelectedExtractionField(null); // Clear selected field to return to main view
    setFieldLabel('');
    setFieldDescription('');
    setFieldRequired(false);
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

        {/* Show signature objects checkbox only in field-labels step */}
        {currentStep === 'field-labels' && (
          <div className="pt-2 border-t border-gray-700">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={showSignatureObjects}
                onChange={(e) => setShowSignatureObjects(e.target.checked)}
                className="rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-blue-500 focus:ring-offset-gray-800"
              />
              <span className="text-xs text-gray-300">Show signature objects</span>
            </label>
            {showSignatureObjects && (
              <div className="mt-2 text-xs text-gray-400">
                Signature objects: {
                  Object.values(selectedSignatureObjects).reduce((total, objects) => total + objects.length, 0)
                }
              </div>
            )}
          </div>
        )}
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
          <h3 className="text-sm font-semibold text-white">
            {tempFieldData ? 'Create Extraction Field' : 'Edit Extraction Field'}
          </h3>
        </div>

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
          <div className="flex space-x-2">
            <button
              onClick={handleSaveField}
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
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1">Extraction Area</label>
            <div className="text-sm text-gray-300">
              Page {field.page + 1}<br/>
              Box: {field.boundingBox.map(n => Math.round(n)).join(', ')}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const objectCounts = getObjectTypeCounts();
  const pdfUrl = runId ? apiClient.getEtoRunPdfContentUrl(runId) : '';

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
                Template Builder NEW - {pdfData?.original_filename || 'Loading...'}
              </h2>
              <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-900 text-blue-300">
                {currentStep === 'object-selection' ? 'Step 1: Select Objects' : 'Step 2: Assign Field Labels'}
              </span>
            </div>
            {pdfData && (
              <div className="text-xs text-gray-400 grid grid-cols-1 lg:grid-cols-2 gap-x-6">
                <div>From: <span className="text-gray-300">{pdfData.sender_email}</span></div>
                <div>Size: <span className="text-gray-300">{formatFileSize(pdfData.file_size)}</span></div>
                <div className="truncate" title={pdfData.email_subject}>Subject: <span className="text-gray-300">{pdfData.email_subject}</span></div>
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
          {/* Left Sidebar */}
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
                <div className="mb-6">
                  {renderSidebarContent()}
                </div>

                {/* Extraction Fields List */}
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
                            onClick={() => {
                              setSelectedExtractionField(field.id);
                              setEditingField(field.id);

                              // Populate form fields with existing data
                              setFieldLabel(field.label);
                              setFieldDescription(field.description);
                              setFieldRequired(field.required);
                            }}
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

            {/* Object Type Visibility Controls */}
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
                  {(Object.keys(OBJECT_TYPE_CONFIGS) as ObjectType[]).map(objectType => {
                    const config = OBJECT_TYPE_CONFIGS[objectType];
                    const count = objectCounts[objectType] || 0;
                    const isSelected = selectedObjectTypes.has(objectType);

                    if (count === 0) return null;

                    return (
                      <div key={objectType} className="flex items-center">
                        <button
                          onClick={() => handleObjectTypeToggle(objectType)}
                          className={`flex-1 flex items-center justify-between p-2 text-xs rounded transition-colors ${
                            isSelected ? 'bg-gray-700 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                          }`}
                        >
                          <div className="flex items-center space-x-2">
                            <div
                              className="w-3 h-3 rounded"
                              style={{ backgroundColor: config.color }}
                            ></div>
                            <span>{config.label}</span>
                          </div>
                          <span className="font-medium">{count}</span>
                        </button>
                      </div>
                    );
                  })}
                </div>

                {pdfData?.error_message && (
                  <div className="mt-4 p-3 bg-red-900 border border-red-700 rounded">
                    <h4 className="text-sm font-semibold text-red-300 mb-1">
                      {pdfData.error_type || 'Error Details'}
                    </h4>
                    <p className="text-xs text-red-200">{pdfData.error_message}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Main Content - PDF Viewer */}
          <div className="flex-1 flex flex-col overflow-hidden" style={{ minWidth: 0 }}>
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
              <PdfViewer_new
                key={`pdf-new-${pdfData.pdf_id}-${pdfData.run_id}`}
                pdfUrl={pdfUrl}
                pdfObjects={
                  currentStep === 'object-selection'
                    ? pdfData.pdf_objects
                    : currentStep === 'field-labels' && showSignatureObjects
                      ? selectedSignatureObjects  // Only pass selected objects in extraction step
                      : { // Empty PdfObjects structure when not showing signature objects
                          text_words: [],
                          text_lines: [],
                          graphic_rects: [],
                          graphic_lines: [],
                          graphic_curves: [],
                          images: [],
                          tables: []
                        }
                }
                showObjectOverlays={
                  currentStep === 'object-selection'
                    ? selectedObjectTypes.size > 0 || selectedObjects.size > 0
                    : currentStep === 'field-labels' && showSignatureObjects
                }
                selectedObjectTypes={
                  currentStep === 'object-selection'
                    ? selectedObjectTypes
                    : currentStep === 'field-labels' && showSignatureObjects
                      ? new Set(Object.keys(selectedSignatureObjects).filter(key =>
                          selectedSignatureObjects[key as ObjectType].length > 0
                        ) as ObjectType[])
                      : new Set()
                }
                selectedObjects={
                  currentStep === 'object-selection'
                    ? selectedObjects
                    : currentStep === 'field-labels' && showSignatureObjects
                      ? selectedObjects
                      : new Set()
                }
                extractionFields={currentStep === 'field-labels' ? extractionFields : []}
                selectedExtractionFieldId={selectedExtractionField}
                isDrawingMode={currentStep === 'field-labels'}
                drawingBox={drawingBox}
                tempFieldData={tempFieldData}
                className="flex-1"
                onObjectClick={handleObjectClick}
                onObjectDoubleClick={handleObjectDoubleClick}
                onExtractionFieldClick={handleExtractionFieldClick}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
              />
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

  // Confirmation Dialog Component
  const confirmationDialog = showCloseConfirmation && (
    <div
      className="fixed inset-0 flex items-center justify-center"
      style={{
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(2px)',
        zIndex: 10000
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

  const rootElement = document.getElementById('root');
  if (!rootElement) return null;

  return (
    <>
      {createPortal(modalContent, rootElement)}
      {confirmationDialog && createPortal(confirmationDialog, rootElement)}
    </>
  );
}