/**
 * Template Builder Modal
 * 3-step wizard for creating PDF templates
 */

import { useState, useMemo, useEffect } from 'react';
import { SignatureObject, ExtractionField } from '../../types';
import { SignatureObjectsStep, ExtractionFieldsStep, PipelineBuilderStep, TestingStep, TemplateSimulationResult } from './steps';
import { TemplateBuilderHeader, TemplateBuilderStepper } from './components';
import { usePdfData, usePdfFilesApi } from '../../../pdf-files/hooks';
import { useMockModulesApi } from '../../../modules/hooks';
import { usePipelineValidation } from '../../../pipelines/hooks';
import type { ModuleTemplate } from '../../../../types/moduleTypes';
import type { PipelineState, VisualState } from '../../../../types/pipelineTypes';

interface TemplateBuilderModalProps {
  isOpen: boolean;
  pdfFileId: number | null;
  pdfFile: File | null; // For new template creation with uploaded PDF
  onClose: () => void;
  onSave: (templateData: TemplateData) => Promise<void>;
}

export interface TemplateData {
  name: string;
  description: string;
  source_pdf_id?: number | null; // Optional for uploaded PDFs
  pdf_file?: File | null; // For uploaded PDFs
  signature_objects: SignatureObject[];
  extraction_fields: ExtractionField[];
  pipeline_state: PipelineState;
  visual_state: VisualState;
}

type BuilderStep = 'signature-objects' | 'extraction-fields' | 'pipeline' | 'testing';

