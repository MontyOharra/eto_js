/**
 * TemplateDetailFooter
 * Footer component with step navigation and close button
 */

type DetailStep = 'signature-objects' | 'extraction-fields' | 'pipeline';

interface TemplateDetailFooterProps {
  currentStep: DetailStep;
  onBack: () => void;
  onNext: () => void;
  onClose: () => void;
}

export function TemplateDetailFooter({
  currentStep,
  onBack,
  onNext,
  onClose,
}: TemplateDetailFooterProps) {
  const isFirstStep = currentStep === 'signature-objects';
  const isLastStep = currentStep === 'pipeline';

  return (
    <div className="border-t border-gray-700 bg-gray-800 px-6 py-4">
      <div className="flex items-center justify-between">
        {/* Left side: Back button */}
        <button
          onClick={onBack}
          disabled={isFirstStep}
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          ← Back
        </button>

        {/* Center: Step indicator */}
        <div className="flex items-center space-x-2">
          <span
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              currentStep === 'signature-objects'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-400'
            }`}
          >
            1
          </span>
          <span
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              currentStep === 'extraction-fields'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-400'
            }`}
          >
            2
          </span>
          <span
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              currentStep === 'pipeline'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-400'
            }`}
          >
            3
          </span>
        </div>

        {/* Right side: Next/Close buttons */}
        <div className="flex items-center space-x-2">
          {!isLastStep ? (
            <button
              onClick={onNext}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
            >
              Next →
            </button>
          ) : (
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors font-medium"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
