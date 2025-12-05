/**
 * Email Config Wizard Footer
 * Navigation and action buttons for the wizard
 */

type WizardStep = 'account' | 'folder' | 'configuration';

interface EmailConfigWizardFooterProps {
  currentStep: WizardStep;
  canProceed: boolean;
  isSaving: boolean;
  showLoadFolders: boolean;
  onClose: () => void;
  onBack: () => void;
  onNext: () => void;
  onSave: () => void;
  onLoadFolders: () => void;
}

export function EmailConfigWizardFooter({
  currentStep,
  canProceed,
  isSaving,
  showLoadFolders,
  onClose,
  onBack,
  onNext,
  onSave,
  onLoadFolders,
}: EmailConfigWizardFooterProps) {
  return (
    <div className="flex items-center justify-between p-4 border-t border-gray-700 bg-gray-800/30">
      <button
        onClick={onClose}
        className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
      >
        Cancel
      </button>

      <div className="flex items-center space-x-3">
        {/* Load Folders button (only show on folder step) */}
        {showLoadFolders && (
          <button
            onClick={onLoadFolders}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
          >
            Load Folders
          </button>
        )}

        {/* Back button (hide on first step) */}
        {currentStep !== 'account' && (
          <button
            onClick={onBack}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
          >
            Back
          </button>
        )}

        {/* Next button - show before configuration step */}
        {currentStep !== 'configuration' ? (
          <button
            onClick={onNext}
            disabled={!canProceed}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded transition-colors"
          >
            Next
          </button>
        ) : (
          <button
            onClick={onSave}
            disabled={!canProceed || isSaving}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded transition-colors"
          >
            {isSaving ? 'Creating...' : 'Create Configuration'}
          </button>
        )}
      </div>
    </div>
  );
}
