/**
 * Template Builder Modal
 * 3-step wizard for creating PDF templates
 */

import { useState, useMemo } from 'react';
import { SignatureObject, ExtractionField, PipelineState, VisualState } from '../../types';
import { SignatureObjectsStep, ExtractionFieldsStep, PipelineBuilderStep } from './steps';
import { TemplateBuilderHeader, TemplateBuilderStepper } from './components';
import { usePdfData } from '../../../pdf-files/hooks/usePdfData';

interface TemplateBuilderModalProps {
  isOpen: boolean;
  pdfFileId: number | null;
  onClose: () => void;
  onSave: (templateData: TemplateData) => Promise<void>;
}

export interface TemplateData {
  name: string;
  description: string;
  source_pdf_id: number;
  signature_objects: SignatureObject[];
  extraction_fields: ExtractionField[];
  pipeline_state: PipelineState;
  visual_state: VisualState;
}

type BuilderStep = 'signature-objects' | 'extraction-fields' | 'pipeline';

export function TemplateBuilderModal({
  isOpen,
  pdfFileId,
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
    positions: {},
  });
  const [isSaving, setIsSaving] = useState(false);

  // PDF viewer state persistence across steps
  const [pdfScale, setPdfScale] = useState<number>(1.0);
  const [pdfCurrentPage, setPdfCurrentPage] = useState<number>(1);

  // Use React Query to fetch and cache PDF data
  const { data: pdfData, isLoading: pdfLoading, error: pdfError } = usePdfData(pdfFileId);

  // Extract PDF data from query result
  const pdfObjects = pdfData?.objectsData;
  const pdfUrl = pdfData?.url || '';
  const pdfDataLoaded = !!pdfData;

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
        return true;
      default:
        return false;
    }
  }, [currentStep, signatureObjects.length, templateName, extractionFields.length]);

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
      default:
        return undefined;
    }
  }, [currentStep, canProceed, templateName, signatureObjects.length]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave({
        name: templateName,
        description: templateDescription,
        source_pdf_id: pdfFileId,
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

  const handleClose = () => {
    // Reset all state (PDF data is cached by React Query, no need to reset)
    setCurrentStep('signature-objects');
    setTemplateName('');
    setTemplateDescription('');
    setSignatureObjects([]);
    setSelectedObjectTypes([]);
    setExtractionFields([]);
    setPipelineState({ entry_points: [], modules: [], connections: [] });
    setVisualState({ positions: {} });
    setPdfScale(1.0);
    setPdfCurrentPage(1);
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
    }
  };

  // Early return after all hooks are defined
  if (!isOpen || !pdfFileId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-gray-900 rounded-lg w-full h-full max-w-[95vw] max-h-[95vh] flex flex-col shadow-2xl border border-gray-700">
        {/* Header */}
        <TemplateBuilderHeader
          pdfFileName={`${pdfFileId}.pdf`}
          onClose={handleClose}
        />

        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          {/* Loading State - only show during initial load */}
          {!pdfDataLoaded && pdfLoading && (
            <div className="h-full flex items-center justify-center">
              <div className="text-white text-lg">Loading PDF...</div>
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
              <div
                className="h-full w-full"
                style={{ display: currentStep === 'signature-objects' ? 'flex' : 'none' }}
              >
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
              </div>
              <div
                className="h-full w-full"
                style={{ display: currentStep === 'extraction-fields' ? 'flex' : 'none' }}
              >
                <ExtractionFieldsStep
                  pdfFileId={pdfFileId}
                  templateName={templateName}
                  templateDescription={templateDescription}
                  extractionFields={extractionFields}
                  signatureObjects={signatureObjects}
                  pdfObjects={pdfObjects}
                  pdfUrl={pdfUrl}
                  onTemplateNameChange={setTemplateName}
                  onTemplateDescriptionChange={setTemplateDescription}
                  onExtractionFieldsChange={setExtractionFields}
                  pdfScale={pdfScale}
                  pdfCurrentPage={pdfCurrentPage}
                  onPdfScaleChange={setPdfScale}
                  onPdfCurrentPageChange={setPdfCurrentPage}
                />
              </div>
              <div
                className="h-full w-full"
                style={{ display: currentStep === 'pipeline' ? 'flex' : 'none' }}
              >
                <PipelineBuilderStep
                  extractionFields={extractionFields}
                  pipelineState={pipelineState}
                  visualState={visualState}
                  onPipelineStateChange={setPipelineState}
                  onVisualStateChange={setVisualState}
                />
              </div>
            </>
          )}
        </div>

        {/* Footer - Stepper with Navigation Buttons */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-700 bg-gray-900">
          <TemplateBuilderStepper
            currentStep={currentStep}
            completedSteps={completedSteps}
          />

          {/* Navigation Buttons */}
          <div className="flex items-center space-x-3">
            {currentStep !== 'signature-objects' && (
              <button
                onClick={handleBack}
                disabled={isSaving}
                className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
              >
                ← Back
              </button>
            )}

            {currentStep !== 'pipeline' ? (
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
            ) : (
              <button
                onClick={handleSave}
                disabled={!canProceed || isSaving}
                className="px-6 py-2 text-sm bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
              >
                {isSaving ? 'Saving...' : 'Save Template'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
