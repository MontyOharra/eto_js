/**
 * Template Detail Modal
 * Version-based read-only viewer for template details
 * Displays signature objects, extraction fields, and pipeline for each version
 */

import { useEffect, useState, useMemo } from 'react';
import { useMockTemplatesApi } from '../../hooks';
import {
  TemplateDetail,
  TemplateVersionListItem,
  TemplateVersionDetail,
  SignatureObject,
  PipelineState,
  VisualState
} from '../../types';
import { TemplateStatusBadge } from '../ui/TemplateStatusBadge';
import { TemplateBuilderStepper } from '../builder/components';
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

export function TemplateDetailModal({
  isOpen,
  templateId,
  onClose,
  onEdit,
}: TemplateDetailModalProps) {
  const { getTemplateDetail, getTemplateVersions, getTemplateVersionDetail, isLoading } = useMockTemplatesApi();

  // Template and version state
  const [template, setTemplate] = useState<TemplateDetail | null>(null);
  const [versions, setVersions] = useState<TemplateVersionListItem[]>([]);
  const [currentVersionIndex, setCurrentVersionIndex] = useState<number>(0);
  const [versionDetail, setVersionDetail] = useState<TemplateVersionDetail | null>(null);

  // UI state
  const [currentStep, setCurrentStep] = useState<ViewStep>('signature-objects');
  const [error, setError] = useState<string | null>(null);

  // PDF data - fetch once using source_pdf_id
  const { data: pdfData, isLoading: pdfLoading, error: pdfError } = usePdfData(
    template?.source_pdf_id ?? null
  );

  // Fetch template and versions when modal opens
  useEffect(() => {
    if (isOpen && templateId) {
      loadTemplateAndVersions();
    } else {
      // Reset state when modal closes
      resetState();
    }
  }, [isOpen, templateId]);

  // Fetch version detail when version changes
  useEffect(() => {
    if (template && versions.length > 0) {
      loadVersionDetail(versions[currentVersionIndex].version_id);
    }
  }, [currentVersionIndex, versions]);

  const loadTemplateAndVersions = async () => {
    if (!templateId) return;

    setError(null);
    try {
      // Fetch template details and versions list in parallel
      const [templateData, versionsData] = await Promise.all([
        getTemplateDetail(templateId),
        getTemplateVersions(templateId),
      ]);

      setTemplate(templateData);
      setVersions(versionsData);

      // Find the current version index
      const currentIdx = versionsData.findIndex((v) => v.is_current);
      setCurrentVersionIndex(currentIdx >= 0 ? currentIdx : 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load template');
    }
  };

  const loadVersionDetail = async (versionId: number) => {
    if (!templateId) return;

    setError(null);
    try {
      const detail = await getTemplateVersionDetail(templateId, versionId);
      setVersionDetail(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load version details');
    }
  };

  const resetState = () => {
    setTemplate(null);
    setVersions([]);
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
    if (currentVersionIndex < versions.length - 1) {
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

  const currentVersion = versions[currentVersionIndex];
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
          {versions.length > 0 && currentVersion && (
            <div className="flex items-center space-x-4">
              <button
                onClick={handleNextVersion}
                disabled={currentVersionIndex === versions.length - 1}
                className="px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded transition-colors"
                title="Decrement version"
              >
                ←
              </button>
              <div className="text-center">
                <div className="text-sm font-medium text-white">
                  Version {currentVersion.version_num} of {versions.length}
                </div>
                <div className="text-xs text-gray-400 flex items-center space-x-2">
                  <span>{currentVersion.usage_count} runs</span>
                  {currentVersion.is_current && (
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
              <TemplateBuilderStepper
                currentStep={currentStep}
                completedSteps={new Set(['signature-objects', 'extraction-fields', 'pipeline'])}
                testStatus={null}
              />

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

// Read-only overlay for signature objects
function SignatureObjectsOverlay({ signatureObjects }: { signatureObjects: SignatureObject[] }) {
  const { renderScale, currentPage, pdfDimensions } = usePdfViewer();

  console.log('[SignatureObjectsOverlay] All signature objects:', signatureObjects);
  console.log('[SignatureObjectsOverlay] Current page:', currentPage);
  console.log('[SignatureObjectsOverlay] PDF dimensions:', pdfDimensions);

  // Filter objects for current page (PDF viewer is 1-indexed, objects are 0-indexed)
  const objectsOnPage = useMemo(() => {
    const filtered = signatureObjects.filter(obj => obj.page === currentPage - 1);
    console.log('[SignatureObjectsOverlay] Objects on current page:', filtered);
    return filtered;
  }, [signatureObjects, currentPage]);

  if (!pdfDimensions) {
    console.log('[SignatureObjectsOverlay] No PDF dimensions yet');
    return null;
  }

  const pageHeight = pdfDimensions.height;

  return (
    <>
      {objectsOnPage.map((obj, index) => {
        const [x0, y0, x1, y1] = obj.bbox;

        // Coordinate transformation - text objects don't need Y-axis flipping
        let screenY0: number, screenY1: number;
        const noFlipping = obj.object_type === 'text_word' ||
                          obj.object_type === 'text_line' ||
                          obj.object_type === 'table' ||
                          obj.object_type === 'graphic_curve';

        if (noFlipping) {
          screenY0 = y0;
          screenY1 = y1;
        } else {
          screenY0 = pageHeight - y1;
          screenY1 = pageHeight - y0;
        }

        const color = OBJECT_TYPE_COLORS[obj.object_type] || '#808080';
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

        console.log('[SignatureObjectsOverlay] Rendering object:', {
          type: obj.object_type,
          bbox: obj.bbox,
          screenY: [screenY0, screenY1],
          style,
        });

        return (
          <div
            key={index}
            style={style}
            title={obj.text || obj.object_type}
          />
        );
      })}
    </>
  );
}

function SignatureObjectsView({ versionDetail, pdfUrl, pdfObjects }: SignatureObjectsViewProps) {
  const [pdfScale, setPdfScale] = useState(1.0);
  const [pdfCurrentPage, setPdfCurrentPage] = useState(1);

  // Group signature objects by type
  const objectsByType = useMemo(() => {
    const grouped: Record<string, SignatureObject[]> = {};
    versionDetail.signature_objects.forEach(obj => {
      if (!grouped[obj.object_type]) {
        grouped[obj.object_type] = [];
      }
      grouped[obj.object_type].push(obj);
    });
    return grouped;
  }, [versionDetail.signature_objects]);

  return (
    <div className="h-full w-full flex">
      {/* Sidebar - Signature Objects Grouped by Type */}
      <div className="w-80 border-r border-gray-700 bg-gray-900 p-4 overflow-y-auto">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-white mb-2">
            Signature Objects
          </h3>
          <p className="text-sm text-gray-400">
            {versionDetail.signature_objects.length} objects define this template's signature
          </p>
        </div>

        {/* Objects grouped by type */}
        <div className="space-y-4">
          {Object.entries(objectsByType).map(([type, objects]) => {
            const color = OBJECT_TYPE_COLORS[type] || '#808080';
            const typeName = OBJECT_TYPE_NAMES[type] || type;

            return (
              <div key={type} className="space-y-2">
                {/* Type Header */}
                <div className="flex items-center space-x-2">
                  <div
                    className="w-4 h-4 rounded border-2"
                    style={{
                      backgroundColor: hexToRgba(color, 0.3),
                      borderColor: color,
                    }}
                  />
                  <span className="text-sm font-semibold text-white">
                    {typeName} ({objects.length})
                  </span>
                </div>

                {/* Objects of this type */}
                <div className="space-y-1 ml-6">
                  {objects.map((obj, index) => (
                    <div
                      key={index}
                      className="bg-gray-800 rounded p-2 text-xs"
                      style={{
                        borderLeft: `3px solid ${color}`,
                      }}
                    >
                      <div className="flex items-center justify-between text-gray-400">
                        <span>Page {obj.page + 1}</span>
                        {obj.text && (
                          <span className="truncate ml-2 text-gray-300" title={obj.text}>
                            "{obj.text}"
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
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
            <SignatureObjectsOverlay signatureObjects={versionDetail.signature_objects} />
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

  // Filter fields for current page (PDF viewer is 1-indexed, fields are 0-indexed)
  const fieldsOnPage = useMemo(() => {
    return extractionFields.filter(field => field.page === currentPage - 1);
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
            key={field.field_id}
            style={style}
            title={field.label}
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
              key={field.field_id}
              className="bg-gray-700 border border-green-600 rounded-lg p-3"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-white">
                  {field.label}
                </span>
                {field.required && (
                  <span className="text-xs px-2 py-0.5 bg-red-900 text-red-300 rounded">
                    Required
                  </span>
                )}
              </div>
              {field.description && (
                <p className="text-xs text-gray-400 mb-1">{field.description}</p>
              )}
              <div className="text-xs text-gray-500">
                Page {field.page + 1} • [{field.bbox.map(v => v.toFixed(0)).join(', ')}]
              </div>
              {field.validation_regex && (
                <div className="text-xs text-gray-400 mt-1">
                  <code className="bg-gray-900 px-1 py-0.5 rounded">
                    {field.validation_regex}
                  </code>
                </div>
              )}
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