export function TemplateBuilderModal({
  isOpen,
  pdfFileId,
  pdfFile,
  onClose,
  onSave,
}: TemplateBuilderModalProps) {
  const [currentStep, setCurrentStep] = useState<BuilderStep>('signature-objects');
  const [templateName, setTemplateName] = useState('');
  const [templateDescription, setTemplateDescription] = useState('');
  const [signatureObjects, setSignatureObjects] = useState<SignatureObject[]>([]);
  const [selectedObjectTypes, setSelectedObjectTypes] = useState<string[]>([]); // Step 1 state persistence
  const [extractionFields, setExtractionFields] = useState<ExtractionField[]>([]);
  const [pipelineState, setPipelineState] = useState<PipelineState>({
    entry_points: [],
    modules: [],
    connections: [],
  });
  const [visualState, setVisualState] = useState<VisualState>({
    modules: {},
    entryPoints: {},
  });
  const [testResults, setTestResults] = useState<TemplateSimulationResult | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [testViewMode, setTestViewMode] = useState<'summary' | 'detail'>('summary');
  const [moduleTemplates, setModuleTemplates] = useState<ModuleTemplate[]>([]);

  // Snapshot of pipeline/visual state when test is run (frozen for testing view)
  const [testedPipelineState, setTestedPipelineState] = useState<PipelineState | null>(null);
  const [testedVisualState, setTestedVisualState] = useState<VisualState | null>(null);

  // PDF viewer state persistence across steps
  const [pdfScale, setPdfScale] = useState<number>(1.0);
  const [pdfCurrentPage, setPdfCurrentPage] = useState<number>(1);

  // State for uploaded PDF file
  const [uploadedPdfUrl, setUploadedPdfUrl] = useState<string | null>(null);
  const [uploadedPdfData, setUploadedPdfData] = useState<any>(null);
  const [isProcessingUpload, setIsProcessingUpload] = useState(false);

  // Use React Query to fetch and cache PDF data (only for stored PDFs)
  const { data: pdfData, isLoading: pdfLoading, error: pdfError } = usePdfData(pdfFileId);
  const { getModules } = useMockModulesApi();
  const { processObjects } = usePdfFilesApi();

  // Auto-validate pipeline as it's being built
  const { isValid: isPipelineValid, error: pipelineValidationError, isValidating: isPipelineValidating } = usePipelineValidation(pipelineState);

  // Load module templates for pipeline execution visualization
  useEffect(() => {
    async function loadModules() {
      try {
        const response = await getModules();
        setModuleTemplates(response.modules);
      } catch (error) {
        console.error('Failed to load modules:', error);
        setModuleTemplates([]);
      }
    }
    loadModules();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only load once on mount

  // Process uploaded PDF file
  useEffect(() => {
    if (!pdfFile) {
      setUploadedPdfUrl(null);
      setUploadedPdfData(null);
      return;
    }

    async function processUploadedPdf() {
      setIsProcessingUpload(true);

      try {
        // Create blob URL for PDF viewer
        const blobUrl = URL.createObjectURL(pdfFile);
        setUploadedPdfUrl(blobUrl);

        // Process PDF to extract objects via real API
        const objectsData = await processObjects(pdfFile);

        const mockMetadata = {
          id: -1, // Temporary ID for uploaded file
          email_id: null,
          filename: pdfFile.name,
          original_filename: pdfFile.name,
          relative_path: '', // No path for uploaded files
          file_size: pdfFile.size,
          file_hash: null, // Not calculated for uploaded files
          page_count: objectsData.page_count,
        };

        setUploadedPdfData({
          objectsData: objectsData,
          url: blobUrl,
          metadata: mockMetadata,
          emailData: null,
        });
      } catch (error) {
        console.error('[TemplateBuilderModal] Failed to process uploaded PDF:', error);
        // Keep URL but show empty objects on error
        const blobUrl = URL.createObjectURL(pdfFile);
        setUploadedPdfUrl(blobUrl);
        setUploadedPdfData(null);
      } finally {
        setIsProcessingUpload(false);
      }
    }

    processUploadedPdf();

    // Cleanup blob URL on unmount
    return () => {
      if (uploadedPdfUrl) {
        URL.revokeObjectURL(uploadedPdfUrl);
      }
    };
  }, [pdfFile]);

  // Extract PDF data from either stored PDF or uploaded file
  const activePdfData = pdfFile ? uploadedPdfData : pdfData;
  const pdfObjects = activePdfData?.objectsData;
  const pdfUrl = activePdfData?.url || '';
  const pdfDataLoaded = !!activePdfData;
  const isPdfLoading = pdfFile ? isProcessingUpload : pdfLoading;

  // Calculate completed steps
  const completedSteps = useMemo(() => {
    const completed = new Set<BuilderStep>();
    if (signatureObjects.length > 0) completed.add('signature-objects');
    if (extractionFields.length > 0) completed.add('extraction-fields');
    return completed;
  }, [signatureObjects.length, extractionFields.length]);

  // Determine if user can proceed from current step
  const canProceed = useMemo(() => {
    switch (currentStep) {
      case 'signature-objects':
        return signatureObjects.length > 0 && templateName.trim().length > 0;
      case 'extraction-fields':
        return extractionFields.length > 0;
      case 'pipeline':
        // Pipeline step requires valid pipeline and not currently validating
        return isPipelineValid && !isPipelineValidating;
      case 'testing':
        return testResults !== null;
      default:
        return false;
    }
  }, [currentStep, signatureObjects.length, templateName, extractionFields.length, testResults, isPipelineValid, isPipelineValidating]);

  // Get validation message for current step
  const validationMessage = useMemo(() => {
    if (canProceed) return undefined;

    switch (currentStep) {
      case 'signature-objects':
        if (templateName.trim().length === 0) {
          return 'Please enter a template name';
        }
        if (signatureObjects.length === 0) {
          return 'Please select at least one signature object';
        }
        return undefined;
      case 'extraction-fields':
        return 'Please define at least one extraction field';
      case 'pipeline':
        // Show validation error or validating status
        if (isPipelineValidating) {
          return 'Validating pipeline...';
        }
        if (pipelineValidationError) {
          return `[${pipelineValidationError.code}] ${pipelineValidationError.message}`;
        }
        return 'Pipeline validation failed';
      default:
        return undefined;
    }
  }, [currentStep, canProceed, templateName, signatureObjects.length, isPipelineValidating, pipelineValidationError]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave({
        name: templateName,
        description: templateDescription,
        source_pdf_id: pdfFileId,
        pdf_file: pdfFile,
        signature_objects: signatureObjects,
        extraction_fields: extractionFields,
        pipeline_state: pipelineState,
        visual_state: visualState,
      });
      handleClose();
    } catch (error) {
      console.error('Failed to save template:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleTest = async () => {
    setIsTesting(true);

    // Snapshot the current pipeline state (frozen for the test)
    const pipelineSnapshot = JSON.parse(JSON.stringify(pipelineState)) as PipelineState;
    const visualSnapshot = JSON.parse(JSON.stringify(visualState)) as VisualState;
    setTestedPipelineState(pipelineSnapshot);
    setTestedVisualState(visualSnapshot);

    try {
      // TODO: Call simulate API endpoint with template data and PDF
      // For now, simulate a successful test
      await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate API call

      // Mock test results - in production this would come from the API
      // This format matches ETO run detail but without template/pipeline IDs

      // Create mock extracted data keyed by field_id
      const mockExtractedData: Record<string, any> = {};
      extractionFields.forEach(field => {
        mockExtractedData[field.field_id] = '  Hello World  ';
      });

      const mockSimulationResult: TemplateSimulationResult = {
        status: 'success',
        data_extraction: {
          extracted_data: mockExtractedData,
          extracted_fields_with_boxes: extractionFields.map((field, idx) => ({
            field_id: field.field_id,
            label: field.label,
            value: '  Hello World  ',
            page: 0,
            bbox: [250, 50 + idx * 50, 400, 70 + idx * 50] as [number, number, number, number],
          })),
        },
        pipeline_execution: {
          status: 'success',
          executed_actions: [
            {
              action_module_name: 'Print Action',
              inputs: {
                message: 'HELLO WORLD',
                prefix: 'Result: ',
              },
            },
          ],
          steps: pipelineState.modules.map((module, idx) => ({
            id: idx + 1,
            step_number: idx + 1,
            module_instance_id: module.module_instance_id,
            inputs: module.inputs.reduce((acc, input) => {
              acc[input.node_id] = {
                name: input.name,
                value: '  Hello World  ',
                type: input.type,
              };
              return acc;
            }, {} as Record<string, { name: string; value: any; type: string }>),
            outputs: module.outputs.reduce((acc, output) => {
              acc[output.node_id] = {
                name: output.name,
                value: 'HELLO WORLD',
                type: output.type,
              };
              return acc;
            }, {} as Record<string, { name: string; value: any; type: string }>),
            error: null,
          })),
        },
      };

      setTestResults(mockSimulationResult);

      // Navigate to testing step
      setCurrentStep('testing');
    } catch (error) {
      console.error('Failed to test template:', error);
    } finally {
      setIsTesting(false);
    }
  };

  const handleClose = () => {
    // Reset all state (PDF data is cached by React Query, no need to reset)
    setCurrentStep('signature-objects');
    setTemplateName('');
    setTemplateDescription('');
    setSignatureObjects([]);
    setSelectedObjectTypes([]);
    setExtractionFields([]);
    setPipelineState({ entry_points: [], modules: [], connections: [] });
    setVisualState({ modules: {}, entryPoints: {} });
    setTestResults(null);
    setPdfScale(1.0);
    setPdfCurrentPage(1);
    setUploadedPdfUrl(null);
    setUploadedPdfData(null);
    onClose();
  };

  const handleNext = () => {
    console.log('[TemplateBuilderModal] handleNext called, current step:', currentStep);
    console.log('[TemplateBuilderModal] Current signature objects count:', signatureObjects.length);
    console.log('[TemplateBuilderModal] Signature objects:', signatureObjects);
    if (currentStep === 'signature-objects') {
      console.log('[TemplateBuilderModal] Moving to extraction-fields');
      setCurrentStep('extraction-fields');
    } else if (currentStep === 'extraction-fields') {
      console.log('[TemplateBuilderModal] Moving to pipeline');
      setCurrentStep('pipeline');
    }
  };

  const handleBack = () => {
    console.log('[TemplateBuilderModal] handleBack called, current step:', currentStep);
    if (currentStep === 'extraction-fields') {
      console.log('[TemplateBuilderModal] Moving back to signature-objects');
      setCurrentStep('signature-objects');
    } else if (currentStep === 'pipeline') {
      console.log('[TemplateBuilderModal] Moving back to extraction-fields');
      setCurrentStep('extraction-fields');
    } else if (currentStep === 'testing') {
      console.log('[TemplateBuilderModal] Moving back to pipeline');
      // Clear test snapshots when leaving testing step
      setTestedPipelineState(null);
      setTestedVisualState(null);
      setTestResults(null);
      setCurrentStep('pipeline');
    }
  };

  // Early return after all hooks are defined
  if (!isOpen || (!pdfFileId && !pdfFile)) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-gray-900 rounded-lg w-full max-w-[95vw] h-[95vh] overflow-hidden flex flex-col shadow-2xl border border-gray-700">
        {/* Header */}
        <TemplateBuilderHeader
          pdfMetadata={activePdfData?.metadata ?? null}
          emailData={activePdfData?.emailData}
          onClose={handleClose}
        />

        {/* Main Content */}
        <div className="flex-1 overflow-y-auto">
          {/* Loading State - only show during initial load */}
          {!pdfDataLoaded && isPdfLoading && (
            <div className="h-full flex items-center justify-center">
              <div className="text-white text-lg">
                {pdfFile ? 'Processing PDF...' : 'Loading PDF...'}
              </div>
            </div>
          )}

          {/* Error State */}
          {pdfError && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <div className="text-red-400 mb-4">
                  {pdfError instanceof Error ? pdfError.message : 'Failed to load PDF data'}
                </div>
                <button
                  onClick={handleClose}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
                >
                  Close
                </button>
              </div>
            </div>
          )}

          {/* Steps - render all but show only active one (keeps PdfCanvas mounted) */}
          {pdfDataLoaded && !pdfError && (
            <>
              {currentStep === 'signature-objects' && (
                <SignatureObjectsStep
                  pdfFileId={pdfFileId}
                  templateName={templateName}
                  templateDescription={templateDescription}
                  signatureObjects={signatureObjects}
                  selectedObjectTypes={selectedObjectTypes}
                  pdfObjects={pdfObjects}
                  pdfUrl={pdfUrl}
                  onTemplateNameChange={setTemplateName}
                  onTemplateDescriptionChange={setTemplateDescription}
                  onSignatureObjectsChange={setSignatureObjects}
                  onSelectedTypesChange={setSelectedObjectTypes}
                  pdfScale={pdfScale}
                  pdfCurrentPage={pdfCurrentPage}
                  onPdfScaleChange={setPdfScale}
                  onPdfCurrentPageChange={setPdfCurrentPage}
                />
              )}
              {currentStep === 'extraction-fields' && (
                <ExtractionFieldsStep
                  pdfFileId={pdfFileId}
                  pdfFile={pdfFile}
                  templateName={templateName}
                  templateDescription={templateDescription}
                  extractionFields={extractionFields}
                  signatureObjects={signatureObjects}
                  pdfObjects={pdfObjects}
                  pdfUrl={pdfUrl}
                  pipelineState={pipelineState}
                  visualState={visualState}
                  onTemplateNameChange={setTemplateName}
                  onTemplateDescriptionChange={setTemplateDescription}
                  onExtractionFieldsChange={setExtractionFields}
                  pdfScale={pdfScale}
                  pdfCurrentPage={pdfCurrentPage}
                  onPdfScaleChange={setPdfScale}
                  onPdfCurrentPageChange={setPdfCurrentPage}
                />
              )}
              {currentStep === 'pipeline' && (
                <PipelineBuilderStep
                  extractionFields={extractionFields}
                  pipelineState={pipelineState}
                  visualState={visualState}
                  onPipelineStateChange={setPipelineState}
                  onVisualStateChange={setVisualState}
                />
              )}
              {currentStep === 'testing' && (
                testResults && pdfUrl && testedPipelineState && testedVisualState ? (
                  <TestingStep
                    pdfUrl={pdfUrl}
                    viewMode={testViewMode}
                    simulationResult={testResults}
                    pipelineState={testedPipelineState}
                    visualState={testedVisualState}
                    moduleTemplates={moduleTemplates}
                  />
                ) : (
                  <div className="flex items-center justify-center py-12">
                    <div className="text-gray-400">No test results available</div>
                  </div>
                )
              )}
            </>
          )}
        </div>

        {/* Footer - Stepper with Navigation Buttons */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-700 bg-gray-900">
          <div className="flex items-center space-x-4">
            <TemplateBuilderStepper
              currentStep={currentStep}
              completedSteps={completedSteps}
              testStatus={testResults?.status === 'success' ? 'success' : testResults?.status === 'failure' ? 'failure' : null}
            />

            {/* View Mode Toggle - Only show in testing step */}
            {currentStep === 'testing' && testResults && (
              <div className="flex items-center bg-gray-800 rounded-lg p-1 border-l border-gray-600 ml-4">
                <button
                  onClick={() => setTestViewMode('summary')}
                  className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                    testViewMode === 'summary'
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  Summary
                </button>
                <button
                  onClick={() => setTestViewMode('detail')}
                  className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                    testViewMode === 'detail'
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  Detail
                </button>
              </div>
            )}
          </div>

          {/* Navigation Buttons */}
          <div className="flex items-center space-x-3">
            {currentStep !== 'signature-objects' && (
              <button
                onClick={handleBack}
                disabled={isSaving || isTesting}
                className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
              >
                ← Back
              </button>
            )}

            {currentStep === 'pipeline' ? (
              <button
                onClick={handleTest}
                disabled={!canProceed || isTesting}
                className="px-6 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
              >
                {isTesting ? 'Testing...' : 'Test Template →'}
              </button>
            ) : currentStep === 'testing' ? (
              <button
                onClick={handleSave}
                disabled={!canProceed || isSaving}
                className="px-6 py-2 text-sm bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
              >
                {isSaving ? 'Saving...' : 'Save Template'}
              </button>
            ) : (
              <div className="relative group">
                <button
                  onClick={handleNext}
                  disabled={!canProceed}
                  className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
                >
                  Next →
                </button>
                {/* Tooltip on hover when disabled */}
                {!canProceed && validationMessage && (
                  <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block z-10">
                    <div className="bg-gray-800 text-amber-400 text-xs px-3 py-2 rounded shadow-lg whitespace-nowrap border border-amber-400/30">
                      {validationMessage}
                      <div className="absolute top-full right-4 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-gray-800"></div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
