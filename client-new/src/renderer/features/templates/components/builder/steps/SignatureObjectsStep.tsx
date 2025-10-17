import { useState, useEffect } from 'react';
import { SignatureObject } from '../../../types';
import { useMockPdfApi } from '../../../../pdf-files/mocks/useMockPdfApi';
import { PdfViewer } from '../../../../../shared/components/pdf';

interface SignatureObjectsStepProps {
  pdfFileId: number;
  templateName: string;
  templateDescription: string;
  signatureObjects: SignatureObject[];
  onTemplateNameChange: (name: string) => void;
  onTemplateDescriptionChange: (description: string) => void;
  onSignatureObjectsChange: (objects: SignatureObject[]) => void;
}

// Object type configurations
const OBJECT_TYPE_NAMES: Record<string, string> = {
  text_word: 'Text Words',
  text_line: 'Text Lines',
  graphic_rect: 'Rectangles',
  graphic_line: 'Lines',
  graphic_curve: 'Curves',
  image: 'Images',
  table: 'Tables',
};

const OBJECT_TYPE_COLORS: Record<string, string> = {
  text_word: '#ff0000',
  text_line: '#00ff00',
  graphic_rect: '#0000ff',
  graphic_line: '#ffff00',
  graphic_curve: '#ff00ff',
  image: '#00ffff',
  table: '#ffa500',
};

export function SignatureObjectsStep({
  pdfFileId,
  templateName,
  templateDescription,
  signatureObjects,
  onTemplateNameChange,
  onTemplateDescriptionChange,
  onSignatureObjectsChange,
}: SignatureObjectsStepProps) {
  const [pdfObjects, setPdfObjects] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [pdfUrl, setPdfUrl] = useState<string>('');

  // Load PDF objects on mount
  useEffect(() => {
    loadPdfObjects();
  }, [pdfFileId]);

  const loadPdfObjects = async () => {
    setLoading(true);
    setError(null);

    try {
      const objectsData = await useMockPdfApi.getPdfObjects(pdfFileId);
      setPdfObjects(objectsData);

      // Set PDF URL
      const url = useMockPdfApi.getPdfDownloadUrl(pdfFileId);
      setPdfUrl(url);
    } catch (err) {
      console.error('Failed to load PDF objects:', err);
      setError(err instanceof Error ? err.message : 'Failed to load PDF objects');
    } finally {
      setLoading(false);
    }
  };

  const handleTypeToggle = (type: string) => {
    const newSelected = new Set(selectedTypes);
    if (newSelected.has(type)) {
      newSelected.delete(type);
    } else {
      newSelected.add(type);
    }
    setSelectedTypes(newSelected);
  };

  const handleShowAll = () => {
    if (!pdfObjects) return;
    const allTypes = Object.keys(OBJECT_TYPE_NAMES).filter((type) => {
      const key = type === 'text_word' ? 'text_words' : type === 'graphic_rect' ? 'graphic_rects' : type === 'graphic_line' ? 'graphic_lines' : type === 'graphic_curve' ? 'graphic_curves' : type === 'text_line' ? 'text_lines' : type === 'image' ? 'images' : 'tables';
      return pdfObjects.objects[key]?.length > 0;
    });
    setSelectedTypes(new Set(allTypes));
  };

  const handleHideAll = () => {
    setSelectedTypes(new Set());
  };

  // Get counts for each type
  const getTypeCounts = () => {
    if (!pdfObjects) return {};

    return {
      text_word: pdfObjects.objects.text_words?.length || 0,
      text_line: pdfObjects.objects.text_lines?.length || 0,
      graphic_rect: pdfObjects.objects.graphic_rects?.length || 0,
      graphic_line: pdfObjects.objects.graphic_lines?.length || 0,
      graphic_curve: pdfObjects.objects.graphic_curves?.length || 0,
      image: pdfObjects.objects.images?.length || 0,
      table: pdfObjects.objects.tables?.length || 0,
    };
  };

  const typeCounts = getTypeCounts();

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-white">Loading PDF objects...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-400 mb-4">{error}</div>
          <button
            onClick={loadPdfObjects}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex">
      {/* Left Sidebar - Object Type Toggles */}
      <div className="w-80 flex-shrink-0 bg-gray-900 border-r border-gray-700 p-4 overflow-y-auto">
        <h3 className="text-sm font-semibold text-white mb-3">Object Visibility</h3>

        {/* Show/Hide All Buttons */}
        <div className="space-y-2 mb-4">
          <button
            onClick={handleShowAll}
            className="w-full px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded"
          >
            Show All Types
          </button>
          <button
            onClick={handleHideAll}
            className="w-full px-3 py-1 text-xs bg-gray-600 hover:bg-gray-700 text-white rounded"
          >
            Hide All Types
          </button>
        </div>

        {/* Object Type Buttons */}
        <div className="space-y-2">
          {Object.entries(OBJECT_TYPE_NAMES).map(([type, label]) => {
            const count = typeCounts[type] || 0;
            const isSelected = selectedTypes.has(type);

            if (count === 0) return null;

            return (
              <div key={type} className="flex items-center">
                <button
                  onClick={() => handleTypeToggle(type)}
                  className={`flex-1 flex items-center justify-between p-2 text-xs rounded transition-colors ${
                    isSelected
                      ? 'bg-gray-700 text-white'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <div
                      className="w-3 h-3 rounded"
                      style={{ backgroundColor: OBJECT_TYPE_COLORS[type] }}
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

      {/* Right Side - PDF Viewer */}
      <div className="flex-1 overflow-hidden">
        {pdfUrl && (
          <PdfViewer pdfUrl={pdfUrl}>
            <PdfViewer.Canvas pdfUrl={pdfUrl}>
              {/* TODO: Add object overlays here */}
            </PdfViewer.Canvas>
            <PdfViewer.InfoPanel position="top-right" filename={`${pdfFileId}.pdf`} />
            <PdfViewer.Controls position="bottom-center" />
          </PdfViewer>
        )}
      </div>
    </div>
  );
}
