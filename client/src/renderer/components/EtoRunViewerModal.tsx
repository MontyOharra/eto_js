import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { PdfViewer } from './PdfViewer';
import { apiClient } from '../services/api';

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

interface EtoRunViewerModalProps {
  runId: string | null;
  onClose: () => void;
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

export function EtoRunViewerModal({ runId, onClose }: EtoRunViewerModalProps) {
  const [pdfData, setPdfData] = useState<EtoRunPdfData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedObjectTypes, setSelectedObjectTypes] = useState<Set<string>>(new Set());
  const [showAllObjectTypes, setShowAllObjectTypes] = useState(true);
  // Remove useApi hook declaration

  useEffect(() => {
    if (runId) {
      fetchPdfData();
    }
  }, [runId]);

  const fetchPdfData = async () => {
    if (!runId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.getEtoRunPdfData(runId);
      setPdfData(response);
      
      // Initialize with all object types selected
      const objectTypes = new Set(response.objects.map((obj: any) => obj.type));
      setSelectedObjectTypes(objectTypes);
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
    setShowAllObjectTypes(false);
  };

  const handleShowAllTypes = () => {
    if (pdfData) {
      const allTypes = new Set(pdfData.objects.map(obj => obj.type));
      setSelectedObjectTypes(allTypes);
      setShowAllObjectTypes(true);
    }
  };

  const handleHideAllTypes = () => {
    setSelectedObjectTypes(new Set());
    setShowAllObjectTypes(false);
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
                {pdfData?.filename || 'Loading...'}
              </h2>
              {pdfData && (
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  pdfData.status === 'success' ? 'bg-green-900 text-green-300' : 
                  pdfData.status === 'error' ? 'bg-red-900 text-red-300' : 'bg-yellow-900 text-yellow-300'
                }`}>
                  {pdfData.status}
                </span>
              )}
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
          {/* Sidebar - Object Type Controls */}
          <div className="w-64 flex-shrink-0 bg-gray-900 border-r border-gray-700 p-4 overflow-y-auto">
            <h3 className="text-sm font-semibold text-white mb-3">Object Overlays</h3>
            
            <div className="space-y-2 mb-4">
              <button
                onClick={handleShowAllTypes}
                className="w-full px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded"
              >
                Show All
              </button>
              <button
                onClick={handleHideAllTypes}
                className="w-full px-3 py-1 text-xs bg-gray-600 hover:bg-gray-700 text-white rounded"
              >
                Hide All
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
                pdfUrl={pdfUrl}
                objects={pdfData.objects}
                showObjectOverlays={selectedObjectTypes.size > 0}
                selectedObjectTypes={selectedObjectTypes}
                className="flex-1"
                onObjectClick={(object) => {
                  console.log('Object clicked:', object);
                  // TODO: Add object inspection or selection logic
                }}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );

  // Use portal to render at the root level to maintain styling context
  const rootElement = document.getElementById('root');
  if (!rootElement) return null;
  
  return createPortal(modalContent, rootElement);
}