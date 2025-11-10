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
    <div className="flex items-center justify-between p-4 border-t border-gray-700 flex-shrink-0 bg-gray-900">
      {/* Left Section: Step Indicator */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
              currentStep === 'signature-objects'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-400'
            }`}
          >
            1
          </div>
          <span
            className={`ml-2 text-sm font-medium ${
              currentStep === 'signature-objects' ? 'text-white' : 'text-gray-400'
            }`}
          >
            Signature Objects
          </span>
        </div>
        <div className="w-12 h-0.5 bg-gray-700"></div>
        <div className="flex items-center">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
              currentStep === 'extraction-fields'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-400'
            }`}
          >
            2
          </div>
          <span
            className={`ml-2 text-sm font-medium ${
              currentStep === 'extraction-fields' ? 'text-white' : 'text-gray-400'
            }`}
          >
            Extraction Fields
          </span>
        </div>
        <div className="w-12 h-0.5 bg-gray-700"></div>
        <div className="flex items-center">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
              currentStep === 'pipeline'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-400'
            }`}
          >
            3
          </div>
          <span
            className={`ml-2 text-sm font-medium ${
              currentStep === 'pipeline' ? 'text-white' : 'text-gray-400'
            }`}
          >
            Pipeline
          </span>
        </div>
      </div>

      {/* Spacer to push buttons to the right */}
      <div className="flex-1"></div>

      {/* Action Buttons */}
      <div className="flex items-center space-x-3">
        {/* Back Button */}
        {!isFirstStep && (
          <button
            onClick={onBack}
            className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
          >
            ← Back
          </button>
        )}

        {/* Close Button - always shown */}
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
        >
          Close
        </button>

        {/* Next Button - only show when not on last step */}
        {!isLastStep && (
          <button
            onClick={onNext}
            className="px-6 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
          >
            Next →
          </button>
        )}
      </div>
    </div>
  );
}
