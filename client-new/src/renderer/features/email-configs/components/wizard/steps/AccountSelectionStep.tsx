/**
 * Account Selection Step (Step 1)
 * Allows user to select an email account to monitor
 */

import type { EmailAccount } from '../../../types';

interface AccountSelectionStepProps {
  accounts: EmailAccount[];
  selectedAccount: string | null;
  isLoading: boolean;
  onSelectAccount: (account: EmailAccount) => void;
  onRetry: () => void;
}

export function AccountSelectionStep({
  accounts,
  selectedAccount,
  isLoading,
  onSelectAccount,
  onRetry,
}: AccountSelectionStepProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
        <span className="ml-3 text-gray-400">Loading email accounts...</span>
      </div>
    );
  }

  if (accounts.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400 mb-4">
          No email accounts found. Make sure email service is configured.
        </p>
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-lg font-medium text-white mb-2">Select Email Account</h3>
      <p className="text-gray-400 mb-4">
        Choose the email account you want to monitor for PDF documents
      </p>

      <div className="space-y-3">
        {accounts.map((account) => (
          <button
            key={account.email_address}
            onClick={() => onSelectAccount(account)}
            className={`w-full text-left p-4 border-2 rounded-lg transition-colors ${
              selectedAccount === account.email_address
                ? 'border-blue-500 bg-blue-900/20'
                : 'border-gray-600 hover:border-gray-500 hover:bg-gray-700/50'
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-white">
                  {account.display_name || account.email_address}
                </h4>
                <p className="text-sm text-gray-400">{account.email_address}</p>
              </div>
              {selectedAccount === account.email_address && (
                <svg className="w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
