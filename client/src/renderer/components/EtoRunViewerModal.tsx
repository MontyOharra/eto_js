import React, { useState, useEffect } from 'react';
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

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg w-full h-full max-w-7xl max-h-[95vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-white">
              PDF Viewer - {pdfData?.filename || 'Loading...'}
            </h2>
            {pdfData && (
              <div className="text-sm text-gray-400 mt-1">
                <div>From: {pdfData.email.sender_email}</div>
                <div>Subject: {pdfData.email.subject}</div>
                <div>Received: {formatDate(pdfData.email.received_date)}</div>
                <div>Size: {formatFileSize(pdfData.file_size)} • {pdfData.page_count} pages • {pdfData.object_count} objects</div>
                <div>Status: <span className={`${pdfData.status === 'success' ? 'text-green-400' : pdfData.status === 'error' ? 'text-red-400' : 'text-yellow-400'}`}>
                  {pdfData.status}
                </span></div>
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white p-2"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar - Object Type Controls */}
          <div className="w-64 bg-gray-900 border-r border-gray-700 p-4 overflow-y-auto">
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
          <div className="flex-1 flex flex-col">
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
}