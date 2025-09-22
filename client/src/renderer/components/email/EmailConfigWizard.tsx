import React, { useState, useEffect } from 'react';
import { apiClient } from '../../services/api';

interface FilterRule {
  field: string;
  operation: string;
  value: string;
  case_sensitive: boolean;
}

interface EmailAccount {
  email_address: string;
  display_name: string;
  account_type: string;
  is_default: boolean;
  provider_specific_id?: string;
}

interface EmailFolder {
  name: string;
  full_path: string;
  message_count: number;
  unread_count: number;
  folder_type?: string;
  parent_folder?: string;
}

interface WizardData {
  // Step 1: Email Account
  selectedEmail: string;
  selectedEmailDisplay: string;

  // Step 2: Folder Selection
  selectedFolder: string;

  // Step 3: Configuration
  name: string;
  description: string;
  filter_rules: FilterRule[];
  poll_interval_seconds: number;
  max_backlog_hours: number;
  error_retry_attempts: number;
}

interface EmailConfigWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function EmailConfigWizard({ isOpen, onClose, onSuccess }: EmailConfigWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [folders, setFolders] = useState<EmailFolder[]>([]);

  // Form data
  const [wizardData, setWizardData] = useState<WizardData>({
    selectedEmail: '',
    selectedEmailDisplay: '',
    selectedFolder: '',
    name: '',
    description: '',
    filter_rules: [],
    poll_interval_seconds: 60,
    max_backlog_hours: 24,
    error_retry_attempts: 3,
  });

  // Step 1: Load email accounts when modal opens
  useEffect(() => {
    if (isOpen && currentStep === 1) {
      fetchEmailAccounts();
    }
  }, [isOpen, currentStep]);

  // Step 2: Load folders when email is selected
  useEffect(() => {
    if (currentStep === 2 && wizardData.selectedEmail) {
      fetchFolders(wizardData.selectedEmail);
    }
  }, [currentStep, wizardData.selectedEmail]);

  const fetchEmailAccounts = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.discoverEmailAccounts();
      if (response.success) {
        setAccounts(response.data.emails);
      } else {
        setError('Failed to load email accounts');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load email accounts');
    } finally {
      setLoading(false);
    }
  };

  const fetchFolders = async (emailAddress: string) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.testOutlookFolders(emailAddress);
      if (response.success) {
        setFolders(response.data.folders);
      } else {
        setError('Failed to load email folders');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load email folders');
    } finally {
      setLoading(false);
    }
  };

  const handleNext = () => {
    if (currentStep === 1 && !wizardData.selectedEmail) {
      setError('Please select an email account');
      return;
    }
    if (currentStep === 2 && !wizardData.selectedFolder) {
      setError('Please select a folder');
      return;
    }
    setError(null);
    setCurrentStep(prev => prev + 1);
  };

  const handleBack = () => {
    setError(null);
    setCurrentStep(prev => prev - 1);
  };

  const handleEmailSelect = (account: EmailAccount) => {
    setWizardData(prev => ({
      ...prev,
      selectedEmail: account.email_address,
      selectedEmailDisplay: account.display_name,
      name: `${account.display_name} - Email Monitor` // Auto-generate name
    }));
  };

  const handleFolderSelect = (folder: EmailFolder) => {
    setWizardData(prev => ({
      ...prev,
      selectedFolder: folder.name
    }));
  };

  const addFilterRule = () => {
    setWizardData(prev => ({
      ...prev,
      filter_rules: [
        ...prev.filter_rules,
        {
          field: 'sender_email',
          operation: 'contains',
          value: '',
          case_sensitive: false
        }
      ]
    }));
  };

  const updateFilterRule = (index: number, field: keyof FilterRule, value: string | boolean) => {
    setWizardData(prev => ({
      ...prev,
      filter_rules: prev.filter_rules.map((rule, i) =>
        i === index ? { ...rule, [field]: value } : rule
      )
    }));
  };

  const removeFilterRule = (index: number) => {
    setWizardData(prev => ({
      ...prev,
      filter_rules: prev.filter_rules.filter((_, i) => i !== index)
    }));
  };

  const handleCreate = async () => {
    try {
      setLoading(true);
      setError(null);

      const configData = {
        name: wizardData.name,
        description: wizardData.description,
        email_address: wizardData.selectedEmail,
        folder_name: wizardData.selectedFolder,
        filter_rules: wizardData.filter_rules,
        poll_interval_seconds: wizardData.poll_interval_seconds,
        max_backlog_hours: wizardData.max_backlog_hours,
        error_retry_attempts: wizardData.error_retry_attempts,
      };

      const response = await apiClient.createEmailIngestionConfig(configData);

      if (response.success) {
        onSuccess();
        onClose();
        // Reset wizard
        setCurrentStep(1);
        setWizardData({
          selectedEmail: '',
          selectedEmailDisplay: '',
          selectedFolder: '',
          name: '',
          description: '',
          filter_rules: [],
          poll_interval_seconds: 60,
          max_backlog_hours: 24,
          error_retry_attempts: 3,
        });
      } else {
        setError('Failed to create configuration. Please check your settings and try again.');
      }
    } catch (err) {
      let errorMessage = 'Failed to create configuration';

      if (err instanceof Error) {
        // Try to parse connection test failures from the API error
        const message = err.message;

        // Check if it's a connection test error (HTTP 400 from backend)
        if (message.includes('Connection test failed:')) {
          // Extract the specific connection error
          const testError = message.replace('Connection test failed:', '').trim();
          errorMessage = `Connection test failed: ${testError}`;
        } else if (message.includes('Failed to connect')) {
          errorMessage = 'Failed to connect to the email account. Please check your credentials and try again.';
        } else if (message.includes('Folder') && message.includes('not found')) {
          errorMessage = message; // Use the full folder error message
        } else {
          errorMessage = message;
        }
      }

      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setCurrentStep(1);
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="fixed inset-0 bg-black bg-opacity-50" onClick={handleClose}></div>
      <div className="flex items-center justify-center min-h-screen p-4">
        <div className="relative bg-gray-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto z-10">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-700">
            <h2 className="text-xl font-semibold text-white">
              Create Email Configuration
            </h2>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Progress Steps */}
          <div className="p-6 border-b border-gray-700">
            <div className="flex items-center space-x-4">
              {[1, 2, 3].map((step) => (
                <div key={step} className="flex items-center">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    step < currentStep ? 'bg-green-600 text-white' :
                    step === currentStep ? 'bg-blue-600 text-white' :
                    'bg-gray-600 text-gray-300'
                  }`}>
                    {step < currentStep ? '✓' : step}
                  </div>
                  {step < 3 && (
                    <div className={`w-12 h-1 mx-2 ${
                      step < currentStep ? 'bg-green-600' : 'bg-gray-600'
                    }`}></div>
                  )}
                </div>
              ))}
            </div>
            <div className="mt-2 text-sm text-gray-400">
              Step {currentStep} of 3: {
                currentStep === 1 ? 'Select Email Account' :
                currentStep === 2 ? 'Choose Folder' :
                'Configure Settings'
              }
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            {error && (
              <div className="bg-red-900/20 border border-red-700 rounded-lg p-3 mb-4">
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}

            {loading && (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
                <span className="ml-3 text-gray-400">Loading...</span>
              </div>
            )}

            {/* Step 1: Email Account Selection */}
            {currentStep === 1 && !loading && (
              <div>
                <h3 className="text-lg font-medium text-white mb-4">Select Email Account</h3>
                <p className="text-gray-400 mb-4">Choose the email account you want to monitor</p>

                {accounts.length === 0 ? (
                  <div className="text-center py-8">
                    <p className="text-gray-400">No email accounts found. Make sure Outlook is configured.</p>
                    <button
                      onClick={fetchEmailAccounts}
                      className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                    >
                      Retry
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {accounts.map((account) => (
                      <div
                        key={account.email_address}
                        onClick={() => handleEmailSelect(account)}
                        className={`p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                          wizardData.selectedEmail === account.email_address
                            ? 'border-blue-500 bg-blue-900/20'
                            : 'border-gray-600 hover:border-gray-500 hover:bg-gray-700/50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-medium text-white">{account.display_name}</h4>
                            <p className="text-sm text-gray-400">{account.email_address}</p>
                            <p className="text-xs text-gray-500">{account.account_type}</p>
                          </div>
                          {account.is_default && (
                            <span className="px-2 py-1 bg-green-600 text-white text-xs rounded">
                              Default
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Step 2: Folder Selection */}
            {currentStep === 2 && !loading && (
              <div>
                <h3 className="text-lg font-medium text-white mb-4">Select Folder</h3>
                <p className="text-gray-400 mb-4">
                  Choose the folder to monitor from <strong>{wizardData.selectedEmailDisplay}</strong>
                </p>

                {folders.length === 0 ? (
                  <div className="text-center py-8">
                    <p className="text-gray-400">No folders found for this email account.</p>
                    <button
                      onClick={() => fetchFolders(wizardData.selectedEmail)}
                      className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                    >
                      Retry
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {folders.map((folder) => (
                      <div
                        key={folder.name}
                        onClick={() => handleFolderSelect(folder)}
                        className={`p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                          wizardData.selectedFolder === folder.name
                            ? 'border-blue-500 bg-blue-900/20'
                            : 'border-gray-600 hover:border-gray-500 hover:bg-gray-700/50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-medium text-white">{folder.name}</h4>
                            <p className="text-sm text-gray-400">{folder.full_path}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm text-gray-300">{folder.message_count} messages</p>
                            {folder.unread_count > 0 && (
                              <p className="text-xs text-blue-400">{folder.unread_count} unread</p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Step 3: Configuration */}
            {currentStep === 3 && (
              <div className="space-y-6">
                <h3 className="text-lg font-medium text-white">Configuration Settings</h3>

                {/* Basic Info */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      Configuration Name *
                    </label>
                    <input
                      type="text"
                      value={wizardData.name}
                      onChange={(e) => setWizardData(prev => ({ ...prev, name: e.target.value }))}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Enter configuration name"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      Description
                    </label>
                    <textarea
                      value={wizardData.description}
                      onChange={(e) => setWizardData(prev => ({ ...prev, description: e.target.value }))}
                      rows={3}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Optional description"
                    />
                  </div>
                </div>

                {/* Advanced Settings */}
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      Poll Interval (seconds)
                    </label>
                    <input
                      type="number"
                      min="5"
                      value={wizardData.poll_interval_seconds}
                      onChange={(e) => setWizardData(prev => ({ ...prev, poll_interval_seconds: parseInt(e.target.value) }))}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      Max Backlog (hours)
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={wizardData.max_backlog_hours}
                      onChange={(e) => setWizardData(prev => ({ ...prev, max_backlog_hours: parseInt(e.target.value) }))}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      Retry Attempts
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={wizardData.error_retry_attempts}
                      onChange={(e) => setWizardData(prev => ({ ...prev, error_retry_attempts: parseInt(e.target.value) }))}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </div>

                {/* Filter Rules */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <label className="block text-sm font-medium text-gray-300">
                      Email Filter Rules
                    </label>
                    <button
                      type="button"
                      onClick={addFilterRule}
                      className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors"
                    >
                      Add Rule
                    </button>
                  </div>

                  {wizardData.filter_rules.length === 0 ? (
                    <p className="text-gray-400 text-sm py-4 text-center">
                      No filter rules added. All emails will be processed.
                    </p>
                  ) : (
                    <div className="space-y-3">
                      {wizardData.filter_rules.map((rule, index) => (
                        <div key={index} className="flex items-center space-x-2 p-3 bg-gray-700 rounded-md">
                          <select
                            value={rule.field}
                            onChange={(e) => updateFilterRule(index, 'field', e.target.value)}
                            className="px-2 py-1 bg-gray-600 border border-gray-500 rounded text-white text-sm"
                          >
                            <option value="sender_email">Sender Email</option>
                            <option value="subject">Subject</option>
                            <option value="has_attachments">Has Attachments</option>
                            <option value="received_date">Received Date</option>
                          </select>

                          <select
                            value={rule.operation}
                            onChange={(e) => updateFilterRule(index, 'operation', e.target.value)}
                            className="px-2 py-1 bg-gray-600 border border-gray-500 rounded text-white text-sm"
                          >
                            <option value="contains">Contains</option>
                            <option value="equals">Equals</option>
                            <option value="starts_with">Starts With</option>
                            <option value="ends_with">Ends With</option>
                            <option value="before">Before</option>
                            <option value="after">After</option>
                          </select>

                          <input
                            type="text"
                            value={rule.value}
                            onChange={(e) => updateFilterRule(index, 'value', e.target.value)}
                            placeholder="Value"
                            className="flex-1 px-2 py-1 bg-gray-600 border border-gray-500 rounded text-white text-sm placeholder-gray-400"
                          />

                          <label className="flex items-center text-sm text-gray-300">
                            <input
                              type="checkbox"
                              checked={rule.case_sensitive}
                              onChange={(e) => updateFilterRule(index, 'case_sensitive', e.target.checked)}
                              className="mr-1"
                            />
                            Case sensitive
                          </label>

                          <button
                            type="button"
                            onClick={() => removeFilterRule(index)}
                            className="px-2 py-1 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors"
                          >
                            Remove
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Selected Info Summary */}
                <div className="bg-gray-700 p-4 rounded-lg">
                  <h4 className="text-sm font-medium text-gray-300 mb-2">Configuration Summary</h4>
                  <div className="text-sm text-gray-400 space-y-1">
                    <p><strong>Email:</strong> {wizardData.selectedEmail}</p>
                    <p><strong>Folder:</strong> {wizardData.selectedFolder}</p>
                    <p><strong>Poll Interval:</strong> {wizardData.poll_interval_seconds} seconds</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between p-6 border-t border-gray-700">
            <div>
              {currentStep > 1 && (
                <button
                  onClick={handleBack}
                  disabled={loading}
                  className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Back
                </button>
              )}
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={handleClose}
                disabled={loading}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>

              {currentStep < 3 ? (
                <button
                  onClick={handleNext}
                  disabled={loading || (currentStep === 1 && !wizardData.selectedEmail) || (currentStep === 2 && !wizardData.selectedFolder)}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              ) : (
                <button
                  onClick={handleCreate}
                  disabled={loading || !wizardData.name.trim()}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Creating...' : 'Create Configuration'}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}