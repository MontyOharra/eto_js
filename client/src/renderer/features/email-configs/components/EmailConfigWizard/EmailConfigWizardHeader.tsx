/**
 * Email Config Wizard Header
 * Title, close button, and progress indicator for the wizard
 */

type WizardStep = 'account' | 'folder' | 'configuration';

interface EmailConfigWizardHeaderProps {
  currentStep: WizardStep;
  stepTitle: string;
  isAccountComplete: boolean;
  isFolderComplete: boolean;
  onClose: () => void;
}

export function EmailConfigWizardHeader({
  currentStep,
  stepTitle,
  isAccountComplete,
  isFolderComplete,
  onClose,
}: EmailConfigWizardHeaderProps) {
  return (
    <>
      {/* Title Bar */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Create Email Configuration</h2>
          <p className="text-sm text-gray-400">{stepTitle}</p>
        </div>
        <button
          onClick={onClose}
          className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      {/* Progress Steps */}
      <div className="px-4 py-3 border-b border-gray-700 bg-gray-800/50">
        <div className="flex items-center justify-center space-x-2">
          {/* Step 1 - Account */}
          <div className="flex items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                currentStep === 'account'
                  ? 'bg-blue-600 text-white'
                  : isAccountComplete
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-700 text-gray-400'
              }`}
            >
              {isAccountComplete && currentStep !== 'account' ? '✓' : '1'}
            </div>
            <span
              className={`ml-2 text-sm font-medium ${
                currentStep === 'account' ? 'text-white' : 'text-gray-400'
              }`}
            >
              Account
            </span>
          </div>

          <div className="w-8 h-0.5 bg-gray-700"></div>

          {/* Step 2 - Folder */}
          <div className="flex items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                currentStep === 'folder'
                  ? 'bg-blue-600 text-white'
                  : isFolderComplete
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-700 text-gray-400'
              }`}
            >
              {isFolderComplete && currentStep !== 'folder' ? '✓' : '2'}
            </div>
            <span
              className={`ml-2 text-sm font-medium ${
                currentStep === 'folder' ? 'text-white' : 'text-gray-400'
              }`}
            >
              Folder
            </span>
          </div>

          <div className="w-8 h-0.5 bg-gray-700"></div>

          {/* Step 3 - Configuration */}
          <div className="flex items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                currentStep === 'configuration'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-400'
              }`}
            >
              3
            </div>
            <span
              className={`ml-2 text-sm font-medium ${
                currentStep === 'configuration' ? 'text-white' : 'text-gray-400'
              }`}
            >
              Settings
            </span>
          </div>
        </div>
      </div>
    </>
  );
}
