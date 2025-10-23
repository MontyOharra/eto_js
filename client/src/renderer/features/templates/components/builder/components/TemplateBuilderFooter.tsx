/**
 * TemplateBuilderFooter
 * Action buttons for navigating between steps and saving
 */

type BuilderStep = 'signature-objects' | 'extraction-fields' | 'pipeline';

interface TemplateBuilderFooterProps {
  currentStep: BuilderStep;
  canProceed: boolean;
  validationMessage?: string;
  isSaving?: boolean;
  onBack: () => void;
  onNext: () => void;
  onSave: () => void;
  onCancel: () => void;
}

export function TemplateBuilderFooter({
  currentStep,
  canProceed,
  validationMessage,
  isSaving = false,
  onBack,
  onNext,
  onSave,
  onCancel,
}: TemplateBuilderFooterProps) {
  const isFirstStep = currentStep === 'signature-objects';
  const isLastStep = currentStep === 'pipeline';

  return (
    <div className="flex items-center justify-between p-4 border-t border-gray-700 flex-shrink-0 bg-gray-900">
      {/* Validation Message / Help Text */}
      <div className="flex-1 text-sm text-gray-400">
        {validationMessage && !canProceed && (
          <span className="text-amber-400">{validationMessage}</span>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex items-center space-x-3">
        {/* Back Button */}
        {!isFirstStep && (
          <button
            onClick={onBack}
            disabled={isSaving}
            className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
          >
            ← Back
          </button>
        )}

        {/* Cancel Button */}
        <button
          onClick={onCancel}
          disabled={isSaving}
          className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
        >
          Cancel
        </button>

        {/* Next / Save Button */}
        {isLastStep ? (
          <button
            onClick={onSave}
            disabled={!canProceed || isSaving}
            className="px-6 py-2 text-sm bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
          >
            {isSaving ? 'Saving...' : 'Save Template'}
          </button>
        ) : (
          <button
            onClick={onNext}
            disabled={!canProceed}
            className="px-6 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
          >
            Next →
          </button>
        )}
      </div>
    </div>
  );
}
