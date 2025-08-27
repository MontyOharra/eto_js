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

const OBJECT_TYPE_LABELS = {
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

export function TemplateBuilderModal({ runId, onClose, onSave }: TemplateBuilderModalProps) {
  const [pdfData, setPdfData] = useState<EtoRunPdfData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedObjectTypes, setSelectedObjectTypes] = useState<Set<string>>(new Set());
  const [selectedObjects, setSelectedObjects] = useState<Set<string>>(new Set()); // Track individual object selection
  const [templateName, setTemplateName] = useState<string>('');
  const [templateDescription, setTemplateDescription] = useState<string>('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (runId) {
      // Small delay to ensure modal is fully mounted before loading PDF
      const timeoutId = setTimeout(() => {
        fetchPdfData();
      }, 100);
      
      return () => {
        clearTimeout(timeoutId);
      };
    }
    
    // Cleanup function to handle modal unmounting
    return () => {
      // Clear states when modal is closing to prevent stale renders
      setPdfData(null);
      setError(null);
      setLoading(false);
    };
  }, [runId]);

  const fetchPdfData = async () => {
    if (!runId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.getEtoRunPdfData(runId);
      
      // Parse objects from raw_extracted_data
      let objects: any[] = [];
      if (response.raw_extracted_data) {
        try {
          const extractedData = JSON.parse(response.raw_extracted_data);
          console.log('Template Builder - Extracted data keys:', Object.keys(extractedData));
          
          if (extractedData.pdf_objects && Array.isArray(extractedData.pdf_objects)) {
            objects = extractedData.pdf_objects;
          }
        } catch (e) {
          console.error('Error parsing raw_extracted_data:', e);
        }
      }
      
      console.log('Template Builder - PDF Data:', {
        eto_run_id: response.eto_run_id,
        objects_found: objects.length,
        sample_objects: objects.slice(0, 2)
      });
      
      // Add objects to the response
      const pdfDataWithObjects = {
        ...response,
        objects: objects,
        object_count: objects.length
      };
      
      setPdfData(pdfDataWithObjects);
      
      // Initialize with all object types selected for viewing
      const objectTypes = new Set(objects.map((obj: any) => obj.type));
      setSelectedObjectTypes(objectTypes);
      
      // Auto-generate template name from filename
      if (pdfDataWithObjects.filename && !templateName) {
        const baseName = pdfDataWithObjects.filename.replace(/\.[^/.]+$/, ""); // Remove extension
        setTemplateName(`${baseName} Template`);
      }
      
    } catch (err: any) {
      console.error('Error fetching PDF data:', err);
      setError(err.response?.data?.error || 'Failed to load PDF data');
    } finally {
      setLoading(false);
    }
  };

  const handleObjectTypeToggle = (objectType: string) => {
    const newSelected = new Set(selectedObjectTypes);
    if (newSelected.has(objectType)) {
      newSelected.delete(objectType);
    } else {
      newSelected.add(objectType);
    }
    setSelectedObjectTypes(newSelected);
  };

  const handleShowAllTypes = () => {
    if (pdfData) {
      const allTypes = new Set(pdfData.objects.map(obj => obj.type));
      setSelectedObjectTypes(allTypes);
    }
  };

  const handleHideAllTypes = () => {
    setSelectedObjectTypes(new Set());
  };

  const handleObjectClick = (object: any) => {
    const objectId = `${object.type}-${object.page}-${object.bbox.join('-')}`;
    const newSelected = new Set(selectedObjects);
    
    if (newSelected.has(objectId)) {
      newSelected.delete(objectId);
    } else {
      newSelected.add(objectId);
    }
    
    setSelectedObjects(newSelected);
    console.log('Template Builder - Object clicked:', {
      object: object,
      objectId: objectId,
      totalSelected: newSelected.size
    });
  };

  const handleSave = async () => {
    if (!pdfData) return;
    
    setSaving(true);
    setError(null);
    
    try {
      // Get the actual selected object data
      const selectedObjectData = pdfData.objects.filter(obj => {
        const objectId = `${obj.type}-${obj.page}-${obj.bbox.join('-')}`;
        return selectedObjects.has(objectId);
      });
      
      const templateData = {
        name: templateName,
        description: templateDescription,
        source_pdf_id: pdfData.pdf_id,
        source_eto_run_id: pdfData.eto_run_id,
        filename: pdfData.filename,
        selected_objects: selectedObjectData
      };
      
      console.log('Template Builder - Saving template:', {
        selectedCount: selectedObjectData.length,
        templateData: templateData
      });
      
      // Call API to create template
      const result = await apiClient.createTemplate(templateData);
      
      console.log('Template created successfully:', result);
      
      // Notify parent component
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

  const getObjectTypeCounts = () => {
    if (!pdfData) return {};
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
        // Close modal if clicking the backdrop
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
                Select Objects & Save Template
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
            className="text-gray-400 hover:text-white p-1 ml-3 flex-shrink-0"
            title="Close"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden" style={{ minHeight: 0, minWidth: 0 }}>
          {/* Left Sidebar - Template Info & Object Controls */}
          <div className="w-80 flex-shrink-0 bg-gray-900 border-r border-gray-700 p-4 overflow-y-auto">
            {/* Template Information */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-white mb-3">Template Information</h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1">Template Name</label>
                  <input
                    type="text"
                    value={templateName}
                    onChange={(e) => setTemplateName(e.target.value)}
                    className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
                    placeholder="Enter template name"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1">Description (Optional)</label>
                  <textarea
                    value={templateDescription}
                    onChange={(e) => setTemplateDescription(e.target.value)}
                    rows={2}
                    className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none resize-none"
                    placeholder="Describe this template..."
                  />
                </div>
              </div>
            </div>

            {/* Selection Summary */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-white mb-2">Selection Summary</h3>
              <div className="bg-gray-800 rounded p-3">
                <div className="text-lg font-semibold text-blue-300">{selectedObjects.size}</div>
                <div className="text-xs text-gray-400">Objects Selected</div>
              </div>
            </div>

            {/* Object Type Visibility Controls */}
            <div>
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
                {Object.entries(OBJECT_TYPE_LABELS).map(([type, label]) => {
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
            </div>

            {pdfData?.error_message && (
              <div className="mt-4 p-3 bg-red-900 border border-red-700 rounded">
                <h4 className="text-sm font-semibold text-red-300 mb-1">Error Details</h4>
                <p className="text-xs text-red-200">{pdfData.error_message}</p>
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
              <PdfViewer
                key={`pdf-${pdfData.pdf_id}-${pdfData.eto_run_id}`}
                pdfUrl={pdfUrl}
                objects={pdfData.objects}
                showObjectOverlays={selectedObjectTypes.size > 0}
                selectedObjectTypes={selectedObjectTypes}
                selectedObjects={selectedObjects} // Pass selected objects for highlighting
                className="flex-1"
                onObjectClick={handleObjectClick} // Enable object selection
              />
            )}
          </div>
        </div>

        {/* Footer - Action Buttons */}
        <div className="flex items-center justify-between p-4 border-t border-gray-700">
          <div className="text-sm text-gray-400">
            Click on objects in the PDF to select them for your template. Selected: {selectedObjects.size} objects
          </div>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-sm bg-gray-600 hover:bg-gray-700 disabled:bg-gray-500 disabled:cursor-not-allowed text-white rounded"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!templateName.trim() || selectedObjects.size === 0 || saving}
              className="px-4 py-2 text-sm bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded"
            >
              {saving ? 'Saving Template...' : 'Save Template'}
            </button>
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