/**
 * Template Detail Modal
 * Version-based read-only viewer for template details
 * Displays signature objects, extraction fields, and pipeline for each version
 */

import { useEffect, useState, useMemo } from 'react';
import { useTemplatesApi } from '../../hooks';
import {
  TemplateDetail,
  TemplateVersionDetail,
  PdfObjects,
} from '../../types';
import { TemplateStatusBadge } from '../ui/TemplateStatusBadge';
import { usePdfData } from '../../../pdf-files/hooks/usePdfData';
import { PdfViewer } from '../../../../shared/components/pdf';
import { usePdfViewer } from '../../../../shared/components/pdf/PdfViewer/PdfViewerContext';

interface TemplateDetailModalProps {
  isOpen: boolean;
  templateId: number | null;
  onClose: () => void;
  onEdit?: (templateId: number) => void;
}

type ViewStep = 'signature-objects' | 'extraction-fields' | 'pipeline';

// Simple viewer stepper (numbers only, no testing step)
const VIEWER_STEPS = [
  { id: 'signature-objects' as ViewStep, number: 1, label: 'Signature Objects' },
  { id: 'extraction-fields' as ViewStep, number: 2, label: 'Extraction Fields' },
  { id: 'pipeline' as ViewStep, number: 3, label: 'Pipeline' },
];

