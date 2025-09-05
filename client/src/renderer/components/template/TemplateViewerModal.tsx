import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { PdfViewer } from '../pdf/PdfViewer';
import { apiClient } from '../services/api';

interface TemplateViewerModalProps {
  templateId: number | null;
  onClose: () => void;
}

interface TemplateViewData {
  id: number;
  name: string;
  description?: string;
  status: "active" | "archived" | "draft";
  is_complete: boolean;
  coverage_threshold: number;
  usage_count: number;
  last_used_at?: string;
  success_rate?: number;
  version: number;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
  extraction_rules_count: number;
  signature_object_count: number;
  
  // PDF and objects data
  sample_pdf_id: number;
  sample_pdf_filename: string;
  sample_pdf_page_count: number;
  pdf_objects: any[];
  signature_objects: any[]; // Static objects that define the template
  extraction_fields: Array<{
    id: string;
    boundingBox: [number, number, number, number];
    page: number;
    label: string;
    description: string;
    required: boolean;
    validationRegex?: string;
  }>;
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

export function TemplateViewerModal({ templateId, onClose }: TemplateViewerModalProps) {
  const [templateData, setTemplateData] = useState<TemplateViewData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedObjectTypes, setSelectedObjectTypes] = useState<Set<string>>(new Set(['word', 'text_line', 'rect']));
  const [selectedExtractionField, setSelectedExtractionField] = useState<string | null>(null);

  // Load template data when modal opens
  useEffect(() => {
    if (!templateId) {
      setTemplateData(null);
      setError(null);
      return;
    }

    const loadTemplateData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        console.log(`Loading template data for template ID: ${templateId}`);
        const response = await apiClient.getTemplateViewData(templateId);
        
        if (response.success) {
          setTemplateData(response.result);
          console.log('Template data loaded:', response.result);
        } else {
          setError(response.error || 'Failed to load template data');
        }
      } catch (err: any) {
        console.error('Error loading template data:', err);
        setError(err.message || 'Failed to load template data');
      } finally {
        setLoading(false);
      }
    };

