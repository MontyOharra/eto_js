/**
 * TemplateDetailModal
 * Main container for template detail viewer
 * Manages state and data fetching for template and version details
 */

import { useState, useMemo, useEffect } from 'react';
import { useTemplateDetail, useTemplateVersionDetail } from '../../api/hooks';
import { usePdfData } from '../../../pdf';
import { usePipelinesApi, type PipelineDetail } from '../../../pipelines';
import { TemplateDetailHeader } from './TemplateDetailHeader';
import { TemplateDetailFooter } from './TemplateDetailFooter';
import { SignatureObjectsView } from './SignatureObjectsView';
import { ExtractionFieldsView } from './ExtractionFieldsView';
import { PipelineView } from './PipelineView';

// Step type
type DetailStep = 'signature-objects' | 'extraction-fields' | 'pipeline';

// Props interface
interface TemplateDetailModalProps {
  isOpen: boolean;
  templateId: number | null;
  onClose: () => void;
  onEdit?: (templateId: number, versionId: number) => void;
}

export function TemplateDetailModal({
  isOpen,
  templateId,
  onClose,
  onEdit,
}: TemplateDetailModalProps) {
  // Current step state
  const [currentStep, setCurrentStep] = useState<DetailStep>('signature-objects');

  // Fetch template detail (includes version list)
  const { data: templateDetail, isLoading: templateLoading, error: templateError } = useTemplateDetail(templateId);

  // Selected version state (defaults to current version)
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);

  // Determine which version to fetch
  const versionIdToFetch = useMemo(() => {
    if (selectedVersionId) return selectedVersionId;
    if (templateDetail?.current_version_id) return templateDetail.current_version_id;
    return null;
  }, [selectedVersionId, templateDetail?.current_version_id]);

  // Fetch version detail
  const { data: versionDetail, isLoading: versionLoading, error: versionError } = useTemplateVersionDetail(versionIdToFetch);

  // Fetch PDF data (only need to fetch once - all versions use same PDF)
  const pdfFileId = templateDetail?.source_pdf_id || null;
  const { data: pdfData, isLoading: pdfLoading } = usePdfData(pdfFileId);

  // Fetch pipeline data for current version
  const { getPipeline } = usePipelinesApi();
  const [pipelineData, setPipelineData] = useState<PipelineDetail | null>(null);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [pipelineError, setPipelineError] = useState<Error | null>(null);

  useEffect(() => {
    if (!versionDetail?.pipeline_definition_id) {
      setPipelineData(null);
      return;
    }

    let cancelled = false;
    setPipelineLoading(true);
    setPipelineError(null);

    getPipeline(versionDetail.pipeline_definition_id)
      .then((data) => {
        if (!cancelled) {
          setPipelineData(data);
          setPipelineLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setPipelineError(err instanceof Error ? err : new Error('Failed to load pipeline'));
          setPipelineLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [versionDetail?.pipeline_definition_id, getPipeline]);

  // Sort versions by version_number ascending
  const sortedVersions = useMemo(() => {
    if (!templateDetail?.versions) return [];
    return [...templateDetail.versions].sort((a, b) => a.version_number - b.version_number);
  }, [templateDetail?.versions]);

  // Handle version selection
  const handleVersionChange = (versionId: number) => {
    setSelectedVersionId(versionId);
    // Keep current step when changing versions for better UX
  };

  // Handle edit button
  const handleEdit = () => {
    if (templateId && versionIdToFetch && onEdit) {
      onEdit(templateId, versionIdToFetch);
    }
  };

  // Handle step navigation
  const handleNext = () => {
    if (currentStep === 'signature-objects') {
      setCurrentStep('extraction-fields');
    } else if (currentStep === 'extraction-fields') {
      setCurrentStep('pipeline');
    }
  };

  const handleBack = () => {
    if (currentStep === 'pipeline') {
      setCurrentStep('extraction-fields');
    } else if (currentStep === 'extraction-fields') {
      setCurrentStep('signature-objects');
    }
  };

  // Don't render if not open
  if (!isOpen) return null;

  // Loading state
  const isLoading = templateLoading || versionLoading || pdfLoading || (currentStep === 'pipeline' && pipelineLoading);

  // Error state
  const error = templateError || versionError || (currentStep === 'pipeline' ? pipelineError : null);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-gray-900 rounded-lg w-full max-w-[95vw] h-[95vh] overflow-hidden flex flex-col shadow-2xl border border-gray-700">
        {/* Header */}
        <TemplateDetailHeader
          templateName={templateDetail?.name || 'Loading...'}
          customerName={templateDetail?.customer_name || null}
          customerId={templateDetail?.customer_id || null}
          versions={sortedVersions}
          selectedVersionId={versionIdToFetch}
          currentVersionId={templateDetail?.current_version_id || null}
          onVersionChange={handleVersionChange}
          onEdit={onEdit ? handleEdit : undefined}
        />

        {/* Content Area */}
        <div className="flex-1 overflow-hidden">
          {isLoading && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p className="text-gray-400">Loading template details...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="h-full flex items-center justify-center p-6">
              <div className="bg-red-900 border border-red-700 rounded-lg p-6 max-w-md">
                <h3 className="text-xl font-bold text-red-300 mb-2">Error</h3>
                <p className="text-red-200">
                  {error instanceof Error ? error.message : 'Failed to load template details'}
                </p>
              </div>
            </div>
          )}

          {!isLoading && !error && versionDetail && pdfData && (
            <>
              {currentStep === 'signature-objects' && (
                <SignatureObjectsView
                  pdfUrl={pdfData.url}
                  signatureObjects={versionDetail.signature_objects}
                />
              )}

              {currentStep === 'extraction-fields' && (
                <ExtractionFieldsView
                  pdfUrl={pdfData.url}
                  extractionFields={versionDetail.extraction_fields}
                />
              )}

              {currentStep === 'pipeline' && pipelineData && (
                <PipelineView
                  pipelineState={pipelineData.pipeline_state}
                  visualState={pipelineData.visual_state}
                />
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <TemplateDetailFooter
          currentStep={currentStep}
          onBack={handleBack}
          onNext={handleNext}
          onClose={onClose}
        />
      </div>
    </div>
  );
}
