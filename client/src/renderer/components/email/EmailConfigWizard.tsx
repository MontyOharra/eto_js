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
  account_type: number;
  is_default: boolean;
}

interface EmailFolder {
  name: string;
  path: string;
  count: number;
}

interface WizardData {
  // Step 1: Basic Info
  name: string;
  description: string;

  // Step 2: Email Account
  selectedEmail: string;

  // Step 3: Folder Selection
  selectedFolder: string;

  // Step 4: Advanced Settings
  poll_interval_seconds: number;
  max_backlog_hours: number;
  error_retry_attempts: number;
  filter_rules: FilterRule[];
}

interface EmailConfigWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

type WizardStep = 1 | 2 | 3 | 4;

export function EmailConfigWizard({ isOpen, onClose, onSuccess }: EmailConfigWizardProps) {
  const [currentStep, setCurrentStep] = useState<WizardStep>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [wizardData, setWizardData] = useState<WizardData>({
    name: '',
    description: '',
    selectedEmail: '',
    selectedFolder: '',
    poll_interval_seconds: 60,
    max_backlog_hours: 24,
    error_retry_attempts: 3,
    filter_rules: []
  });

  // Step-specific states
  const [availableEmails, setAvailableEmails] = useState<EmailAccount[]>([]);
  const [availableFolders, setAvailableFolders] = useState<EmailFolder[]>([]);
  const [loadingEmails, setLoadingEmails] = useState(false);
  const [loadingFolders, setLoadingFolders] = useState(false);

  // Load available emails when wizard opens
  useEffect(() => {
    if (isOpen && currentStep === 2) {
      loadAvailableEmails();
    }
  }, [isOpen, currentStep]);

  // Load folders when email is selected
  useEffect(() => {
    if (currentStep === 3 && wizardData.selectedEmail) {
      loadAvailableFolders();
    }
  }, [currentStep, wizardData.selectedEmail]);

  const loadAvailableEmails = async () => {
    try {
      setLoadingEmails(true);
      const response = await apiClient.discoverEmailAccounts();
      if (response.success) {
        setAvailableEmails(response.data.emails);
      }
    } catch (err) {
      setError('Failed to load email accounts');
    } finally {
      setLoadingEmails(false);
    }
  };

  const loadAvailableFolders = async () => {
    try {
      setLoadingFolders(true);
      const response = await apiClient.testOutlookFolders(wizardData.selectedEmail);
      if (response.success && response.data.folders.length > 0) {
        setAvailableFolders(response.data.folders[0].folders);
      }
    } catch (err) {
      setError('Failed to load folders for selected email');
    } finally {
      setLoadingFolders(false);
    }
  };

  const updateWizardData = (updates: Partial<WizardData>) => {
    setWizardData(prev => ({ ...prev, ...updates }));
  };

  const addFilterRule = () => {
    const newRule: FilterRule = {
      field: 'sender_email',
      operation: 'equals',
      value: '',
      case_sensitive: false
    };
    updateWizardData({
      filter_rules: [...wizardData.filter_rules, newRule]
    });
  };

  const updateFilterRule = (index: number, updates: Partial<FilterRule>) => {
    const updatedRules = wizardData.filter_rules.map((rule, i) =>
      i === index ? { ...rule, ...updates } : rule
    );
    updateWizardData({ filter_rules: updatedRules });
  };

  const removeFilterRule = (index: number) => {
    const updatedRules = wizardData.filter_rules.filter((_, i) => i !== index);
    updateWizardData({ filter_rules: updatedRules });
  };

  const canProceedToNextStep = (): boolean => {
    switch (currentStep) {
      case 1:
        return wizardData.name.trim() !== '';
      case 2:
        return wizardData.selectedEmail !== '';
      case 3:
        return wizardData.selectedFolder !== '';
      case 4:
        return true; // Always can proceed from advanced settings
      default:
        return false;
    }
  };

  const handleNext = () => {
    if (canProceedToNextStep() && currentStep < 4) {
      setCurrentStep((prev) => (prev + 1) as WizardStep);
      setError(null);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => (prev - 1) as WizardStep);
      setError(null);
    }
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      setError(null);

      const configData = {
        name: wizardData.name,
        description: wizardData.description || undefined,
        connection: {
          email_address: wizardData.selectedEmail,
          folder_name: wizardData.selectedFolder
        },
        filter_rules: wizardData.filter_rules.length > 0 ? wizardData.filter_rules : undefined,
        monitoring: {
          poll_interval_seconds: wizardData.poll_interval_seconds,
          max_backlog_hours: wizardData.max_backlog_hours,
          error_retry_attempts: wizardData.error_retry_attempts
        },
        created_by: 'user'
      };

      const response = await apiClient.createEmailIngestionConfig(configData);

      if (response.success) {
        onSuccess();
        handleClose();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setCurrentStep(1);
    setWizardData({
      name: '',
      description: '',
      selectedEmail: '',
      selectedFolder: '',
      poll_interval_seconds: 60,
      max_backlog_hours: 24,
      error_retry_attempts: 3,
      filter_rules: []
    });
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  const stepTitles = {
    1: 'Basic Information',
    2: 'Select Email Account',
    3: 'Choose Folder',
    4: 'Advanced Settings'
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold text-white">Create Email Configuration</h2>
            <p className="text-gray-400 text-sm">Step {currentStep} of 4: {stepTitles[currentStep]}</p>
          </div>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-200"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex justify-between items-center mb-2">
            {[1, 2, 3, 4].map((step) => (
              <div
                key={step}
                className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
                  step <= currentStep
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-600 text-gray-400'
                }`}
              >
                {step}
              </div>
            ))}
          </div>
          <div className="w-full bg-gray-600 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${(currentStep / 4) * 100}%` }}
            />
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-900/20 border border-red-700 rounded-lg p-4 mb-6">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {/* Step Content */}
        <div className="mb-6">
          {currentStep === 1 && (
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-white mb-4">Basic Information</h3>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Configuration Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={wizardData.name}
                  onChange={(e) => updateWizardData({ name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
                  placeholder="Enter a descriptive name for this configuration"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Description (Optional)</label>
                <textarea
                  value={wizardData.description}
                  onChange={(e) => updateWizardData({ description: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
                  rows={3}
                  placeholder="Describe the purpose of this email configuration"
                />
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-white mb-4">Select Email Account</h3>
              {loadingEmails ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-400"></div>
                  <span className="ml-2 text-gray-400">Loading email accounts...</span>
                </div>
              ) : (
                <div className="space-y-3">
                  {availableEmails.map((email) => (
                    <label
                      key={email.email_address}
                      className={`flex items-center p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                        wizardData.selectedEmail === email.email_address
                          ? 'border-blue-500 bg-blue-900/20'
                          : 'border-gray-600 hover:border-gray-500'
                      }`}
                    >
                      <input
                        type="radio"
                        name="email"
                        value={email.email_address}
                        checked={wizardData.selectedEmail === email.email_address}
                        onChange={(e) => updateWizardData({ selectedEmail: e.target.value })}
                        className="mr-3"
                      />
                      <div>
                        <div className="text-white font-medium">{email.email_address}</div>
                        <div className="text-gray-400 text-sm">{email.display_name}</div>
                        {email.is_default && (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 mt-1">
                            Default Account
                          </span>
                        )}
                      </div>
                    </label>
                  ))}

                  {availableEmails.length === 0 && (
                    <div className="text-center py-8">
                      <p className="text-gray-400">No email accounts found. Please ensure Outlook is configured.</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {currentStep === 3 && (
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-white mb-4">Choose Folder</h3>
              {loadingFolders ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-400"></div>
                  <span className="ml-2 text-gray-400">Loading folders for {wizardData.selectedEmail}...</span>
                </div>
              ) : (
                <div className="space-y-3">
                  {availableFolders.map((folder) => (
                    <label
                      key={folder.path}
                      className={`flex items-center justify-between p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                        wizardData.selectedFolder === folder.name
                          ? 'border-blue-500 bg-blue-900/20'
                          : 'border-gray-600 hover:border-gray-500'
                      }`}
                    >
                      <div className="flex items-center">
                        <input
                          type="radio"
                          name="folder"
                          value={folder.name}
                          checked={wizardData.selectedFolder === folder.name}
                          onChange={(e) => updateWizardData({ selectedFolder: e.target.value })}
                          className="mr-3"
                        />
                        <div>
                          <div className="text-white font-medium">{folder.path}</div>
                          <div className="text-gray-400 text-sm">{folder.count} emails</div>
                        </div>
                      </div>
                    </label>
                  ))}

                  {availableFolders.length === 0 && (
                    <div className="text-center py-8">
                      <p className="text-gray-400">No folders found for the selected email account.</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {currentStep === 4 && (
            <div className="space-y-6">
              <h3 className="text-lg font-medium text-white mb-4">Advanced Settings</h3>

              {/* Monitoring Settings */}
              <div>
                <h4 className="text-md font-medium text-gray-300 mb-3">Monitoring Configuration</h4>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Poll Interval (seconds)</label>
                    <input
                      type="number"
                      value={wizardData.poll_interval_seconds}
                      onChange={(e) => updateWizardData({ poll_interval_seconds: parseInt(e.target.value) })}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
                      min="5"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Max Backlog (hours)</label>
                    <input
                      type="number"
                      value={wizardData.max_backlog_hours}
                      onChange={(e) => updateWizardData({ max_backlog_hours: parseInt(e.target.value) })}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
                      min="1"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Retry Attempts</label>
                    <input
                      type="number"
                      value={wizardData.error_retry_attempts}
                      onChange={(e) => updateWizardData({ error_retry_attempts: parseInt(e.target.value) })}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
                      min="1"
                      max="10"
                    />
                  </div>
                </div>
              </div>

              {/* Filter Rules */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-md font-medium text-gray-300">Filter Rules (Optional)</h4>
                  <button
                    onClick={addFilterRule}
                    className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors"
                  >
                    Add Rule
                  </button>
                </div>

                {wizardData.filter_rules.map((rule, index) => (
                  <div key={index} className="bg-gray-700 rounded p-4 mb-3">
                    <div className="grid grid-cols-4 gap-3 mb-3">
                      <select
                        value={rule.field}
                        onChange={(e) => updateFilterRule(index, { field: e.target.value })}
                        className="px-3 py-2 bg-gray-600 border border-gray-500 rounded text-white focus:border-blue-500 focus:outline-none"
                      >
                        <option value="sender_email">Sender Email</option>
                        <option value="subject">Subject</option>
                        <option value="has_attachments">Has Attachments</option>
                      </select>

                      <select
                        value={rule.operation}
                        onChange={(e) => updateFilterRule(index, { operation: e.target.value })}
                        className="px-3 py-2 bg-gray-600 border border-gray-500 rounded text-white focus:border-blue-500 focus:outline-none"
                      >
                        <option value="equals">Equals</option>
                        <option value="contains">Contains</option>
                        <option value="starts_with">Starts With</option>
                        <option value="ends_with">Ends With</option>
                      </select>

                      <input
                        type="text"
                        value={rule.value}
                        onChange={(e) => updateFilterRule(index, { value: e.target.value })}
                        className="px-3 py-2 bg-gray-600 border border-gray-500 rounded text-white focus:border-blue-500 focus:outline-none"
                        placeholder="Filter value"
                      />

                      <button
                        onClick={() => removeFilterRule(index)}
                        className="px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
                      >
                        Remove
                      </button>
                    </div>

                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={rule.case_sensitive}
                        onChange={(e) => updateFilterRule(index, { case_sensitive: e.target.checked })}
                        className="mr-2"
                      />
                      <span className="text-sm text-gray-300">Case sensitive</span>
                    </label>
                  </div>
                ))}

                {wizardData.filter_rules.length === 0 && (
                  <p className="text-gray-400 text-sm">No filter rules configured. All emails will be processed.</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex justify-between">
          <button
            onClick={handlePrevious}
            disabled={currentStep === 1}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-700 disabled:opacity-50 text-white rounded transition-colors"
          >
            Previous
          </button>

          <div className="space-x-3">
            <button
              onClick={handleClose}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
            >
              Cancel
            </button>

            {currentStep < 4 ? (
              <button
                onClick={handleNext}
                disabled={!canProceedToNextStep()}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:opacity-50 text-white rounded transition-colors"
              >
                Next
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={loading || !canProceedToNextStep()}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:opacity-50 text-white rounded transition-colors"
              >
                {loading ? 'Creating...' : 'Create Configuration'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}