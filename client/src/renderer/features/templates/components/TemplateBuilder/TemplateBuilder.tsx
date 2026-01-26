/**
 * TemplateBuilder
 * Main template builder modal component
 * Manages state for signature objects, extraction fields, and pipeline
 */

import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { TemplateBuilderHeader } from './TemplateBuilderHeader';
import { TemplateBuilderFooter } from './TemplateBuilderFooter';
import { PageSelectionStep } from './PageSelectionStep';
import { SignatureObjectsStep } from './SignatureObjectsStep';
import { ExtractionFieldsStep } from './ExtractionFieldsStep';
import { PipelineStep } from './PipelineStep';
import { TestingStep } from './TestingStep';
import { TemplateCopyModal } from '../TemplateCopyModal';
import type { PdfObjects, ExtractionField } from '../../types';
import type { PipelineState, VisualState } from '../../../pipelines/types';
import { usePdfData, useProcessPdfObjects, createSubsetPdf } from '../../../pdf';
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
  customer_id: number | null;
  source_pdf_id?: number; // Optional: Set by parent after uploading PDF
  signature_objects: PdfObjects;
  extraction_fields: ExtractionField[];
  pipeline_state: PipelineState;
  visual_state: VisualState;
  pdf_file?: File; // Optional: Only provided when PDF needs to be uploaded
  is_autoskip: boolean; // If true, pages matching this template are automatically skipped
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
  const [customerId, setCustomerId] = useState<number | null>(initialData?.customer_id ?? null);

  // Determine if customer selection should be disabled (edit mode with existing customer)
  const disableCustomerChange = initialData?.customer_id != null;

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

  // Autoskip state - if true, template will automatically skip matching pages
  const [isAutoskip, setIsAutoskip] = useState<boolean>(
    initialData?.is_autoskip ?? false
  );

  // Saving state
  const [isSaving, setIsSaving] = useState(false);

  // Copy template modal state
  const [isCopyModalOpen, setIsCopyModalOpen] = useState(false);

  // Track previous selected pages to detect changes
  const prevSelectedPagesRef = useRef<number[]>([]);

  // PDF Data Management - Centralized at TemplateBuilder level
  // Create mode: Process local PDF file
  const { mutateAsync: processObjects, isPending: isProcessing } = useProcessPdfObjects();
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [extractedObjects, setExtractedObjects] = useState<PdfObjects | null>(null);

  // Subset PDF state (only created when user selects partial pages)
  const [subsetPdfFile, setSubsetPdfFile] = useState<File | null>(null);
  const [subsetPdfBlobUrl, setSubsetPdfBlobUrl] = useState<string | null>(null);
  const [isCreatingSubset, setIsCreatingSubset] = useState(false);
  const [subsetCreationError, setSubsetCreationError] = useState<string | null>(null);

  // Edit mode: Fetch PDF data from backend
  const { data: pdfData, isLoading: isFetching, error: fetchError } = usePdfData(
    pdfFileId,
    undefined // Don't filter by pages for stored PDFs - get all objects
  );

  // Reset all state when selected pages change (only in create mode)
  useEffect(() => {
    if (templateId) return; // Only apply in create mode

    // Compare current selectedPages with previous
    const prevPages = prevSelectedPagesRef.current;
    const currentPages = selectedPages;

    // Check if pages have actually changed
    const hasChanged =
      prevPages.length !== currentPages.length ||
      prevPages.some((page, idx) => page !== currentPages[idx]);

    if (hasChanged && prevPages.length > 0) {
      // Pages changed after initial selection - reset all subsequent state
      console.log('[TemplateBuilder] Selected pages changed, resetting all state');

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

      // Clear extracted objects to trigger re-extraction with new pages
      setExtractedObjects(null);

      // Clear subset PDF - will be recreated with new pages
      if (subsetPdfBlobUrl) {
        URL.revokeObjectURL(subsetPdfBlobUrl);
      }
      setSubsetPdfFile(null);
      setSubsetPdfBlobUrl(null);
      setSubsetCreationError(null);

      // Go back to step 1 if we're on a later step
      if (currentStep !== 'page-selection') {
        setCurrentStep('page-selection');
      }
    }

    // Update ref for next comparison
    prevSelectedPagesRef.current = [...currentPages];
  }, [selectedPages, templateId, currentStep]);

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
      setIsAutoskip(false);
      setViewMode('summary');
      setSimulationResult(null);
      setCenterTrigger(0);
      setIsSaving(false);
      setPdfBlobUrl(null);
      setExtractedObjects(null);

      // Clear subset PDF state
      if (subsetPdfBlobUrl) {
        URL.revokeObjectURL(subsetPdfBlobUrl);
      }
      setSubsetPdfFile(null);
      setSubsetPdfBlobUrl(null);
      setSubsetCreationError(null);
      setIsCreatingSubset(false);
    }
  }, [isOpen, templateId, subsetPdfBlobUrl]);

  // Create blob URL immediately when pdfFile is provided (for PageSelectionStep to display PDF)
  useEffect(() => {
    if (pdfFile && !pdfBlobUrl) {
      const blobUrl = URL.createObjectURL(pdfFile);
      setPdfBlobUrl(blobUrl);
      console.log('[TemplateBuilder] Created blob URL for PDF preview');
    }
  }, [pdfFile, pdfBlobUrl]);

  // Create subset PDF when transitioning away from page-selection (only if partial pages selected)
  // This happens automatically when selectedPages changes and we're past page-selection step
  useEffect(() => {
    // Only run in create mode when we have a PDF file
    if (!pdfFile) return;

    // Only run after page selection step
    if (currentStep === 'page-selection') return;

    // Only run if we have selected pages
    if (selectedPages.length === 0) return;

    // If subset already exists and pages haven't changed, don't recreate
    if (subsetPdfFile) return;

    const createSubset = async () => {
      // Always create a new template PDF from selected pages
      // This ensures templates have their own independent PDF files
      console.log(`[TemplateBuilder] Creating template PDF with ${selectedPages.length} pages`);
      setIsCreatingSubset(true);
      setSubsetCreationError(null);

      try {
        const subset = await createSubsetPdf(pdfFile, selectedPages);
        setSubsetPdfFile(subset);

        const blobUrl = URL.createObjectURL(subset);
        setSubsetPdfBlobUrl(blobUrl);

        console.log('[TemplateBuilder] Template PDF created successfully');
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        console.error('[TemplateBuilder] Failed to create template PDF:', errorMsg);
        setSubsetCreationError(errorMsg);
      } finally {
        setIsCreatingSubset(false);
      }
    };

    createSubset();
  }, [pdfFile, currentStep, selectedPages, subsetPdfFile]);

  // Create subset PDF in edit mode (download from backend, then create subset)
  useEffect(() => {
    // Only run in edit mode when we have pdfData
    if (!pdfData || pdfFile) return;

    // Only run after page selection step
    if (currentStep === 'page-selection') return;

    // Only run if we have selected pages
    if (selectedPages.length === 0) return;

    // If subset already exists, don't recreate
    if (subsetPdfFile) return;

    const createSubsetFromBackend = async () => {
      // Always create a new template PDF from selected pages
      // This ensures templates have their own independent PDF files
      console.log(`[TemplateBuilder] Edit mode: Creating template PDF with ${selectedPages.length} pages`);
      setIsCreatingSubset(true);
      setSubsetCreationError(null);

      try {
        // Fetch the PDF file from backend
        const response = await fetch(pdfData.url);
        const blob = await response.blob();
        const pdfFileFromBackend = new File([blob], pdfMetadata?.filename || 'document.pdf', {
          type: 'application/pdf',
        });

        // Create template PDF from selected pages
        const subset = await createSubsetPdf(pdfFileFromBackend, selectedPages);
        setSubsetPdfFile(subset);

        const blobUrl = URL.createObjectURL(subset);
        setSubsetPdfBlobUrl(blobUrl);

        console.log('[TemplateBuilder] Edit mode: Template PDF created successfully');
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        console.error('[TemplateBuilder] Edit mode: Failed to create template PDF:', errorMsg);
        setSubsetCreationError(errorMsg);
      } finally {
        setIsCreatingSubset(false);
      }
    };

    createSubsetFromBackend();
  }, [pdfData, pdfFile, pdfMetadata, currentStep, selectedPages, subsetPdfFile]);

  // Extract objects from the appropriate PDF (original or subset)
  useEffect(() => {
    // Only run after page selection step
    if (currentStep === 'page-selection') return;

    // Don't extract if we already have objects
    if (extractedObjects) return;

    // Determine which PDF to use
    const pdfToProcess = subsetPdfFile || pdfFile;
    if (!pdfToProcess) return;

    const processPdf = async () => {
      try {
        console.log('[TemplateBuilder] Extracting objects from PDF');
        // No pages parameter needed - we're processing the whole PDF (original or subset)
        const result = await processObjects(pdfToProcess);
        setExtractedObjects(result.objects);
      } catch (err) {
        console.error('Failed to process PDF:', err);
      }
    };

    processPdf();
  }, [pdfFile, subsetPdfFile, processObjects, extractedObjects, currentStep]);

  // Cleanup blob URLs ONLY on component unmount (not on re-renders)
  useEffect(() => {
    return () => {
      // Only revoke on unmount, not when URLs change during normal operation
      if (pdfBlobUrl) {
        URL.revokeObjectURL(pdfBlobUrl);
      }
      if (subsetPdfBlobUrl) {
        URL.revokeObjectURL(subsetPdfBlobUrl);
      }
    };
  }, []); // Empty deps = only run on mount/unmount

  // Determine which data source to use
  const isLoadingPdf = pdfFile ? (isProcessing || isCreatingSubset) : isFetching;
  const pdfError = fetchError || subsetCreationError;

  // Normalize data structure (both modes now have same shape: { objects: PdfObjects, url: string })
  // For page-selection step, use original PDF
  // For all other steps, use subset PDF if available, otherwise original PDF
  const activePdfData = useMemo(() => {
    if (pdfFile) {
      // Create mode
      if (currentStep === 'page-selection') {
        // Page selection step: show original PDF
        return pdfBlobUrl ? { objects: null, url: pdfBlobUrl } : null;
      } else {
        // Other steps: show subset PDF if available, otherwise original PDF
        const urlToUse = subsetPdfBlobUrl || pdfBlobUrl;
        return urlToUse ? { objects: extractedObjects, url: urlToUse } : null;
      }
    } else if (pdfData) {
      // Edit mode
      if (currentStep === 'page-selection') {
        // Page selection step: show original PDF from backend
        return { objects: pdfData.objectsData.objects, url: pdfData.url };
      } else {
        // Other steps: show subset PDF if available, otherwise original PDF
        const urlToUse = subsetPdfBlobUrl || pdfData.url;
        const objectsToUse = extractedObjects || pdfData.objectsData.objects;
        return { objects: objectsToUse, url: urlToUse };
      }
    }
    return null;
  }, [pdfFile, pdfBlobUrl, subsetPdfBlobUrl, extractedObjects, pdfData, currentStep]);

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
    // Can't proceed while creating subset PDF
    if (isCreatingSubset) {
      return false;
    }

    // If there was an error creating the subset PDF, can't proceed
    if (subsetCreationError) {
      return false;
    }

    // In create mode (has pdfFile), must have subset PDF created
    // In version mode (no pdfFile), subset is not required (reuse existing template PDF)
    if (pdfFile && !subsetPdfFile && currentStep !== 'page-selection') {
      return false;
    }

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
        // Autoskip templates don't need extraction fields - can save directly
        if (isAutoskip) {
          return true;
        }
        // Normal templates must have at least one extraction field
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
  }, [currentStep, selectedPages, selectedSignatureObjects, extractionFields, templateName, isPipelineValid, isPipelineValidating, isCreatingSubset, subsetCreationError, pdfFile, subsetPdfFile, isAutoskip]);

  const validationMessage = useMemo(() => {
    // Show message while creating subset PDF
    if (isCreatingSubset) {
      return 'Creating template PDF...';
    }

    // Show error if subset PDF creation failed
    if (subsetCreationError) {
      return `Failed to create template PDF: ${subsetCreationError}`;
    }

    // Show message if waiting for subset PDF creation
    if (pdfFile && !subsetPdfFile && currentStep !== 'page-selection') {
      return 'Waiting for template PDF to be created...';
    }

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
        // Autoskip templates can proceed without extraction fields
        if (isAutoskip) {
          return undefined;
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
  }, [canProceed, currentStep, selectedPages, templateName, pipelineState, isPipelineValidating, pipelineValidationError, isCreatingSubset, subsetCreationError, pdfFile, subsetPdfFile, isAutoskip]);

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

    // Step 3: Pipeline (requires template name + valid pipeline with modules)
    const hasPipelineModules = pipelineState.modules.length > 0;
    if (
      hasTemplateName &&
      hasPipelineModules &&
      isPipelineValid &&
      !isPipelineValidating
    ) {
      completed.add('pipeline');
    }

    // Step 4: Testing (no completion criteria - it's a verification step)
    // Users can proceed to save without needing to "complete" this step

    return completed;
  }, [templateId, selectedPages, selectedSignatureObjects, extractionFields, templateName, pipelineState, isPipelineValid, isPipelineValidating]);

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
      // Always use the subset PDF (created from selected pages)
      // Subset PDF is created whenever selectedPages changes in both create and edit modes
      // This ensures templates always have their own independent PDF files
      const pdfToSave = subsetPdfFile || pdfFile;

      console.log('[TemplateBuilder] Saving template:');
      console.log('  pdfFile:', pdfFile?.name);
      console.log('  subsetPdfFile:', subsetPdfFile?.name);
      console.log('  pdfToSave:', pdfToSave?.name);
      console.log('  selectedPages:', selectedPages);
      console.log('  isAutoskip state value:', isAutoskip);

      const data: TemplateBuilderData = {
        name: templateName,
        description: templateDescription,
        customer_id: customerId,
        signature_objects: selectedSignatureObjects,
        extraction_fields: extractionFields,
        pipeline_state: pipelineState,
        visual_state: visualState,
        is_autoskip: isAutoskip,
        ...(pdfToSave && { pdf_file: pdfToSave }),
      };

      console.log('[TemplateBuilder] Template data:', {
        ...data,
        pdf_file: data.pdf_file?.name,
      });
      console.log('[TemplateBuilder] data.is_autoskip:', data.is_autoskip);

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
    customerId,
    pdfFile,
    pdfFileId,
    subsetPdfFile,
    selectedSignatureObjects,
    extractionFields,
    pipelineState,
    visualState,
    isAutoskip,
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

              {currentStep === 'signature-objects' && !activePdfData.objects && (
                <div className="flex items-center justify-center h-full bg-gray-900">
                  <div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4"></div>
                    <p className="text-gray-400">Extracting objects from selected pages...</p>
                  </div>
                </div>
              )}

              {currentStep === 'signature-objects' && activePdfData.objects && (
                <SignatureObjectsStep
                  pdfUrl={activePdfData.url}
                  pdfObjects={activePdfData.objects}
                  templateName={templateName}
                  templateDescription={templateDescription}
                  customerId={customerId}
                  disableCustomerChange={disableCustomerChange}
                  selectedSignatureObjects={selectedSignatureObjects}
                  onTemplateNameChange={setTemplateName}
                  onTemplateDescriptionChange={setTemplateDescription}
                  onCustomerIdChange={setCustomerId}
                  onSignatureObjectsChange={setSelectedSignatureObjects}
                  onCopyFromExisting={() => setIsCopyModalOpen(true)}
                />
              )}

              {currentStep === 'extraction-fields' && activePdfData.objects && (
                <ExtractionFieldsStep
                  pdfUrl={activePdfData.url}
                  templateName={templateName}
                  templateDescription={templateDescription}
                  customerId={customerId}
                  disableCustomerChange={disableCustomerChange}
                  extractionFields={extractionFields}
                  selectedSignatureObjects={selectedSignatureObjects}
                  pipelineState={pipelineState}
                  visualState={visualState}
                  isAutoskip={isAutoskip}
                  onTemplateNameChange={setTemplateName}
                  onTemplateDescriptionChange={setTemplateDescription}
                  onCustomerIdChange={setCustomerId}
                  onExtractionFieldsChange={setExtractionFields}
                  onPipelineStateChange={setPipelineState}
                  onVisualStateChange={setVisualState}
                  onIsAutoskipChange={setIsAutoskip}
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

              {currentStep === 'testing' && activePdfData.objects && (
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
          isAutoskip={isAutoskip}
          onBack={handleBack}
          onNext={handleNext}
          onTest={handleTest}
          onSave={handleSave}
          onCancel={handleCancel}
          onViewModeChange={setViewMode}
        />
      </div>

      {/* Copy Template Modal */}
      <TemplateCopyModal
        isOpen={isCopyModalOpen}
        onClose={() => setIsCopyModalOpen(false)}
        availablePdfObjects={activePdfData?.objects || {
          text_words: [],
          graphic_rects: [],
          graphic_lines: [],
          graphic_curves: [],
          images: [],
          tables: [],
        }}
        onCopyStructure={(signatureObjects, extractionFields, pipelineState, visualState) => {
          setSelectedSignatureObjects(signatureObjects);
          setExtractionFields(extractionFields);
          setPipelineState(pipelineState);
          setVisualState(visualState);
        }}
      />
    </div>
  );
}
