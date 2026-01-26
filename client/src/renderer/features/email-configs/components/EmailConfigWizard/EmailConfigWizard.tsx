/**
 * Email Configuration Wizard
 * 3-step wizard for creating email ingestion configurations
 * Step 1: Select email account
 * Step 2: Select folder
 * Step 3: Configure settings
 */

import { useState, useEffect } from 'react';
import type { FilterRule } from '../../types';
import type { CreateEmailConfigRequest } from '../../api/types';
import { AccountSelectionStep, FolderSelectionStep, ConfigurationStep } from './steps';
import { EmailConfigWizardHeader } from './EmailConfigWizardHeader';
import { EmailConfigWizardFooter } from './EmailConfigWizardFooter';
import { useEmailAccountsApi, type EmailAccountSummary } from '../../../email-accounts';

interface EmailConfigWizardProps {
  onClose: () => void;
  onSave: (data: CreateEmailConfigRequest) => Promise<void>;
}

type WizardStep = 'account' | 'folder' | 'configuration';

export function EmailConfigWizard({
  onClose,
  onSave,
}: EmailConfigWizardProps) {
  const { getEmailAccounts, getAccountFolders } = useEmailAccountsApi();

  const [currentStep, setCurrentStep] = useState<WizardStep>('account');
  const [isSaving, setIsSaving] = useState(false);

  // Account selection
  const [accounts, setAccounts] = useState<EmailAccountSummary[]>([]);
  const [isLoadingAccounts, setIsLoadingAccounts] = useState(true);
  const [accountsError, setAccountsError] = useState<string | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<EmailAccountSummary | null>(null);

  // Folder discovery
  const [folders, setFolders] = useState<string[]>([]);
  const [isLoadingFolders, setIsLoadingFolders] = useState(false);
  const [foldersError, setFoldersError] = useState<string | null>(null);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);

  // Form data
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [pollInterval, setPollInterval] = useState(60);
  const [filterRules, setFilterRules] = useState<FilterRule[]>([]);

  // Load accounts on mount
  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    setIsLoadingAccounts(true);
    setAccountsError(null);
    try {
      const accountsList = await getEmailAccounts({ validated_only: true });
      setAccounts(accountsList);
    } catch (err) {
      setAccountsError(err instanceof Error ? err.message : 'Failed to load accounts');
    } finally {
      setIsLoadingAccounts(false);
    }
  };

  const loadFolders = async () => {
    if (!selectedAccount) return;

    setIsLoadingFolders(true);
    setFoldersError(null);
    try {
      const foldersList = await getAccountFolders(selectedAccount.id);
      setFolders(foldersList);
    } catch (err) {
      setFoldersError(err instanceof Error ? err.message : 'Failed to load folders');
    } finally {
      setIsLoadingFolders(false);
    }
  };

  // Auto-load folders when entering the folder selection step
  useEffect(() => {
    if (currentStep === 'folder' && folders.length === 0 && !isLoadingFolders && selectedAccount) {
      loadFolders();
    }
  }, [currentStep, selectedAccount]);

  const handleSelectAccount = (account: EmailAccountSummary) => {
    setSelectedAccount(account);
    // Reset folder selection when account changes
    setSelectedFolder(null);
    setFolders([]);
  };

  const handleSelectFolder = (folder: string) => {
    setSelectedFolder(folder);
  };

  const handleAddFilterRule = () => {
    setFilterRules([
      ...filterRules,
      {
        field: 'sender_email',
        operation: 'contains',
        value: '',
        case_sensitive: false,
        negate: false,
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
        account_id: selectedAccount.id,
        name,
        description,
        folder_name: selectedFolder,
        filter_rules: filterRules,
        poll_interval_seconds: pollInterval,
      });

      // Close modal - state will be automatically reset on unmount
      onClose();
    } catch (err) {
      console.error('Failed to save configuration:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const stepConfig = {
    account: {
      title: 'Select Account',
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
        <EmailConfigWizardHeader
          currentStep={currentStep}
          stepTitle={currentConfig.title}
          isAccountComplete={!!selectedAccount}
          isFolderComplete={!!selectedFolder}
          onClose={onClose}
        />

        {/* Main Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {currentStep === 'account' && (
            <AccountSelectionStep
              accounts={accounts}
              selectedAccountId={selectedAccount?.id ?? null}
              isLoading={isLoadingAccounts}
              error={accountsError}
              onSelectAccount={handleSelectAccount}
              onRetry={loadAccounts}
            />
          )}

          {currentStep === 'folder' && (
            <FolderSelectionStep
              folders={folders}
              selectedFolder={selectedFolder}
              emailAccount={selectedAccount?.email_address || ''}
              isLoading={isLoadingFolders}
              error={foldersError}
              onSelectFolder={handleSelectFolder}
              onRetry={loadFolders}
            />
          )}

          {currentStep === 'configuration' && (
            <ConfigurationStep
              name={name}
              description={description}
              pollInterval={pollInterval}
              filterRules={filterRules}
              emailAccount={selectedAccount?.email_address || ''}
              folderName={selectedFolder || ''}
              onNameChange={setName}
              onDescriptionChange={setDescription}
              onPollIntervalChange={setPollInterval}
              onAddFilterRule={handleAddFilterRule}
              onUpdateFilterRule={handleUpdateFilterRule}
              onRemoveFilterRule={handleRemoveFilterRule}
            />
          )}
        </div>

        {/* Footer */}
        <EmailConfigWizardFooter
          currentStep={currentStep}
          canProceed={currentConfig.canProceed}
          isSaving={isSaving}
          showLoadFolders={currentStep === 'folder' && folders.length === 0 && !isLoadingFolders && !foldersError}
          onClose={onClose}
          onBack={handleBack}
          onNext={handleNext}
          onSave={handleSave}
          onLoadFolders={loadFolders}
        />
      </div>
    </div>
  );
}
