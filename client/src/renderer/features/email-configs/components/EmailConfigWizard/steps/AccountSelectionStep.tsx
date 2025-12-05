/**
 * Account Selection Step
 * First step in email config wizard - select from existing email accounts
 */

import type { EmailAccountSummary } from '../../../../email-accounts';

interface AccountSelectionStepProps {
  accounts: EmailAccountSummary[];
  selectedAccountId: number | null;
  isLoading: boolean;
  error: string | null;
  onSelectAccount: (account: EmailAccountSummary) => void;
  onRetry: () => void;
}

export function AccountSelectionStep({
  accounts,
  selectedAccountId,
  isLoading,
  error,
  onSelectAccount,
  onRetry,
}: AccountSelectionStepProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <svg className="animate-spin h-8 w-8 text-blue-500 mb-4" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p className="text-gray-400">Loading email accounts...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="text-red-400 mb-4">
          <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <p className="text-red-400 mb-4">{error}</p>
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (accounts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="text-gray-500 mb-4">
          <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-300 mb-2">No email accounts configured</h3>
        <p className="text-gray-500 text-center max-w-md">
          You need to add an email account before creating an ingestion configuration.
          Go to Settings to add your first email connection.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-white mb-2">Select Email Account</h3>
        <p className="text-sm text-gray-400">
          Choose which email account to monitor for this configuration
        </p>
      </div>

      <div className="space-y-3">
        {accounts.map((account) => {
          const isSelected = selectedAccountId === account.id;
          return (
            <button
              key={account.id}
              onClick={() => onSelectAccount(account)}
              className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
                isSelected
                  ? 'border-blue-600 bg-blue-600/10'
                  : 'border-gray-700 bg-gray-800 hover:border-gray-600 hover:bg-gray-750'
              }`}
            >
              <div className="flex items-center space-x-4">
                {/* Icon */}
                <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
                  isSelected ? 'bg-blue-600/20 text-blue-400' : 'bg-gray-700 text-gray-400'
                }`}>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-1">
                    <h4 className="text-base font-semibold text-white truncate">{account.name}</h4>
                    {!account.is_validated && (
                      <span className="text-xs px-2 py-0.5 rounded bg-yellow-600/20 text-yellow-400">
                        Not Validated
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-400 truncate">{account.email_address}</p>
                </div>

                {/* Selection Indicator */}
                <div className="flex-shrink-0">
                  <div
                    className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                      isSelected
                        ? 'border-blue-600 bg-blue-600'
                        : 'border-gray-600'
                    }`}
                  >
                    {isSelected && (
                      <svg
                        className="w-3 h-3 text-white"
                        fill="currentColor"
                        viewBox="0 0 12 12"
                      >
                        <path d="M10 3L4.5 8.5L2 6" stroke="currentColor" strokeWidth="2" fill="none" />
                      </svg>
                    )}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Info Box */}
      <div className="mt-6 p-4 rounded-lg bg-blue-600/10 border border-blue-600/30">
        <div className="flex items-start space-x-3">
          <div className="text-blue-400 flex-shrink-0 mt-0.5">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="flex-1">
            <h5 className="text-sm font-medium text-blue-400 mb-1">Need a different account?</h5>
            <p className="text-sm text-gray-300 leading-relaxed">
              You can add new email accounts in Settings. Each account can be used for multiple ingestion configurations.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
