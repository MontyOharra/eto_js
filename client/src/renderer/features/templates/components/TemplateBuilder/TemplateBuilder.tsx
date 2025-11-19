/**
 * TemplateBuilder
 * Main template builder modal component
 * Manages state for signature objects, extraction fields, and pipeline
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import { TemplateBuilderHeader } from './TemplateBuilderHeader';
import { TemplateBuilderFooter } from './TemplateBuilderFooter';
import { PageSelectionStep } from './PageSelectionStep';
import { SignatureObjectsStep } from './SignatureObjectsStep';
import { ExtractionFieldsStep } from './ExtractionFieldsStep';
import { PipelineStep } from './PipelineStep';
import { TestingStep } from './TestingStep';
import type { PdfObjects, ExtractionField } from '../../types';
import type { PipelineState, VisualState } from '../../../pipelines/types';
import { usePdfData, useProcessPdfObjects } from '../../../pdf';
import type { PdfFileMetadata } from '../../../pdf';
import { usePipelineValidation } from '../../../pipelines/hooks';
import { useSimulateTemplate } from '../../api/hooks';
import type { SimulateTemplateResponse } from '../../api/types';

// Step type
type BuilderStep = 'page-selection' | 'signature-objects' | 'extraction-fields' | 'pipeline' | 'testing';

// Props interface
interface TemplateBuilderProps {
  isOpen: boolean;
  pdfFile: File | null;          // For create mode (local file)
  pdfFileId: number | null;       // For edit mode (existing PDF)
  pdfMetadata: PdfFileMetadata | null;
  templateId?: number;            // If provided, creating new version of existing template
  onClose: () => void;
  onSave: (data: TemplateBuilderData, templateId?: number) => Promise<void>;
  initialData?: Partial<TemplateBuilderData>;
}

// Data structure for save
export interface TemplateBuilderData {
  name: string;
  description: string;
  source_pdf_id: number;
  signature_objects: PdfObjects;
  extraction_fields: ExtractionField[];
  pipeline_state: PipelineState;
  visual_state: VisualState;
}

export function TemplateBuilder({
  isOpen,
  pdfFile,
  pdfFileId,
  pdfMetadata,
  templateId,
  onClose,
  onSave,
  initialData,
}: TemplateBuilderProps) {
  // Current step - Start with page-selection for create mode, signature-objects for version mode
  const [currentStep, setCurrentStep] = useState<BuilderStep>(() => {
    return templateId ? 'signature-objects' : 'page-selection';
  });

  // Template metadata
  const [templateName, setTemplateName] = useState(initialData?.name || '');
  const [templateDescription, setTemplateDescription] = useState(initialData?.description || '');

  // Selected pages state (for create mode only)
  const [selectedPages, setSelectedPages] = useState<number[]>([]);

  // Signature objects state
  const [selectedSignatureObjects, setSelectedSignatureObjects] = useState<PdfObjects>(
    initialData?.signature_objects || {
      text_words: [],
      graphic_rects: [],
      graphic_lines: [],
      graphic_curves: [],
      images: [],
      tables: [],
    }
  );

  // Extraction fields state
  const [extractionFields, setExtractionFields] = useState<ExtractionField[]>(
    initialData?.extraction_fields || []
  );

  // Pipeline state
  const [pipelineState, setPipelineState] = useState<PipelineState>(
    initialData?.pipeline_state || {
      entry_points: [],
      modules: [],
      connections: [],
    }
  );

  // Visual state (node positions)
  const [visualState, setVisualState] = useState<VisualState>(
    initialData?.visual_state || {}
  );

  // Saving state
  const [isSaving, setIsSaving] = useState(false);

  // Testing state
  const [viewMode, setViewMode] = useState<'summary' | 'detail'>('summary');
  const [simulationResult, setSimulationResult] = useState<SimulateTemplateResponse | null>(null);
  const [centerTrigger, setCenterTrigger] = useState<number>(0);
  const simulateMutation = useSimulateTemplate();

  // Reset all state when modal closes (isOpen becomes false)
  useEffect(() => {
    if (!isOpen) {
      // Reset to clean state for next open
      setCurrentStep(templateId ? 'signature-objects' : 'page-selection');
      setTemplateName('');
      setTemplateDescription('');
      setSelectedPages([]);
      setSelectedSignatureObjects({
        text_words: [],
        graphic_rects: [],
        graphic_lines: [],
        graphic_curves: [],
        images: [],
        tables: [],
      });
      setExtractionFields([]);
      setPipelineState({
        entry_points: [],
        modules: [],
        connections: [],
      });
      setVisualState({});
      setViewMode('summary');
      setSimulationResult(null);
      setCenterTrigger(0);
      setIsSaving(false);
      setProcessedData(null);
    }
  }, [isOpen, templateId]);

  // PDF Data Management - Centralized at TemplateBuilder level
  // Create mode: Process local PDF file
  const { mutateAsync: processObjects, isPending: isProcessing } = useProcessPdfObjects();
  const [processedData, setProcessedData] = useState<{ objects: PdfObjects; url: string } | null>(null);

  // Edit mode: Fetch PDF data from backend
  const { data: pdfData, isLoading: isFetching, error: fetchError } = usePdfData(pdfFileId);

  // Process local file when modal opens (create mode)
  useEffect(() => {
    if (pdfFile && !processedData) {
      const processPdf = async () => {
        try {
          const result = await processObjects(pdfFile);
          const blobUrl = URL.createObjectURL(pdfFile);
          setProcessedData({
            objects: result.objects,
            url: blobUrl,
          });
        } catch (err) {
          console.error('Failed to process PDF:', err);
        }
      };
      processPdf();
    }
  }, [pdfFile, processObjects, processedData]);

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (processedData?.url) {
        URL.revokeObjectURL(processedData.url);
      }
    };
  }, [processedData]);

  // Determine which data source to use
  const isLoadingPdf = pdfFile ? isProcessing : isFetching;
  const pdfError = fetchError;

  // Normalize data structure (both modes now have same shape: { objects: PdfObjects, url: string })
  const activePdfData = useMemo(() => {
    if (pdfFile) {
      return processedData;
    } else if (pdfData) {
      return { objects: pdfData.objectsData.objects, url: pdfData.url };
    }
    return null;
  }, [pdfFile, processedData, pdfData]);

  // Create complete pipeline state for validation (includes entry points)
  const completePipelineState = useMemo<PipelineState>(() => ({
    ...pipelineState,
    entry_points: pipelineState.entry_points,
  }), [pipelineState]);

  // Validate pipeline automatically when on pipeline step
  const {
    isValid: isPipelineValid,
    error: pipelineValidationError,
    isValidating: isPipelineValidating,
  } = usePipelineValidation(currentStep === 'pipeline' ? completePipelineState : null);

  // Validation logic
  const canProceed = useMemo(() => {
    switch (currentStep) {
      case 'page-selection': {
        // Must have at least one page selected
        return selectedPages.length > 0;
      }
      case 'signature-objects': {
        // Template name is required for all non-page-selection steps
        if (templateName.trim().length === 0) {
          return false;
        }
        // Must have at least one signature object selected
        const hasObjects =
          selectedSignatureObjects.text_words.length > 0 ||
          selectedSignatureObjects.graphic_rects.length > 0 ||
          selectedSignatureObjects.graphic_lines.length > 0 ||
          selectedSignatureObjects.graphic_curves.length > 0 ||
          selectedSignatureObjects.images.length > 0 ||
          selectedSignatureObjects.tables.length > 0;
        return hasObjects;
      }
      case 'extraction-fields': {
        // Template name required
        if (templateName.trim().length === 0) {
          return false;
        }
        // Must have at least one extraction field
        return extractionFields.length > 0;
      }
      case 'pipeline': {
        // Template name required
        if (templateName.trim().length === 0) {
          return false;
        }
        // Must have valid pipeline to proceed to testing
        // Use backend validation result
        return isPipelineValid && !isPipelineValidating;
      }
      case 'testing': {
        // Template name required
        if (templateName.trim().length === 0) {
          return false;
        }
        // All requirements already checked above
        return true;
      }
      default:
        return false;
    }
  }, [currentStep, selectedPages, selectedSignatureObjects, extractionFields, templateName, isPipelineValid, isPipelineValidating]);

  const validationMessage = useMemo(() => {
    if (canProceed) return undefined;

    switch (currentStep) {
      case 'page-selection':
        return 'Select at least one page to continue';
      case 'signature-objects':
        // Template name is required for all non-page-selection steps
        if (templateName.trim().length === 0) {
          return 'Enter a template name to continue';
        }
        return 'Select at least one signature object to continue';
      case 'extraction-fields':
        if (templateName.trim().length === 0) {
          return 'Enter a template name to continue';
        }
        return 'Create at least one extraction field to continue';
      case 'pipeline':
        if (templateName.trim().length === 0) {
          return 'Enter a template name to continue';
        }
        if (isPipelineValidating) {
          return 'Validating pipeline...';
        }
        if (pipelineValidationError) {
          return `[${pipelineValidationError.code}] ${pipelineValidationError.message}`;
        }
        if (pipelineState.entry_points.length === 0) {
          return 'Pipeline must have entry points';
        }
        if (pipelineState.modules.length === 0) {
          return 'Pipeline must have at least one module';
        }
        return 'Pipeline is not valid';
      case 'testing':
        if (templateName.trim().length === 0) {
          return 'Enter a template name to continue';
        }
        return 'All requirements met';
      default:
        return undefined;
    }
  }, [canProceed, currentStep, selectedPages, templateName, pipelineState, isPipelineValidating, pipelineValidationError]);

  // Track completed steps
  const completedSteps = useMemo(() => {
    const completed = new Set<BuilderStep>();

    // Template name is required for all steps except page-selection
    const hasTemplateName = templateName.trim().length > 0;

    // Step 0: Page selection (only for create mode)
    if (!templateId && selectedPages.length > 0) {
      completed.add('page-selection');
    }

    // Step 1: Signature objects (requires template name + signature objects)
    const hasSignatureObjects =
      selectedSignatureObjects.text_words.length > 0 ||
      selectedSignatureObjects.graphic_rects.length > 0 ||
      selectedSignatureObjects.graphic_lines.length > 0 ||
      selectedSignatureObjects.graphic_curves.length > 0 ||
      selectedSignatureObjects.images.length > 0 ||
      selectedSignatureObjects.tables.length > 0;
    if (hasTemplateName && hasSignatureObjects) {
      completed.add('signature-objects');
    }

    // Step 2: Extraction fields (requires template name + extraction fields)
    if (hasTemplateName && extractionFields.length > 0) {
      completed.add('extraction-fields');
    }

    // Step 3: Pipeline (requires template name + valid pipeline)
    if (
      hasTemplateName &&
      isPipelineValid &&
      !isPipelineValidating
    ) {
      completed.add('pipeline');
    }

    // Step 4: Testing (requires template name - same as step 1-3)
    if (hasTemplateName) {
      completed.add('testing');
    }

    return completed;
  }, [templateId, selectedPages, selectedSignatureObjects, extractionFields, templateName, isPipelineValid, isPipelineValidating]);

  // Navigation handlers
  const handleNext = useCallback(() => {
    if (!canProceed) return;

    if (currentStep === 'page-selection') {
      setCurrentStep('signature-objects');
    } else if (currentStep === 'signature-objects') {
      setCurrentStep('extraction-fields');
    } else if (currentStep === 'extraction-fields') {
      setCurrentStep('pipeline');
    } else if (currentStep === 'pipeline') {
      setCurrentStep('testing');
    }
  }, [currentStep, canProceed]);

  const handleBack = useCallback(() => {
    if (currentStep === 'signature-objects') {
      // Only go back to page-selection if in create mode
      if (!templateId) {
        setCurrentStep('page-selection');
      }
    } else if (currentStep === 'extraction-fields') {
      setCurrentStep('signature-objects');
    } else if (currentStep === 'pipeline') {
      setCurrentStep('extraction-fields');
    } else if (currentStep === 'testing') {
      setCurrentStep('pipeline');
    }
  }, [currentStep, templateId]);

  const handleCancel = useCallback(() => {
    onClose();
  }, [onClose]);

  const handleTest = useCallback(async () => {
    if (!canProceed || !activePdfData) return;

    try {
      const response = await simulateMutation.mutateAsync({
        pdf_objects: activePdfData.objects,
        extraction_fields: extractionFields,
        pipeline_state: pipelineState,
      });
      setSimulationResult(response);
      setCenterTrigger(Date.now());
      // Navigate to testing step
      setCurrentStep('testing');
    } catch (err) {
      console.error('[TemplateBuilder] Simulation failed:', err);
      // Error is handled by mutation
    }
  }, [canProceed, activePdfData, extractionFields, pipelineState, simulateMutation]);

  const handleSave = useCallback(async () => {
    if (!canProceed) return;

    setIsSaving(true);
    try {
      const data: TemplateBuilderData = {
        name: templateName,
        description: templateDescription,
        source_pdf_id: pdfFileId,
        signature_objects: selectedSignatureObjects,
        extraction_fields: extractionFields,
        pipeline_state: pipelineState,
        visual_state: visualState,
      };

      await onSave(data, templateId);
      // Parent will close modal on success
    } catch (error) {
      console.error('[TemplateBuilder] Save failed:', error);
      // Error handling is done by parent
    } finally {
      setIsSaving(false);
    }
  }, [
    canProceed,
    templateId,
    templateName,
    templateDescription,
    pdfFileId,
    selectedSignatureObjects,
    extractionFields,
    pipelineState,
    visualState,
    onSave,
  ]);

  // Don't render if not open
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-gray-900 rounded-lg w-full max-w-[95vw] h-[95vh] overflow-hidden flex flex-col shadow-2xl border border-gray-700">
        {/* Header */}
        <TemplateBuilderHeader
          pdfMetadata={pdfMetadata}
          mode={templateId ? 'version' : 'create'}
          onClose={handleCancel}
        />

        {/* Body - Dynamic Step Content */}
        <div className="flex-1 overflow-hidden min-h-0">
          {/* Loading state for PDF */}
          {isLoadingPdf && (
            <div className="h-full w-full flex items-center justify-center bg-gray-900">
              <div className="text-white text-lg">Loading PDF...</div>
            </div>
          )}

          {/* Error state for PDF */}
          {pdfError && (
            <div className="h-full w-full flex items-center justify-center bg-gray-900">
              <div className="text-center">
                <div className="text-red-400 mb-4">
                  <svg className="mx-auto h-12 w-12 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                  <p className="text-lg font-medium">Failed to load PDF</p>
                  <p className="text-sm text-red-300 mt-2">{pdfError.message}</p>
                </div>
              </div>
            </div>
          )}

          {/* Steps - Only render when PDF data is available */}
          {!isLoadingPdf && !pdfError && activePdfData && (
            <>
              {currentStep === 'page-selection' && (
                <PageSelectionStep
                  pdfUrl={activePdfData.url}
                  selectedPages={selectedPages}
                  onPagesChange={setSelectedPages}
                />
              )}

              {currentStep === 'signature-objects' && (
                <SignatureObjectsStep
                  pdfUrl={activePdfData.url}
                  pdfObjects={activePdfData.objects}
                  templateName={templateName}
                  templateDescription={templateDescription}
                  selectedSignatureObjects={selectedSignatureObjects}
                  selectedPages={!templateId ? selectedPages : undefined}
                  onTemplateNameChange={setTemplateName}
                  onTemplateDescriptionChange={setTemplateDescription}
                  onSignatureObjectsChange={setSelectedSignatureObjects}
                />
              )}

              {currentStep === 'extraction-fields' && (
                <ExtractionFieldsStep
                  pdfUrl={activePdfData.url}
                  pdfObjects={activePdfData.objects}
                  pdfFile={pdfFile}
                  pdfFileId={pdfFileId}
                  templateName={templateName}
                  templateDescription={templateDescription}
                  extractionFields={extractionFields}
                  selectedSignatureObjects={selectedSignatureObjects}
                  selectedPages={!templateId ? selectedPages : undefined}
                  pipelineState={pipelineState}
                  visualState={visualState}
                  onTemplateNameChange={setTemplateName}
                  onTemplateDescriptionChange={setTemplateDescription}
                  onExtractionFieldsChange={setExtractionFields}
                  onPipelineStateChange={setPipelineState}
                  onVisualStateChange={setVisualState}
                />
              )}

              {currentStep === 'pipeline' && (
                <PipelineStep
                  pipelineState={pipelineState}
                  visualState={visualState}
                  onPipelineStateChange={setPipelineState}
                  onVisualStateChange={setVisualState}
                />
              )}

              {currentStep === 'testing' && (
                <TestingStep
                  pdfUrl={activePdfData.url}
                  pdfObjects={activePdfData.objects}
                  extractionFields={extractionFields}
                  pipelineState={pipelineState}
                  viewMode={viewMode}
                  result={simulationResult}
                  isLoading={simulateMutation.isPending}
                  centerTrigger={centerTrigger}
                />
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <TemplateBuilderFooter
          currentStep={currentStep}
          completedSteps={completedSteps}
          canProceed={canProceed}
          validationMessage={validationMessage}
          isSaving={isSaving}
          isTesting={simulateMutation.isPending}
          viewMode={viewMode}
          mode={templateId ? 'version' : 'create'}
          onBack={handleBack}
          onNext={handleNext}
          onTest={handleTest}
          onSave={handleSave}
          onCancel={handleCancel}
          onViewModeChange={setViewMode}
        />
      </div>
    </div>
  );
}