    loadTemplateData();
  }, [templateId]);

  // Don't render if no templateId
  if (!templateId) return null;

  const handleClose = () => {
    setTemplateData(null);
    setError(null);
    setSelectedExtractionField(null);
    onClose();
  };

  const getVisibleObjects = () => {
    if (!templateData) return [];
    
    // Return only the signature objects (template definition objects) filtered by selected types
    const visibleSignatureObjects = templateData.signature_objects.filter(obj => {
      const objType = obj.type || obj.object_type;
      return selectedObjectTypes.has(objType);
    });
    
    console.log('Signature Objects Debug:', {
      total_signature_objects: templateData.signature_objects.length,
      visible_signature_objects: visibleSignatureObjects.length,
      selected_types: Array.from(selectedObjectTypes),
      sample_signature_object: templateData.signature_objects[0]
    });
    
    return visibleSignatureObjects;
  };

  const getVisibleExtractionFields = () => {
    if (!templateData) return [];
    // Always show extraction fields since we removed tabs
    return templateData.extraction_fields;
  };

  const objectTypeCounts = templateData ? templateData.signature_objects.reduce((counts: Record<string, number>, obj: any) => {
    const objType = obj.type || obj.object_type;
    counts[objType] = (counts[objType] || 0) + 1;
    return counts;
  }, {}) : {};

  return createPortal(
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999]">
      <div className="bg-gray-800 border border-gray-700 rounded-lg w-[95vw] h-[90vh] max-w-7xl flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div>
            <h2 className="text-xl font-semibold text-blue-300">
              {templateData ? `View Template: ${templateData.name}` : 'Loading Template...'}
            </h2>
            {templateData && (
              <p className="text-sm text-gray-400 mt-1">
                {templateData.description || 'No description'} • 
                Status: <span className={`${templateData.status === 'active' ? 'text-green-400' : templateData.status === 'draft' ? 'text-yellow-400' : 'text-gray-400'}`}>
                  {templateData.status}
                </span> • 
                {templateData.signature_object_count} signature objects • 
                {templateData.extraction_rules_count} extraction fields
              </p>
            )}
          </div>
          <button
            onClick={handleClose}
            className="p-2 text-gray-400 hover:text-white transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {loading && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400 mx-auto mb-4"></div>
              <p className="text-gray-400">Loading template data...</p>
            </div>
          </div>
        )}

        {error && (
          <div className="flex-1 flex items-center justify-center">
            <div className="bg-red-900/20 border border-red-700 rounded-lg p-6 max-w-md">
              <div className="flex items-center">
                <svg className="w-6 h-6 text-red-400 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div>
                  <h3 className="text-red-400 font-medium">Error Loading Template</h3>
                  <p className="text-gray-400 text-sm mt-1">{error}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {templateData && (
          <>
            {/* Main Content */}
            <div className="flex-1 flex overflow-hidden">
              {/* Left Sidebar */}
              <div className="w-80 border-r border-gray-700 flex flex-col overflow-hidden">
                <div className="p-4 border-b border-gray-700">
                  <h3 className="font-medium text-gray-300 mb-3">Signature Objects</h3>
                  <div className="space-y-2">
                    {Object.entries(OBJECT_TYPE_NAMES).map(([type, name]) => {
                      const count = objectTypeCounts[type] || 0;
                      const isSelected = selectedObjectTypes.has(type);
                      
                      if (count === 0) return null;
                      
                      return (
                        <div key={type} className="flex items-center">
                          <button
                            onClick={() => {
                              const newTypes = new Set(selectedObjectTypes);
                              if (isSelected) {
                                newTypes.delete(type);
                              } else {
                                newTypes.add(type);
                              }
                              setSelectedObjectTypes(newTypes);
                            }}
                            className={`flex-1 flex items-center justify-between p-2 text-xs rounded transition-colors ${
                              isSelected ? 'bg-gray-700 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                            }`}
                          >
                            <div className="flex items-center space-x-2">
                              <div
                                className="w-3 h-3 rounded"
                                style={{ backgroundColor: OBJECT_TYPE_COLORS[type as keyof typeof OBJECT_TYPE_COLORS] }}
                              ></div>
                              <span>{name}</span>
                            </div>
                            <span className="font-medium">{count}</span>
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Extraction Fields List */}
                <div className="flex-1 overflow-y-auto p-4">
                  <h3 className="font-medium text-gray-300 mb-3">Extraction Fields</h3>
                  {templateData.extraction_fields.length === 0 ? (
                    <p className="text-sm text-gray-500">No extraction fields defined</p>
                  ) : (
                    <div className="space-y-2">
                      {templateData.extraction_fields.map((field) => (
                        <div
                          key={field.id}
                          onClick={() => setSelectedExtractionField(
                            selectedExtractionField === field.id ? null : field.id
                          )}
                          className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                            selectedExtractionField === field.id
                              ? 'border-purple-400 bg-purple-900/20'
                              : 'border-gray-600 hover:border-gray-500 hover:bg-gray-800/50'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <h4 className="font-medium text-sm text-purple-300">{field.label}</h4>
                            {field.required && (
                              <span className="text-xs text-red-400">Required</span>
                            )}
                          </div>
                          {field.description && (
                            <p className="text-xs text-gray-400 mb-2">{field.description}</p>
                          )}
                          <div className="text-xs text-gray-500">
                            Page {field.page + 1} • 
                            ({field.boundingBox[0].toFixed(1)}, {field.boundingBox[1].toFixed(1)}) → 
                            ({field.boundingBox[2].toFixed(1)}, {field.boundingBox[3].toFixed(1)})
                          </div>
                          {field.validationRegex && (
                            <div className="text-xs text-gray-500 mt-1">
                              Regex: <code className="bg-gray-700 px-1 rounded">{field.validationRegex}</code>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* PDF Viewer */}
              <div className="flex-1">
                <PdfViewer
                  pdfId={templateData.sample_pdf_id}
                  objects={getVisibleObjects()}
                  extractionFields={getVisibleExtractionFields()}
                  selectedExtractionField={selectedExtractionField}
                  isReadOnly={true}
                />
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-gray-700 bg-gray-800">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-400">
                  Template created by {templateData.created_by || 'Unknown'} • 
                  Used {templateData.usage_count} times • 
                  Success rate: {templateData.success_rate ? `${(templateData.success_rate * 100).toFixed(1)}%` : 'N/A'}
                </div>
                <button
                  onClick={handleClose}
                  className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>,
    document.body
  );
}