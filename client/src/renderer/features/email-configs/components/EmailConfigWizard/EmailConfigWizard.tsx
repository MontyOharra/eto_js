/**
 * Email Configuration Wizard
 * 4-step wizard for creating email ingestion configurations with multi-provider support
 */

import { useState } from 'react';
import type { EmailFolder, FilterRule, CreateEmailConfigRequest } from '../../types';
import { ProviderSelectionStep, CredentialsStep, FolderSelectionStep, ConfigurationStep } from './steps';
import { EmailConfigWizardHeader } from './EmailConfigWizardHeader';
import { EmailConfigWizardFooter } from './EmailConfigWizardFooter';

interface EmailConfigWizardProps {
  onClose: () => void;
  onSave: (data: CreateEmailConfigRequest) => Promise<void>;
  onLoadFolders: (providerType: string, providerSettings: Record<string, any>) => Promise<EmailFolder[]>;
  onTestConnection: (providerType: string, providerSettings: Record<string, any>, folderName: string) => Promise<{ success: boolean; message: string }>;
}

type WizardStep = 'provider' | 'credentials' | 'folder' | 'configuration';

interface ImapCredentials {
  host: string;
  port: number;
  email_address: string;
  password: string;
  use_ssl: boolean;
}

export function EmailConfigWizard({
  onClose,
  onSave,
  onLoadFolders,
  onTestConnection,
}: EmailConfigWizardProps) {
  const [currentStep, setCurrentStep] = useState<WizardStep>('provider');
  const [isSaving, setIsSaving] = useState(false);

  // Provider selection
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);

  // Provider credentials
  const [credentials, setCredentials] = useState<ImapCredentials | null>(null);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [connectionTestResult, setConnectionTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // Folder discovery
  const [folders, setFolders] = useState<EmailFolder[]>([]);
  const [isLoadingFolders, setIsLoadingFolders] = useState(false);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);

  // Form data
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [pollInterval, setPollInterval] = useState(60);
  const [filterRules, setFilterRules] = useState<FilterRule[]>([]);

  const handleSelectProvider = (provider: string) => {
    setSelectedProvider(provider);
  };

  const handleCredentialsChange = (newCredentials: ImapCredentials) => {
    setCredentials(newCredentials);
    // Reset connection test result when credentials change
    setConnectionTestResult(null);
  };

  const handleTestConnection = async () => {
    if (!credentials || !selectedProvider) return;

    setIsTestingConnection(true);
    setConnectionTestResult(null);

    try {
      const result = await onTestConnection(selectedProvider, credentials, 'INBOX');
      setConnectionTestResult(result);
    } catch (err) {
      console.error('Connection test failed:', err);
      setConnectionTestResult({
        success: false,
        message: 'Connection test failed: ' + (err as Error).message,
      });
    } finally {
      setIsTestingConnection(false);
    }
  };

  const loadFolders = async () => {
    if (!credentials || !selectedProvider) return;

    setIsLoadingFolders(true);
    try {
      const data = await onLoadFolders(selectedProvider, credentials);
      setFolders(data);
    } catch (err) {
      console.error('Failed to load folders:', err);
    } finally {
      setIsLoadingFolders(false);
    }
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
    if (currentStep === 'provider' && selectedProvider) {
      setCurrentStep('credentials');
    } else if (currentStep === 'credentials' && credentials && connectionTestResult?.success) {
      setCurrentStep('folder');
    } else if (currentStep === 'folder' && selectedFolder) {
      setCurrentStep('configuration');
    }
  };

  const handleBack = () => {
    if (currentStep === 'credentials') {
      setCurrentStep('provider');
    } else if (currentStep === 'folder') {
      setCurrentStep('credentials');
    } else if (currentStep === 'configuration') {
      setCurrentStep('folder');
    }
  };

  const handleSave = async () => {
    if (!selectedProvider || !credentials || !selectedFolder) return;

    setIsSaving(true);
    try {
      await onSave({
        provider_type: selectedProvider,
        provider_settings: credentials,
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
    provider: {
      title: 'Choose Provider',
      canProceed: !!selectedProvider,
    },
    credentials: {
      title: 'Enter Credentials',
      canProceed: !!credentials && !!connectionTestResult?.success,
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
          isProviderComplete={!!selectedProvider}
          isCredentialsComplete={!!credentials && !!connectionTestResult?.success}
          isFolderComplete={!!selectedFolder}
          onClose={onClose}
        />

        {/* Main Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {currentStep === 'provider' && (
            <ProviderSelectionStep
              selectedProvider={selectedProvider}
              onSelectProvider={handleSelectProvider}
            />
          )}

          {currentStep === 'credentials' && selectedProvider && (
            <CredentialsStep
              providerType={selectedProvider}
              credentials={credentials}
              onCredentialsChange={handleCredentialsChange}
              onTestConnection={handleTestConnection}
              isTestingConnection={isTestingConnection}
              connectionTestResult={connectionTestResult}
            />
          )}

          {currentStep === 'folder' && (
            <FolderSelectionStep
              folders={folders}
              selectedFolder={selectedFolder}
              emailAccount={credentials?.email_address || ''}
              isLoading={isLoadingFolders}
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
              emailAccount={credentials?.email_address || ''}
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
          showLoadFolders={currentStep === 'folder' && folders.length === 0 && !isLoadingFolders}
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
