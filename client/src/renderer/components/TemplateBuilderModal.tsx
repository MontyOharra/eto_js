import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { PdfViewer } from './PdfViewer';
import { apiClient } from '../services/api';

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
  objects: any[];
  email: {
    subject: string;
    sender_email: string;
    received_date: string;
  };
  status: string;
  error_message?: string;
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
    objectId: string;
    label: string;
    description: string;
    required: boolean;
    validationRegex?: string;
    obj: any; // Store the actual PDF object
  }>>([]);
  const [selectedExtractionField, setSelectedExtractionField] = useState<string | null>(null);
  const [editingField, setEditingField] = useState<string | null>(null); // For editing/creating extraction fields
  const [tempFieldData, setTempFieldData] = useState<{id: string, objectId: string, obj: any} | null>(null); // Temporary storage for field creation
  const [saving, setSaving] = useState(false);
  // Field editor form state - must be at component level to follow Rules of Hooks
  const [fieldLabel, setFieldLabel] = useState('');
  const [fieldDescription, setFieldDescription] = useState('');
  const [fieldRequired, setFieldRequired] = useState(false);
  const [fieldValidationRegex, setFieldValidationRegex] = useState('');

  useEffect(() => {
    if (runId) {
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
      }
    };
  }, [pdfData]);

  const fetchPdfData = async () => {
    if (!runId) return;

    setLoading(true);
    setError(null);

    try {
      console.log('Fetching PDF data for run:', runId);
      const rawData = await apiClient.getEtoRunPdfData(runId);
      console.log('Raw PDF data loaded:', rawData);
      
      // Parse the extracted data JSON to get objects
      let objects: any[] = [];
      let objectCount = 0;
      
      if (rawData.raw_extracted_data) {
        try {
          const extractedData = JSON.parse(rawData.raw_extracted_data);
          objects = extractedData.pdf_objects || [];
          objectCount = objects.length;
          console.log('Parsed objects:', objectCount, 'objects found');
        } catch (parseError) {
          console.error('Error parsing extracted data:', parseError);
          console.log('Raw extracted data:', rawData.raw_extracted_data);
        }
      }
      
      // Create the expected data structure
      const pdfData: EtoRunPdfData = {
        ...rawData,
        objects: objects,
        object_count: objectCount
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
      // Handle single click on extraction field - show existing field info
      const objectId = `${obj.type}-${obj.page}-${obj.bbox.join('-')}`;
      const existingField = extractionFields.find(field => field.objectId === objectId);
      
      if (existingField) {
        setSelectedExtractionField(existingField.id);
        setEditingField(null);
        console.log('Showing extraction field:', existingField);
      }
    }
  };

  const handleObjectDoubleClick = (obj: any) => {
    if (currentStep === 'field-labels') {
      // Handle double click - create new extraction field
      const objectId = `${obj.type}-${obj.page}-${obj.bbox.join('-')}`;
      const existingField = extractionFields.find(field => field.objectId === objectId);
      
      if (!existingField && obj.type === 'word') {
        // Create new extraction field
        const newFieldId = `field_${Date.now()}`;
        setEditingField(newFieldId);
        setSelectedExtractionField(null);
        
        // Store temporary field data for the editor
        setTempFieldData({
          id: newFieldId,
          objectId: objectId,
          obj: obj
        });
        
        // Reset form fields
        setFieldLabel('');
        setFieldDescription('');
        setFieldRequired(false);
        setFieldValidationRegex('');
        
        console.log('Creating new extraction field for object:', { objectId, text: obj.text, type: obj.type });
      }
    }
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
      const wordObjects = pdfData?.objects?.filter(obj => {
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
      const selectedObjectData = pdfData.objects.filter(obj => {
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
          objectId: field.objectId,
          label: field.label,
          description: field.description,
          required: field.required,
          validationRegex: field.validationRegex,
          source_text: field.obj?.text || '',
          source_type: field.obj?.type || '',
          source_page: field.obj?.page || 0,
          source_bbox: field.obj?.bbox || [0, 0, 0, 0]
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
    if (!editingField || !tempFieldData) return;

    const newField = {
      id: editingField,
      objectId: tempFieldData.objectId,
      label: fieldLabel,
      description: fieldDescription,
      required: fieldRequired,
      validationRegex: fieldValidationRegex || undefined,
      obj: tempFieldData.obj
    };

    console.log('Saving new extraction field:', newField);

    setExtractionFields(prev => [...prev, newField]);
    setEditingField(null);
    setTempFieldData(null);
    setSelectedExtractionField(newField.id);
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
        
        {/* Show the source text being labeled */}
        {tempFieldData && (
          <div className="mb-4 p-3 bg-gray-800 border border-gray-600 rounded">
            <div className="text-xs text-gray-400 mb-1">Source Text:</div>
            <div className="text-sm text-white font-mono">"{ tempFieldData.obj?.text || 'N/A'}"</div>
            <div className="text-xs text-gray-500 mt-1">
              {tempFieldData.obj?.type} • Page {(tempFieldData.obj?.page || 0) + 1}
            </div>
          </div>
        )}
        
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Field Label</label>
            <input
              type="text"
              value={fieldLabel}
              onChange={(e) => setFieldLabel(e.target.value)}
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
          <div className="flex items-center">
            <button
              onClick={() => setSelectedExtractionField(null)}
              className="mr-3 p-1 text-gray-400 hover:text-white"
            >
              ← Back
            </button>
            <h3 className="text-sm font-semibold text-white">Extraction Field</h3>
          </div>
          <button
            onClick={() => handleDeleteExtractionField(field.id)}
            className="p-1 text-red-400 hover:text-red-300"
            title="Delete field"
          >
            🗑️
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
            <label className="block text-xs font-medium text-gray-400 mb-1">Source Text</label>
            <div className="text-sm text-gray-300">"{field.obj?.text || 'N/A'}"</div>
          </div>
        </div>
      </div>
    );
  };

  const getObjectTypeCounts = () => {
    if (!pdfData || !pdfData.objects) return {};
    const counts: { [key: string]: number } = {};
    
    pdfData.objects.forEach(obj => {
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
          onClose();
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
            onClick={onClose}
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

                {/* Extraction Fields Summary */}
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-white mb-2">Extraction Fields</h3>
                  <div className="bg-gray-800 rounded p-3">
                    <div className="text-lg font-semibold text-purple-300">{extractionFields.length}</div>
                    <div className="text-xs text-gray-400">Fields Defined</div>
                  </div>
                </div>

                {/* Instructions */}
                <div className="bg-blue-900/30 border border-blue-700 rounded p-3">
                  <div className="text-xs text-blue-300 font-medium mb-1">Instructions:</div>
                  <div className="text-xs text-blue-200">
                    • Double-click words to create extraction field<br/>
                    • Single-click existing fields to view/edit<br/>
                    • Purple highlighted = has extraction field
                  </div>
                </div>
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

                {pdfData?.error_message && (
                  <div className="mt-4 p-3 bg-red-900 border border-red-700 rounded">
                    <h4 className="text-sm font-semibold text-red-300 mb-1">Error Details</h4>
                    <p className="text-xs text-red-200">{pdfData.error_message}</p>
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
                    objects={pdfData.objects}
                    showObjectOverlays={selectedObjectTypes.size > 0}
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
                    objects={pdfData.objects.filter(obj => obj.type === 'word')} // Only show word objects
                    showObjectOverlays={true}
                    selectedObjectTypes={new Set(['word'])}
                    selectedObjects={new Set()}
                    extractionFields={new Set(extractionFields.map(field => field.objectId))}
                    className="flex-1"
                    onObjectClick={handleObjectClick}
                    onObjectDoubleClick={handleObjectDoubleClick}
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
              : `Double-click words to create extraction fields. Single-click existing fields to view/edit. Fields defined: ${extractionFields.length}`
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
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-sm bg-gray-600 hover:bg-gray-700 disabled:bg-gray-500 disabled:cursor-not-allowed text-white rounded"
            >
              Cancel
            </button>
            {currentStep === 'object-selection' ? (
              <button
                onClick={handleNextStep}
                disabled={!templateName.trim() || selectedObjects.size === 0}
                className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded"
              >
                Next: Assign Labels →
              </button>
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

  // Use portal to render at the root level
  const rootElement = document.getElementById('root');
  if (!rootElement) return null;
  
  return createPortal(modalContent, rootElement);
}