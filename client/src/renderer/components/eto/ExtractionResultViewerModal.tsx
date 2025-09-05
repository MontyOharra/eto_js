import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { PdfViewer } from '../pdf/PdfViewer';
import { apiClient } from '../services/api';

interface ExtractionResultViewerModalProps {
  runId: string | null;
  onClose: () => void;
}

interface ExtractionResultData {
  id: number;
  status: string;
  matched_template_id: number;
  template_name: string;
  pdf_id: number;
  filename: string;
  page_count: number;
  extracted_data: Record<string, any>;
  extraction_fields: Array<{
    id: string;
    label: string;
    description: string;
    boundingBox: [number, number, number, number];
    page: number;
    extracted_value: any;
  }>;
  email: {
    subject: string;
    sender_email: string;
    received_date: string;
  };
}

export function ExtractionResultViewerModal({ runId, onClose }: ExtractionResultViewerModalProps) {
  const [extractionData, setExtractionData] = useState<ExtractionResultData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedField, setSelectedField] = useState<string | null>(null);

  // Load extraction data when modal opens
  useEffect(() => {
    if (runId) {
      loadExtractionData(runId);
    }
  }, [runId]);

  const loadExtractionData = async (runId: string) => {
    setLoading(true);
    setError(null);
    
    try {
      // We'll need to create this API endpoint
      const response = await apiClient.getExtractionResults(parseInt(runId));
      setExtractionData(response);
    } catch (err) {
      console.error('Error loading extraction results:', err);
      setError(err instanceof Error ? err.message : 'Failed to load extraction results');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setExtractionData(null);
    setSelectedField(null);
    setError(null);
    onClose();
  };

  const getSelectedFieldDetails = () => {
    if (!selectedField || !extractionData) return null;
    return extractionData.extraction_fields.find(field => field.id === selectedField);
  };

  if (!runId) return null;

  return createPortal(
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999]">
      <div className="bg-gray-800 border border-gray-700 rounded-lg w-[95vw] h-[90vh] max-w-7xl flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div>
            <h2 className="text-xl font-semibold text-white">
              {extractionData ? `Extraction Results: ${extractionData.filename}` : 'Loading Extraction Results...'}
            </h2>
            {extractionData && (
              <p className="text-sm text-gray-400 mt-1">
                Template: {extractionData.template_name} • 
                Status: <span className="text-green-400">Success</span> • 
                {extractionData.extraction_fields.length} fields extracted
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
              <p className="text-gray-400">Loading extraction results...</p>
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
                  <h3 className="text-red-400 font-medium">Error Loading Results</h3>
                  <p className="text-gray-400 text-sm mt-1">{error}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {extractionData && (
          <>
            {/* Main Content */}
            <div className="flex-1 flex overflow-hidden">
              {/* Left Sidebar - Extracted Fields */}
              <div className="w-80 border-r border-gray-700 flex flex-col overflow-hidden">
                <div className="p-4 border-b border-gray-700">
                  <h3 className="font-medium text-gray-300 mb-3">Extracted Fields</h3>
                  {extractionData.extraction_fields.length === 0 ? (
                    <p className="text-sm text-gray-500">No fields extracted</p>
                  ) : (
                    <div className="space-y-2">
                      {extractionData.extraction_fields.map((field) => (
                        <div
                          key={field.id}
                          onClick={() => setSelectedField(
                            selectedField === field.id ? null : field.id
                          )}
                          className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                            selectedField === field.id
                              ? 'border-blue-400 bg-blue-900/20'
                              : 'border-gray-600 hover:border-gray-500 hover:bg-gray-800/50'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <h4 className="font-medium text-sm text-blue-300">{field.label}</h4>
                            <span className="text-xs text-green-400">✓ Extracted</span>
                          </div>
                          {field.description && (
                            <p className="text-xs text-gray-400 mb-2">{field.description}</p>
                          )}
                          <div className="text-sm text-white mb-1 font-mono bg-gray-700 px-2 py-1 rounded">
                            {field.extracted_value || 'No value'}
                          </div>
                          <div className="text-xs text-gray-500">
                            Page {field.page + 1} • Raw extracted value
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Field Details Panel */}
                {selectedField && getSelectedFieldDetails() && (
                  <div className="flex-1 overflow-y-auto p-4 border-t border-gray-700">
                    <h3 className="font-medium text-gray-300 mb-3">Field Details</h3>
                    {(() => {
                      const field = getSelectedFieldDetails()!;
                      return (
                        <div className="space-y-3">
                          <div>
                            <h4 className="text-sm font-medium text-blue-300 mb-1">Field: {field.label}</h4>
                            {field.description && (
                              <p className="text-xs text-gray-400 mb-2">{field.description}</p>
                            )}
                          </div>
                          
                          <div>
                            <h4 className="text-sm font-medium text-blue-300 mb-1">Location</h4>
                            <div className="text-sm text-gray-300">
                              Page {field.page + 1}<br/>
                              Coordinates: ({field.boundingBox[0].toFixed(1)}, {field.boundingBox[1].toFixed(1)}) → ({field.boundingBox[2].toFixed(1)}, {field.boundingBox[3].toFixed(1)})
                            </div>
                          </div>
                          
                          <div>
                            <h4 className="text-sm font-medium text-green-300 mb-1">Extracted Value</h4>
                            <div className="text-sm text-white bg-gray-700 p-3 rounded font-mono border">
                              {field.extracted_value || 'No value extracted'}
                            </div>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                )}

                {/* Raw Extracted Data Panel */}
                {!selectedField && (
                  <div className="flex-1 overflow-y-auto p-4 border-t border-gray-700">
                    <h3 className="font-medium text-gray-300 mb-3">Raw Extracted Data</h3>
                    <div className="bg-gray-800 p-3 rounded font-mono text-sm text-gray-300 overflow-auto">
                      <pre>{JSON.stringify(extractionData.extracted_data, null, 2)}</pre>
                    </div>
                    <p className="text-xs text-gray-500 mt-2">Click on a field above to see specific extraction details</p>
                  </div>
                )}
              </div>

              {/* PDF Viewer */}
              <div className="flex-1">
                <PdfViewer
                  pdfId={extractionData.pdf_id}
                  extractionFields={extractionData.extraction_fields}
                  selectedExtractionField={selectedField}
                  isReadOnly={true}
                />
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-gray-700 bg-gray-800">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-400">
                  Email: {extractionData.email.subject} • 
                  From: {extractionData.email.sender_email} • 
                  Processed: {new Date(extractionData.email.received_date).toLocaleDateString()}
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