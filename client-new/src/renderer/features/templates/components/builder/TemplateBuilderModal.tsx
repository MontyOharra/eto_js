/**
 * Template Builder Modal
 * 3-step wizard for creating PDF templates
 */

import { useState } from 'react';
import { SignatureObject, ExtractionField, PipelineState, VisualState } from '../../types';
import { SignatureObjectsStep, ExtractionFieldsStep, PipelineBuilderStep } from './steps';

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

  if (!isOpen || !pdfFileId) return null;

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
    // Reset all state
    setCurrentStep('signature-objects');
    setTemplateName('');
    setTemplateDescription('');
    setSignatureObjects([]);
    setExtractionFields([]);
    setPipelineState({ entry_points: [], modules: [], connections: [] });
    setVisualState({ positions: {} });
    onClose();
  };

  const stepConfig = {
    'signature-objects': {
      title: 'Step 1: Signature Objects',
      description: 'Select PDF objects that uniquely identify this template type',
      canProceed: signatureObjects.length > 0 && templateName.trim().length > 0,
    },
    'extraction-fields': {
      title: 'Step 2: Extraction Fields',
      description: 'Define fields to extract data from the PDF',
      canProceed: extractionFields.length > 0,
    },
    'pipeline': {
      title: 'Step 3: Pipeline Definition',
      description: 'Define how extracted data should be transformed',
      canProceed: true,
    },
  };

  const currentConfig = stepConfig[currentStep];

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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-gray-900 rounded-lg w-full h-full max-w-[95vw] max-h-[95vh] flex flex-col shadow-2xl border border-gray-700">
        {/* Header with Integrated Stepper */}
        <div className="p-4 border-b border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xl font-bold text-white">
              Template Builder
            </h2>
            <button
              onClick={handleClose}
              className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="flex items-center justify-between">
            {/* Stepper Navigation */}
            <div className="flex items-center space-x-4">
              {/* Step 1 */}
              <div className="flex items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  currentStep === 'signature-objects'
                    ? 'bg-blue-600 text-white'
                    : signatureObjects.length > 0
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-700 text-gray-400'
                }`}>
                  {signatureObjects.length > 0 && currentStep !== 'signature-objects' ? '✓' : '1'}
                </div>
                <span className={`ml-2 text-sm font-medium ${
                  currentStep === 'signature-objects' ? 'text-white' : 'text-gray-400'
                }`}>
                  Signature Objects
                </span>
              </div>

              {/* Divider */}
              <div className="w-12 h-0.5 bg-gray-700"></div>

              {/* Step 2 */}
              <div className="flex items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  currentStep === 'extraction-fields'
                    ? 'bg-blue-600 text-white'
                    : extractionFields.length > 0
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-700 text-gray-400'
                }`}>
                  {extractionFields.length > 0 && currentStep !== 'extraction-fields' ? '✓' : '2'}
                </div>
                <span className={`ml-2 text-sm font-medium ${
                  currentStep === 'extraction-fields' ? 'text-white' : 'text-gray-400'
                }`}>
                  Extraction Fields
                </span>
              </div>

              {/* Divider */}
              <div className="w-12 h-0.5 bg-gray-700"></div>

              {/* Step 3 */}
              <div className="flex items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  currentStep === 'pipeline'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-400'
                }`}>
                  3
                </div>
                <span className={`ml-2 text-sm font-medium ${
                  currentStep === 'pipeline' ? 'text-white' : 'text-gray-400'
                }`}>
                  Pipeline
                </span>
              </div>
            </div>

            {/* Step Description */}
            <p className="text-sm text-gray-400">
              {currentConfig.description}
            </p>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          {currentStep === 'signature-objects' && (
            <SignatureObjectsStep
              pdfFileId={pdfFileId}
              templateName={templateName}
              templateDescription={templateDescription}
              signatureObjects={signatureObjects}
              onTemplateNameChange={setTemplateName}
              onTemplateDescriptionChange={setTemplateDescription}
              onSignatureObjectsChange={setSignatureObjects}
            />
          )}
          {currentStep === 'extraction-fields' && (
            <ExtractionFieldsStep
              pdfFileId={pdfFileId}
              extractionFields={extractionFields}
              onExtractionFieldsChange={setExtractionFields}
            />
          )}
          {currentStep === 'pipeline' && (
            <PipelineBuilderStep
              pipelineState={pipelineState}
              visualState={visualState}
              onPipelineStateChange={setPipelineState}
              onVisualStateChange={setVisualState}
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-gray-700 bg-gray-800/30">
          <div className="flex items-center space-x-2">
            {/* Template Name Input - Always visible */}
            <input
              type="text"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              placeholder="Template name..."
              className="px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
              disabled={currentStep !== 'signature-objects'}
            />
            {currentStep === 'signature-objects' && signatureObjects.length > 0 && (
              <span className="text-sm text-gray-400">
                {signatureObjects.length} object{signatureObjects.length !== 1 ? 's' : ''} selected
              </span>
            )}
            {currentStep === 'extraction-fields' && extractionFields.length > 0 && (
              <span className="text-sm text-gray-400">
                {extractionFields.length} field{extractionFields.length !== 1 ? 's' : ''} defined
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2">
            {currentStep !== 'signature-objects' && (
              <button
                onClick={handleBack}
                className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              >
                Back
              </button>
            )}
            {currentStep !== 'pipeline' ? (
              <button
                onClick={handleNext}
                disabled={!currentConfig.canProceed}
                className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
              >
                Next
              </button>
            ) : (
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="px-4 py-2 text-sm bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
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