function TemplateViewerStepper({ currentStep }: { currentStep: ViewStep }) {
  return (
    <div className="flex items-center space-x-3">
      {VIEWER_STEPS.map((step, index) => {
        const isActive = step.id === currentStep;

        return (
          <div key={step.id} className="flex items-center">
            {/* Step Circle */}
            <div className="flex items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-400'
                }`}
              >
                {step.number}
              </div>
              <span
                className={`ml-2 text-sm font-medium ${
                  isActive ? 'text-white' : 'text-gray-400'
                }`}
              >
                {step.label}
              </span>
            </div>

            {/* Divider */}
            {index < VIEWER_STEPS.length - 1 && (
              <div className="w-12 h-0.5 bg-gray-700 mx-3"></div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function TemplateDetailModal({
  isOpen,
  templateId,
  onClose,
  onEdit,
}: TemplateDetailModalProps) {
  const { getTemplateDetail, getTemplateVersionDetail, isLoading } = useTemplatesApi();

  // Template and version state
  const [template, setTemplate] = useState<TemplateDetail | null>(null);
  const [currentVersionIndex, setCurrentVersionIndex] = useState<number>(0);
  const [versionDetail, setVersionDetail] = useState<TemplateVersionDetail | null>(null);

  // UI state
  const [currentStep, setCurrentStep] = useState<ViewStep>('signature-objects');
  const [error, setError] = useState<string | null>(null);

  // PDF data - fetch once using source_pdf_id from version detail
  const { data: pdfData, isLoading: pdfLoading, error: pdfError } = usePdfData(
    versionDetail?.source_pdf_id ?? null
  );

  // Fetch template when modal opens
  useEffect(() => {
    if (isOpen && templateId) {
      loadTemplate();
    } else {
      // Reset state when modal closes
      resetState();
    }
  }, [isOpen, templateId]);

  // Fetch version detail when version changes
  useEffect(() => {
    if (template && template.versions.length > 0) {
      const versionId = template.versions[currentVersionIndex].version_id;
      loadVersionDetail(versionId);
    }
  }, [currentVersionIndex, template]);

  const loadTemplate = async () => {
    if (!templateId) return;

    setError(null);
    try {
      // Fetch template details (includes versions list)
      const templateData = await getTemplateDetail(templateId);
      setTemplate(templateData);

      // Find the current version index
      const currentIdx = templateData.versions.findIndex(
        (v) => v.version_id === templateData.current_version_id
      );
      setCurrentVersionIndex(currentIdx >= 0 ? currentIdx : 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load template');
    }
  };

  const loadVersionDetail = async (versionId: number) => {
    setError(null);
    try {
      const detail = await getTemplateVersionDetail(versionId);
      setVersionDetail(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load version details');
    }
  };

  const resetState = () => {
    setTemplate(null);
    setCurrentVersionIndex(0);
    setVersionDetail(null);
    setCurrentStep('signature-objects');
    setError(null);
  };

  const handlePreviousVersion = () => {
    if (currentVersionIndex > 0) {
      setCurrentVersionIndex(currentVersionIndex - 1);
    }
  };

  const handleNextVersion = () => {
    if (template && currentVersionIndex < template.versions.length - 1) {
      setCurrentVersionIndex(currentVersionIndex + 1);
    }
  };

  const handleNext = () => {
    if (currentStep === 'signature-objects') {
      setCurrentStep('extraction-fields');
    } else if (currentStep === 'extraction-fields') {
      setCurrentStep('pipeline');
    }
  };

  const handleBack = () => {
    if (currentStep === 'extraction-fields') {
      setCurrentStep('signature-objects');
    } else if (currentStep === 'pipeline') {
      setCurrentStep('extraction-fields');
    }
  };

  if (!isOpen) return null;

  const currentVersion = template?.versions[currentVersionIndex];
  const pdfUrl = pdfData?.url || '';
  const pdfObjects = pdfData?.objectsData;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-lg shadow-2xl w-full max-w-[95vw] h-[95vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div className="flex items-center space-x-4">
            <h2 className="text-2xl font-bold text-white">
              {template?.name || 'Template Details'}
            </h2>
            {template && <TemplateStatusBadge status={template.status} />}
          </div>

          {/* Version Navigation */}
          {template && template.versions.length > 0 && currentVersion && versionDetail && (
            <div className="flex items-center space-x-4">
              <button
                onClick={handleNextVersion}
                disabled={currentVersionIndex === template.versions.length - 1}
                className="px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded transition-colors"
                title="Decrement version"
              >
                ←
              </button>
              <div className="text-center">
                <div className="text-sm font-medium text-white">
                  Version {currentVersion.version_number} of {template.versions.length}
                </div>
                <div className="text-xs text-gray-400 flex items-center space-x-2">
                  {versionDetail.is_current && (
                    <span className="px-2 py-0.5 bg-blue-900 text-blue-300 rounded text-xs">
                      Current
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={handlePreviousVersion}
                disabled={currentVersionIndex === 0}
                className="px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded transition-colors"
                title="Increment version"
              >
                →
              </button>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center space-x-2">
            {onEdit && template && (
              <button
                onClick={() => onEdit(template.id)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
              >
                Edit Template
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors font-medium"
            >
              Close
            </button>
          </div>
        </div>

        {/* Loading State */}
        {(isLoading || pdfLoading) && (
          <div className="flex items-center justify-center p-12">
            <div className="text-gray-400">
              {pdfLoading ? 'Loading PDF...' : 'Loading template details...'}
            </div>
          </div>
        )}

        {/* Error State */}
        {(error || pdfError) && (
          <div className="p-6">
            <div className="bg-red-900 border border-red-700 rounded-lg p-4">
              <h3 className="text-xl font-bold text-red-300 mb-2">Error</h3>
              <p className="text-red-200">
                {error || (pdfError instanceof Error ? pdfError.message : 'Failed to load PDF')}
              </p>
            </div>
          </div>
        )}

        {/* Main Content - Step Views */}
        {!isLoading && !pdfLoading && !error && !pdfError && template && versionDetail && pdfData && (
          <>
            <div className="flex-1 overflow-y-auto">
              {currentStep === 'signature-objects' && (
                <SignatureObjectsView
                  versionDetail={versionDetail}
                  pdfUrl={pdfUrl}
                  pdfObjects={pdfObjects}
                />
              )}
              {currentStep === 'extraction-fields' && (
                <ExtractionFieldsView
                  versionDetail={versionDetail}
                  pdfUrl={pdfUrl}
                  pdfObjects={pdfObjects}
                />
              )}
              {currentStep === 'pipeline' && (
                <PipelineView versionDetail={versionDetail} />
              )}
            </div>

            {/* Footer - Stepper with Navigation */}
            <div className="flex items-center justify-between px-6 py-4 border-t border-gray-700 bg-gray-900">
              <TemplateViewerStepper currentStep={currentStep} />

              {/* Navigation Buttons */}
              <div className="flex items-center space-x-3">
                {currentStep !== 'signature-objects' && (
                  <button
                    onClick={handleBack}
                    className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
                  >
                    ← Back
                  </button>
                )}
                {currentStep !== 'pipeline' && (
                  <button
                    onClick={handleNext}
                    className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
                  >
                    Next →
                  </button>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Signature Objects View - Read-only view with PDF overlay
// =============================================================================

// Object type colors from template builder
const OBJECT_TYPE_COLORS: Record<string, string> = {
  text_word: '#ff0000',
  text_line: '#00ff00',
  graphic_rect: '#0000ff',
  graphic_line: '#ffff00',
  graphic_curve: '#ff00ff',
  image: '#00ffff',
  table: '#ffa500',
};

const OBJECT_TYPE_NAMES: Record<string, string> = {
  text_word: 'Text Words',
  text_line: 'Text Lines',
  graphic_rect: 'Rectangles',
  graphic_line: 'Lines',
  graphic_curve: 'Curves',
  image: 'Images',
  table: 'Tables',
};

interface SignatureObjectsViewProps {
  versionDetail: TemplateVersionDetail;
  pdfUrl: string;
  pdfObjects: any;
}

// Convert hex to rgba
function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// Read-only overlay for signature objects (PdfObjects format)
function SignatureObjectsOverlay({
  signatureObjects,
  selectedTypes
}: {
  signatureObjects: PdfObjects;
  selectedTypes: Set<string>;
}) {
  const { renderScale, currentPage, pdfDimensions } = usePdfViewer();

  // Flatten PdfObjects and filter for current page + visible types
  const objectsOnPage = useMemo(() => {
    const flattened: Array<{ type: string; page: number; bbox: [number, number, number, number]; text?: string }> = [];

    // Only add objects of selected types
    if (selectedTypes.has('text_word')) {
      signatureObjects.text_words.forEach(obj => flattened.push({ ...obj, type: 'text_word' }));
    }
    if (selectedTypes.has('text_line')) {
      signatureObjects.text_lines.forEach(obj => flattened.push({ ...obj, type: 'text_line' }));
    }
    if (selectedTypes.has('graphic_rect')) {
      signatureObjects.graphic_rects.forEach(obj => flattened.push({ ...obj, type: 'graphic_rect' }));
    }
    if (selectedTypes.has('graphic_line')) {
      signatureObjects.graphic_lines.forEach(obj => flattened.push({ ...obj, type: 'graphic_line' }));
    }
    if (selectedTypes.has('graphic_curve')) {
      signatureObjects.graphic_curves.forEach(obj => flattened.push({ ...obj, type: 'graphic_curve' }));
    }
    if (selectedTypes.has('image')) {
      signatureObjects.images.forEach(obj => flattened.push({ ...obj, type: 'image' }));
    }
    if (selectedTypes.has('table')) {
      signatureObjects.tables.forEach(obj => flattened.push({ ...obj, type: 'table' }));
    }

    // Filter for current page (1-indexed)
    return flattened.filter(obj => obj.page === currentPage);
  }, [signatureObjects, currentPage, selectedTypes]);

  if (!pdfDimensions) {
    return null;
  }

  const pageHeight = pdfDimensions.height;

  return (
    <>
      {objectsOnPage.map((obj, index) => {
        const [x0, y0, x1, y1] = obj.bbox;

        // Coordinate transformation - text objects use pdfplumber coords (y=0 at top)
        const screenY0 = y0;
        const screenY1 = y1;

        const color = OBJECT_TYPE_COLORS[obj.type] || '#808080';
        const backgroundColor = hexToRgba(color, 0.2);
        const borderColor = hexToRgba(color, 0.6);

        const style: React.CSSProperties = {
          position: 'absolute',
          left: `${x0 * renderScale}px`,
          top: `${screenY0 * renderScale}px`,
          width: `${(x1 - x0) * renderScale}px`,
          height: `${(screenY1 - screenY0) * renderScale}px`,
          backgroundColor,
          border: `2px solid ${borderColor}`,
          pointerEvents: 'none',
          zIndex: 5,
        };

        return (
          <div
            key={index}
            style={style}
            title={obj.text || obj.type}
          />
        );
      })}
    </>
  );
}

function SignatureObjectsView({ versionDetail, pdfUrl, pdfObjects }: SignatureObjectsViewProps) {
  const [pdfScale, setPdfScale] = useState(1.0);
  const [pdfCurrentPage, setPdfCurrentPage] = useState(1);

  // Count signature objects by type
  const typeCounts = useMemo(() => {
    return {
      text_word: versionDetail.signature_objects.text_words.length,
      text_line: versionDetail.signature_objects.text_lines.length,
      graphic_rect: versionDetail.signature_objects.graphic_rects.length,
      graphic_line: versionDetail.signature_objects.graphic_lines.length,
      graphic_curve: versionDetail.signature_objects.graphic_curves.length,
      image: versionDetail.signature_objects.images.length,
      table: versionDetail.signature_objects.tables.length,
    };
  }, [versionDetail.signature_objects]);

  const totalCount = Object.values(typeCounts).reduce((sum, count) => sum + count, 0);

  // Visibility toggles - start with all types visible
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(() => {
    const allTypes = Object.keys(typeCounts).filter((type) => typeCounts[type as keyof typeof typeCounts] > 0);
    return new Set(allTypes);
  });

  const handleTypeToggle = (type: string) => {
    setSelectedTypes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(type)) {
        newSet.delete(type);
      } else {
        newSet.add(type);
      }
      return newSet;
    });
  };

  const handleShowAll = () => {
    const allTypes = Object.keys(typeCounts).filter((type) => typeCounts[type as keyof typeof typeCounts] > 0);
    setSelectedTypes(new Set(allTypes));
  };

  const handleHideAll = () => {
    setSelectedTypes(new Set());
  };

  return (
    <div className="h-full w-full flex">
      {/* Sidebar - Matches builder structure */}
      <div className="w-80 flex-shrink-0 bg-gray-900 border-r border-gray-700 p-4 overflow-y-auto">
        {/* Template Information (read-only) */}
        <div className="mb-6 pb-4 border-b border-gray-700">
          <h3 className="text-sm font-semibold text-white mb-3">Template Information</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">
                Total Signature Objects
              </label>
              <div className="text-sm text-white">
                {totalCount} objects
              </div>
            </div>
          </div>
        </div>

        {/* Object Visibility Section */}
        <h3 className="text-sm font-semibold text-white mb-3">Object Visibility</h3>

        {/* Show/Hide All Buttons */}
        <div className="space-y-2 mb-4">
          <button
            onClick={handleShowAll}
            className="w-full px-3 py-2 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors font-medium"
          >
            Show All Types
          </button>
          <button
            onClick={handleHideAll}
            className="w-full px-3 py-2 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors font-medium"
          >
            Hide All Types
          </button>
        </div>

        {/* Object Type Buttons */}
        <div className="space-y-2">
          {Object.entries(OBJECT_TYPE_NAMES).map(([type, label]) => {
            const count = typeCounts[type as keyof typeof typeCounts] || 0;

            // Don't render if no objects of this type
            if (count === 0) return null;

            const color = OBJECT_TYPE_COLORS[type] || '#808080';
            const isSelected = selectedTypes.has(type);

            return (
              <button
                key={type}
                onClick={() => handleTypeToggle(type)}
                className={`w-full flex items-center justify-between p-2.5 text-xs rounded transition-colors ${
                  isSelected
                    ? 'bg-gray-700 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
                aria-label={`Toggle ${label}`}
                aria-pressed={isSelected}
              >
                <div className="flex items-center space-x-2.5">
                  <div
                    className="w-3 h-3 rounded flex-shrink-0"
                    style={{ backgroundColor: color }}
                    aria-hidden="true"
                  />
                  <span className="text-left">{label}</span>
                </div>
                <span className="font-medium ml-2">{count.toLocaleString()}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* PDF Viewer with Signature Object Overlays */}
      <div className="flex-1 overflow-hidden bg-gray-800">
        <PdfViewer
          pdfUrl={pdfUrl}
          initialScale={pdfScale}
          initialPage={pdfCurrentPage}
          onScaleChange={setPdfScale}
          onPageChange={setPdfCurrentPage}
        >
          <PdfViewer.Canvas pdfUrl={pdfUrl}>
            <SignatureObjectsOverlay
              signatureObjects={versionDetail.signature_objects}
              selectedTypes={selectedTypes}
            />
          </PdfViewer.Canvas>
          <PdfViewer.ControlsSidebar position="right" />
        </PdfViewer>
      </div>
    </div>
  );
}

// =============================================================================
// Extraction Fields View - Read-only view with PDF overlay
// =============================================================================

interface ExtractionFieldsViewProps {
  versionDetail: TemplateVersionDetail;
  pdfUrl: string;
  pdfObjects: any;
}

// Read-only overlay for extraction fields
function ExtractionFieldsOverlay({ extractionFields }: { extractionFields: any[] }) {
  const { renderScale, currentPage, pdfDimensions } = usePdfViewer();

  // Filter fields for current page (both PDF viewer and fields are 1-indexed)
  const fieldsOnPage = useMemo(() => {
    return extractionFields.filter(field => field.page === currentPage);
  }, [extractionFields, currentPage]);

  if (!pdfDimensions) {
    return null;
  }

  const pageHeight = pdfDimensions.height;

  return (
    <>
      {fieldsOnPage.map((field, index) => {
        const [x0, y0, x1, y1] = field.bbox;

        // Coordinate transformation - extraction fields use text coordinates
        const screenY0 = y0;
        const screenY1 = y1;

        const style: React.CSSProperties = {
          position: 'absolute',
          left: `${x0 * renderScale}px`,
          top: `${screenY0 * renderScale}px`,
          width: `${(x1 - x0) * renderScale}px`,
          height: `${(screenY1 - screenY0) * renderScale}px`,
          backgroundColor: 'rgba(34, 197, 94, 0.2)', // Green for extraction fields
          border: '2px solid rgba(34, 197, 94, 0.7)',
          pointerEvents: 'none', // Read-only, not clickable
          zIndex: 5,
        };

        return (
          <div
            key={field.name}
            style={style}
            title={field.name}
          />
        );
      })}
    </>
  );
}

function ExtractionFieldsView({ versionDetail, pdfUrl, pdfObjects }: ExtractionFieldsViewProps) {
  const [pdfScale, setPdfScale] = useState(1.0);
  const [pdfCurrentPage, setPdfCurrentPage] = useState(1);

  return (
    <div className="h-full w-full flex">
      {/* Sidebar - Extraction Fields List */}
      <div className="w-80 border-r border-gray-700 bg-gray-800 p-4 overflow-y-auto">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-white mb-2">
            Extraction Fields
          </h3>
          <p className="text-sm text-gray-400">
            {versionDetail.extraction_fields.length} fields will be extracted
          </p>
        </div>

        <div className="space-y-2">
          {versionDetail.extraction_fields.map((field) => (
            <div
              key={field.name}
              className="bg-gray-700 border border-green-600 rounded-lg p-3"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-white">
                  {field.name}
                </span>
              </div>
              {field.description && (
                <p className="text-xs text-gray-400 mb-1">{field.description}</p>
              )}
              <div className="text-xs text-gray-500">
                Page {field.page} • [{field.bbox.map(v => v.toFixed(0)).join(', ')}]
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* PDF Viewer with Extraction Field Overlays */}
      <div className="flex-1 overflow-hidden bg-gray-800">
        <PdfViewer
          pdfUrl={pdfUrl}
          initialScale={pdfScale}
          initialPage={pdfCurrentPage}
          onScaleChange={setPdfScale}
          onPageChange={setPdfCurrentPage}
        >
          <PdfViewer.Canvas pdfUrl={pdfUrl}>
            <ExtractionFieldsOverlay extractionFields={versionDetail.extraction_fields} />
          </PdfViewer.Canvas>
          <PdfViewer.ControlsSidebar position="right" />
        </PdfViewer>
      </div>
    </div>
  );
}

// =============================================================================
// Pipeline View - Read-only pipeline visualization
// =============================================================================

interface PipelineViewProps {
  versionDetail: TemplateVersionDetail;
}

function PipelineView({ versionDetail }: PipelineViewProps) {
  return (
    <div className="h-full w-full bg-gray-900 p-6">
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
        <h3 className="text-xl font-semibold text-white mb-4">
          Pipeline Visualization
        </h3>
        <p className="text-sm text-gray-400 mb-4">
          Visual representation of the data transformation pipeline for this version.
        </p>
        <div className="text-sm text-gray-400">
          Pipeline Definition ID: {versionDetail.pipeline_definition_id}
        </div>
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-lg p-8 flex items-center justify-center min-h-[400px] mt-6">
        <div className="text-center">
          <div className="text-gray-400 mb-2">
            <svg
              className="mx-auto h-16 w-16 text-gray-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z"
              />
            </svg>
          </div>
          <h4 className="text-lg font-medium text-white mb-2">
            Pipeline Visualization Coming Soon
          </h4>
          <p className="text-sm text-gray-400">
            Interactive pipeline graph will be displayed here
          </p>
        </div>
      </div>
    </div>
  );
}
