/**
 * TemplateDetailModal
 * Main container for template detail viewer
 * Manages state and data fetching for template and version details
 */

import { useState, useMemo, useEffect, useRef } from 'react';
import { useTemplateDetail, useTemplateVersionDetail, useDebugMatchTemplate } from '../../api/hooks';
import { usePdfData, createSubsetPdf } from '../../../pdf';
import { usePipelinesApi, type PipelineDetail } from '../../../pipelines';
import { TemplateDetailHeader } from './TemplateDetailHeader';
import { TemplateDetailFooter } from './TemplateDetailFooter';
import { SignatureObjectsView } from './SignatureObjectsView';
import { ExtractionFieldsView } from './ExtractionFieldsView';
import { PipelineView } from './PipelineView';
import { PageSelectionStep } from '../TemplateBuilder/PageSelectionStep';
import { DebugMatchResultsView } from './DebugMatchResultsView';
import type { DebugMatchResponse } from '../../api/types';

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

  // Test match state
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [testMatchPdfFile, setTestMatchPdfFile] = useState<File | null>(null);
  const [testMatchPdfUrl, setTestMatchPdfUrl] = useState<string | null>(null);
  const [testMatchSelectedPages, setTestMatchSelectedPages] = useState<number[]>([]);
  const [showPageSelectionModal, setShowPageSelectionModal] = useState(false);
  const [testMatchStep, setTestMatchStep] = useState<'page-selection' | 'results'>('page-selection');
  const [testMatchResults, setTestMatchResults] = useState<DebugMatchResponse | null>(null);
  const [testMatchSubsetPdfUrl, setTestMatchSubsetPdfUrl] = useState<string | null>(null);

  // Debug match mutation
  const debugMatchMutation = useDebugMatchTemplate();

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

  // Handle test match button - opens file picker
  const handleTestMatch = () => {
    fileInputRef.current?.click();
  };

  // Handle file selection for test match
  const handleTestMatchFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setTestMatchPdfFile(file);
      // Create blob URL for the PDF
      const url = URL.createObjectURL(file);
      setTestMatchPdfUrl(url);
      setTestMatchSelectedPages([]);
      setShowPageSelectionModal(true);
    }
    // Reset input so same file can be selected again
    e.target.value = '';
  };

  // Handle closing the test match modal
  const handleCloseTestMatch = () => {
    setShowPageSelectionModal(false);
    setTestMatchStep('page-selection');
    setTestMatchResults(null);
    // Clean up blob URLs
    if (testMatchPdfUrl) {
      URL.revokeObjectURL(testMatchPdfUrl);
      setTestMatchPdfUrl(null);
    }
    if (testMatchSubsetPdfUrl) {
      URL.revokeObjectURL(testMatchSubsetPdfUrl);
      setTestMatchSubsetPdfUrl(null);
    }
    setTestMatchPdfFile(null);
    setTestMatchSelectedPages([]);
  };

  // Handle continuing from page selection to results
  const handlePageSelectionContinue = async () => {
    if (!testMatchPdfFile || !versionIdToFetch) return;

    try {
      // Create subset PDF with selected pages
      const subsetPdf = await createSubsetPdf(testMatchPdfFile, testMatchSelectedPages);

      // Create blob URL for the subset PDF (for display in results)
      const subsetUrl = URL.createObjectURL(subsetPdf);
      setTestMatchSubsetPdfUrl(subsetUrl);

      // Call the debug match API
      const results = await debugMatchMutation.mutateAsync({
        versionId: versionIdToFetch,
        pdfFile: subsetPdf,
      });

      setTestMatchResults(results);
      setTestMatchStep('results');
    } catch (error) {
      console.error('Debug match failed:', error);
      // TODO: Show error to user
    }
  };

  // Handle going back from results to page selection
  const handleBackToPageSelection = () => {
    setTestMatchStep('page-selection');
    setTestMatchResults(null);
    if (testMatchSubsetPdfUrl) {
      URL.revokeObjectURL(testMatchSubsetPdfUrl);
      setTestMatchSubsetPdfUrl(null);
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
        {/* Hidden file input for test match */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleTestMatchFileChange}
          className="hidden"
        />

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
          onTestMatch={handleTestMatch}
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

      {/* Test Match Modal */}
      {showPageSelectionModal && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-gray-900 rounded-lg w-full max-w-[90vw] h-[90vh] overflow-hidden flex flex-col shadow-2xl border border-gray-700">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-700 flex-shrink-0">
              <h2 className="text-xl font-semibold text-white">
                {testMatchStep === 'page-selection' ? 'Select Pages to Test' : 'Match Results'}
              </h2>
              <button
                onClick={handleCloseTestMatch}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden">
              {testMatchStep === 'page-selection' && testMatchPdfUrl && (
                <PageSelectionStep
                  pdfUrl={testMatchPdfUrl}
                  selectedPages={testMatchSelectedPages}
                  onPagesChange={setTestMatchSelectedPages}
                />
              )}

              {testMatchStep === 'results' && testMatchResults && testMatchSubsetPdfUrl && (
                <DebugMatchResultsView
                  pdfUrl={testMatchSubsetPdfUrl}
                  results={testMatchResults}
                />
              )}

              {debugMatchMutation.isPending && (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                    <p className="text-gray-400">Testing template match...</p>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between p-4 border-t border-gray-700 flex-shrink-0">
              {testMatchStep === 'page-selection' ? (
                <>
                  <button
                    onClick={handleCloseTestMatch}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handlePageSelectionContinue}
                    disabled={testMatchSelectedPages.length === 0 || debugMatchMutation.isPending}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                  >
                    {debugMatchMutation.isPending
                      ? 'Testing...'
                      : `Continue (${testMatchSelectedPages.length} page${testMatchSelectedPages.length !== 1 ? 's' : ''} selected)`
                    }
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={handleBackToPageSelection}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
                  >
                    Back
                  </button>
                  <button
                    onClick={handleCloseTestMatch}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                  >
                    Done
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
