/**
 * TemplateBuilderFooter
 * Action buttons for navigating between steps and saving
 * Includes step progress indicator
 */

type BuilderStep = 'signature-objects' | 'extraction-fields' | 'pipeline' | 'testing';

interface StepConfig {
  id: BuilderStep;
  number: number;
  label: string;
}

const STEPS: StepConfig[] = [
  { id: 'signature-objects', number: 1, label: 'Signature Objects' },
  { id: 'extraction-fields', number: 2, label: 'Extraction Fields' },
  { id: 'pipeline', number: 3, label: 'Pipeline' },
  { id: 'testing', number: 4, label: 'Testing' },
];

interface TemplateBuilderFooterProps {
  currentStep: BuilderStep;
  completedSteps: Set<BuilderStep>;
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
  completedSteps,
  canProceed,
  validationMessage,
  isSaving = false,
  onBack,
  onNext,
  onSave,
  onCancel,
}: TemplateBuilderFooterProps) {
  const isFirstStep = currentStep === 'signature-objects';
  const isLastStep = currentStep === 'testing';
  const currentStepNumber = STEPS.find((s) => s.id === currentStep)?.number || 1;

  return (
    <div className="flex items-center justify-between p-4 border-t border-gray-700 flex-shrink-0 bg-gray-900">
      {/* Left Section: Step Indicator */}
      <div className="flex items-center space-x-3">
        {STEPS.map((step, index) => {
          const isActive = step.id === currentStep;
          const isCompleted = completedSteps.has(step.id);
          const isPast = step.number < currentStepNumber;

          return (
            <div key={step.id} className="flex items-center">
              {/* Step Circle */}
              <div className="flex items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white'
                      : isCompleted || isPast
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-700 text-gray-400'
                  }`}
                >
                  {isCompleted || isPast ? (
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : (
                    step.number
                  )}
                </div>
                <span
                  className={`ml-2 text-sm font-medium ${
                    isActive ? 'text-white' : 'text-gray-400'
                  }`}
                >
                  {step.label}
                </span>
              </div>

              {/* Divider */}
              {index < STEPS.length - 1 && (
                <div className="w-12 h-0.5 bg-gray-700 mx-3"></div>
              )}
            </div>
          );
        })}
      </div>

      {/* Spacer to push buttons to the right */}
      <div className="flex-1"></div>

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

        {/* Next / Save Button with Tooltip */}
        {isLastStep ? (
          <div className="relative group">
            <button
              onClick={onSave}
              disabled={!canProceed || isSaving}
              className="px-6 py-2 text-sm bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
            >
              {isSaving ? 'Saving...' : 'Save Template'}
            </button>
            {/* Tooltip - only show when button is disabled and there's a validation message */}
            {!canProceed && validationMessage && (
              <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block">
                <div className="bg-gray-800 text-amber-400 text-xs rounded-lg py-2 px-3 whitespace-nowrap shadow-lg border border-gray-700">
                  {validationMessage}
                  {/* Arrow pointing down */}
                  <div className="absolute top-full right-4 -mt-1">
                    <div className="border-4 border-transparent border-t-gray-800"></div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="relative group">
            <button
              onClick={onNext}
              disabled={!canProceed}
              className="px-6 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
            >
              Next →
            </button>
            {/* Tooltip - only show when button is disabled and there's a validation message */}
            {!canProceed && validationMessage && (
              <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block">
                <div className="bg-gray-800 text-amber-400 text-xs rounded-lg py-2 px-3 whitespace-nowrap shadow-lg border border-gray-700">
                  {validationMessage}
                  {/* Arrow pointing down */}
                  <div className="absolute top-full right-4 -mt-1">
                    <div className="border-4 border-transparent border-t-gray-800"></div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
