/**
 * Email Configuration Wizard
 * 3-step wizard for creating email ingestion configurations
 */

import { useState, useEffect } from 'react';
import type { EmailAccount, EmailFolder, FilterRule } from '../../types';
import { AccountSelectionStep, FolderSelectionStep, ConfigurationStep } from './steps';

interface EmailConfigWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: WizardData) => Promise<void>;
  onLoadAccounts: () => Promise<EmailAccount[]>;
  onLoadFolders: (emailAddress: string) => Promise<EmailFolder[]>;
}

export interface WizardData {
  name: string;
  description: string;
  email_address: string;
  folder_name: string;
  filter_rules: FilterRule[];
  poll_interval_seconds: number;
  max_backlog_hours: number;
  error_retry_attempts: number;
}

type WizardStep = 'account' | 'folder' | 'configuration';

export function EmailConfigWizard({
  isOpen,
  onClose,
  onSave,
  onLoadAccounts,
  onLoadFolders,
}: EmailConfigWizardProps) {
  const [currentStep, setCurrentStep] = useState<WizardStep>('account');
  const [isSaving, setIsSaving] = useState(false);

  // Discovery data
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [folders, setFolders] = useState<EmailFolder[]>([]);
  const [isLoadingAccounts, setIsLoadingAccounts] = useState(false);
  const [isLoadingFolders, setIsLoadingFolders] = useState(false);

  // Form data
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [selectedAccountDisplay, setSelectedAccountDisplay] = useState<string | null>(null);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [pollInterval, setPollInterval] = useState(60);
  const [maxBacklog, setMaxBacklog] = useState(24);
  const [retryAttempts, setRetryAttempts] = useState(3);
  const [filterRules, setFilterRules] = useState<FilterRule[]>([]);

  // Load accounts when modal opens
  useEffect(() => {
    if (isOpen && currentStep === 'account') {
      loadAccounts();
    }
  }, [isOpen, currentStep]);

  // Load folders when account is selected and moving to folder step
  useEffect(() => {
    if (currentStep === 'folder' && selectedAccount) {
      loadFolders(selectedAccount);
    }
  }, [currentStep, selectedAccount]);

  const loadAccounts = async () => {
    setIsLoadingAccounts(true);
    try {
      const data = await onLoadAccounts();
      setAccounts(data);
    } catch (err) {
      console.error('Failed to load accounts:', err);
    } finally {
      setIsLoadingAccounts(false);
    }
  };

  const loadFolders = async (emailAddress: string) => {
    setIsLoadingFolders(true);
    try {
      const data = await onLoadFolders(emailAddress);
      setFolders(data);
    } catch (err) {
      console.error('Failed to load folders:', err);
    } finally {
      setIsLoadingFolders(false);
    }
  };

  const handleSelectAccount = (account: EmailAccount) => {
    setSelectedAccount(account.email_address);
    setSelectedAccountDisplay(account.display_name || account.email_address);
    setName(`${account.display_name || account.email_address} - Email Monitor`);
  };

  const handleSelectFolder = (folder: EmailFolder) => {
    setSelectedFolder(folder.folder_name);
  };

  const handleAddFilterRule = () => {
    setFilterRules([
      ...filterRules,
      {
        field: 'sender_email',
        operation: 'contains',
        value: '',
        case_sensitive: false,
      },
    ]);
  };

  const handleUpdateFilterRule = (index: number, field: keyof FilterRule, value: any) => {
    setFilterRules(
      filterRules.map((rule, i) => (i === index ? { ...rule, [field]: value } : rule))
    );
  };

  const handleRemoveFilterRule = (index: number) => {
    setFilterRules(filterRules.filter((_, i) => i !== index));
  };

  const handleNext = () => {
    if (currentStep === 'account' && selectedAccount) {
      setCurrentStep('folder');
    } else if (currentStep === 'folder' && selectedFolder) {
      setCurrentStep('configuration');
    }
  };

  const handleBack = () => {
    if (currentStep === 'folder') {
      setCurrentStep('account');
    } else if (currentStep === 'configuration') {
      setCurrentStep('folder');
    }
  };

  const handleSave = async () => {
    if (!selectedAccount || !selectedFolder) return;

    setIsSaving(true);
    try {
      await onSave({
        name,
        description,
        email_address: selectedAccount,
        folder_name: selectedFolder,
        filter_rules: filterRules,
        poll_interval_seconds: pollInterval,
        max_backlog_hours: maxBacklog,
        error_retry_attempts: retryAttempts,
      });

      // Reset wizard
      handleClose();
    } catch (err) {
      console.error('Failed to save configuration:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleClose = () => {
    setCurrentStep('account');
    setSelectedAccount(null);
    setSelectedAccountDisplay(null);
    setSelectedFolder(null);
    setName('');
    setDescription('');
    setPollInterval(60);
    setMaxBacklog(24);
    setRetryAttempts(3);
    setFilterRules([]);
    onClose();
  };

  if (!isOpen) return null;

  const stepConfig = {
    account: {
      title: 'Select Email Account',
      canProceed: !!selectedAccount,
    },
    folder: {
      title: 'Choose Folder',
      canProceed: !!selectedFolder,
    },
    configuration: {
      title: 'Configure Settings',
      canProceed: name.trim().length > 0,
    },
  };

  const currentConfig = stepConfig[currentStep];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-gray-900 rounded-lg w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl border border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div>
            <h2 className="text-xl font-bold text-white mb-1">Create Email Configuration</h2>
            <p className="text-sm text-gray-400">{currentConfig.title}</p>
          </div>
          <button
            onClick={handleClose}
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
          <div className="flex items-center justify-center space-x-4">
            {/* Step 1 */}
            <div className="flex items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  currentStep === 'account'
                    ? 'bg-blue-600 text-white'
                    : selectedAccount
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-700 text-gray-400'
                }`}
              >
                {selectedAccount && currentStep !== 'account' ? '✓' : '1'}
              </div>
              <span
                className={`ml-2 text-sm font-medium ${
                  currentStep === 'account' ? 'text-white' : 'text-gray-400'
                }`}
              >
                Email Account
              </span>
            </div>

            <div className="w-12 h-0.5 bg-gray-700"></div>

            {/* Step 2 */}
            <div className="flex items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  currentStep === 'folder'
                    ? 'bg-blue-600 text-white'
                    : selectedFolder
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-700 text-gray-400'
                }`}
              >
                {selectedFolder && currentStep !== 'folder' ? '✓' : '2'}
              </div>
              <span
                className={`ml-2 text-sm font-medium ${
                  currentStep === 'folder' ? 'text-white' : 'text-gray-400'
                }`}
              >
                Folder
              </span>
            </div>

            <div className="w-12 h-0.5 bg-gray-700"></div>

            {/* Step 3 */}
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
                Configuration
              </span>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {currentStep === 'account' && (
            <AccountSelectionStep
              accounts={accounts}
              selectedAccount={selectedAccount}
              isLoading={isLoadingAccounts}
              onSelectAccount={handleSelectAccount}
              onRetry={loadAccounts}
            />
          )}

          {currentStep === 'folder' && (
            <FolderSelectionStep
              folders={folders}
              selectedFolder={selectedFolder}
              emailAccount={selectedAccountDisplay || ''}
              isLoading={isLoadingFolders}
              onSelectFolder={handleSelectFolder}
              onRetry={() => selectedAccount && loadFolders(selectedAccount)}
            />
          )}

          {currentStep === 'configuration' && (
            <ConfigurationStep
              name={name}
              description={description}
              pollInterval={pollInterval}
              maxBacklog={maxBacklog}
              retryAttempts={retryAttempts}
              filterRules={filterRules}
              emailAccount={selectedAccountDisplay || ''}
              folderName={selectedFolder || ''}
              onNameChange={setName}
              onDescriptionChange={setDescription}
              onPollIntervalChange={setPollInterval}
              onMaxBacklogChange={setMaxBacklog}
              onRetryAttemptsChange={setRetryAttempts}
              onAddFilterRule={handleAddFilterRule}
              onUpdateFilterRule={handleUpdateFilterRule}
              onRemoveFilterRule={handleRemoveFilterRule}
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-gray-700 bg-gray-800/30">
          <div>
            {currentStep !== 'account' && (
              <button
                onClick={handleBack}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
              >
                Back
              </button>
            )}
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleClose}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
            >
              Cancel
            </button>

            {currentStep !== 'configuration' ? (
              <button
                onClick={handleNext}
                disabled={!currentConfig.canProceed}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded transition-colors"
              >
                Next
              </button>
            ) : (
              <button
                onClick={handleSave}
                disabled={!currentConfig.canProceed || isSaving}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded transition-colors"
              >
                {isSaving ? 'Creating...' : 'Create Configuration'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
