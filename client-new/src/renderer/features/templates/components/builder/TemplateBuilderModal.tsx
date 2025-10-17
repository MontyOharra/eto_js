/**
 * Template Builder Modal
 * 3-step wizard for creating PDF templates
 */

import { useState, useMemo } from 'react';
import { SignatureObject, ExtractionField, PipelineState, VisualState } from '../../types';
import { SignatureObjectsStep, ExtractionFieldsStep, PipelineBuilderStep } from './steps';
import { TemplateBuilderHeader, TemplateBuilderStepper, TemplateBuilderFooter } from './components';

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
        {/* Header */}
        <TemplateBuilderHeader
          templateName={templateName || 'Template Builder'}
          pdfFileName={`${pdfFileId}.pdf`}
          onClose={handleClose}
        />

        {/* Stepper */}
        <TemplateBuilderStepper
          currentStep={currentStep}
          completedSteps={completedSteps}
        />

        {/* Template Name Input - Only on Step 1 */}
        {currentStep === 'signature-objects' && (
          <div className="px-6 py-4 border-b border-gray-700">
            <div className="space-y-3">
              <div>
                <label htmlFor="template-name" className="block text-sm font-medium text-gray-300 mb-2">
                  Template Name *
                </label>
                <input
                  id="template-name"
                  type="text"
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  placeholder="Enter template name..."
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label htmlFor="template-description" className="block text-sm font-medium text-gray-300 mb-2">
                  Description
                </label>
                <textarea
                  id="template-description"
                  value={templateDescription}
                  onChange={(e) => setTemplateDescription(e.target.value)}
                  placeholder="Enter template description (optional)..."
                  rows={2}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none"
                />
              </div>
            </div>
          </div>
        )}

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
        <TemplateBuilderFooter
          currentStep={currentStep}
          canProceed={canProceed}
          validationMessage={validationMessage}
          isSaving={isSaving}
          onBack={handleBack}
          onNext={handleNext}
          onSave={handleSave}
          onCancel={handleClose}
        />
      </div>
    </div>
  );
}
