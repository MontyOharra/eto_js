import { createFileRoute } from '@tanstack/react-router';
import { useState, useEffect } from 'react';
import { useEmailConfigsApi } from '../../../features/email-configs/hooks';
import {
  EmailConfigCard,
  EmailConfigWizard,
  EditConfigModal,
} from '../../../features/email-configs/components';
import type { EmailConfigDetail, CreateEmailConfigRequest } from '../../../features/email-configs/types';

export const Route = createFileRoute('/dashboard/configs/')({
  component: ConfigurationsPage,
});

function ConfigurationsPage() {
  const {
    getEmailConfigs,
    getEmailConfigDetail,
    createEmailConfig,
    updateEmailConfig,
    deleteEmailConfig,
    activateEmailConfig,
    deactivateEmailConfig,
    discoverFolders,
    testConnection,
    isLoading,
    error,
  } = useEmailConfigsApi();

  const [configs, setConfigs] = useState<EmailConfigDetail[]>([]);
  const [showCreateWizard, setShowCreateWizard] = useState(false);
  const [editingConfig, setEditingConfig] = useState<EmailConfigDetail | null>(null);

  // Fetch configurations on mount
  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    try {
      const summaries = await getEmailConfigs();
      // Fetch full details for each config
      const details = await Promise.all(
        summaries.map((summary) => getEmailConfigDetail(summary.id))
      );
      setConfigs(details);
    } catch (err) {
      console.error('Failed to load configurations:', err);
    }
  };

  const handleCreateConfig = async (data: CreateEmailConfigRequest) => {
    try {
      await createEmailConfig(data);
      await loadConfigs();
    } catch (err) {
      console.error('Failed to create configuration:', err);
      throw err; // Re-throw to let wizard handle error
    }
  };

  const handleEditConfig = (id: number) => {
    const config = configs.find((c) => c.id === id);
    if (config) {
      setEditingConfig(config);
    }
  };

  const handleUpdateConfig = async (
    id: number,
    data: {
      description?: string | null;
      filter_rules?: any[];
      poll_interval_seconds?: number;
    }
  ) => {
    try {
      await updateEmailConfig(id, data);
      await loadConfigs();
    } catch (err) {
      console.error('Failed to update configuration:', err);
      throw err;
    }
  };

  const handleActivate = async (id: number) => {
    try {
      await activateEmailConfig(id);
      await loadConfigs();
    } catch (err) {
      console.error('Failed to activate configuration:', err);
    }
  };

  const handleDeactivate = async (id: number) => {
    try {
      await deactivateEmailConfig(id);
      await loadConfigs();
    } catch (err) {
      console.error('Failed to deactivate configuration:', err);
    }
  };

  const handleDelete = async (id: number) => {
    if (
      !window.confirm(
        'Are you sure you want to delete this configuration? This action cannot be undone.'
      )
    ) {
      return;
    }

    try {
      await deleteEmailConfig(id);
      await loadConfigs();
    } catch (err) {
      console.error('Failed to delete configuration:', err);
    }
  };

  const handleLoadFolders = async (providerType: string, providerSettings: Record<string, any>) => {
    return discoverFolders({ provider_type: providerType, provider_settings: providerSettings });
  };

  const handleTestConnection = async (
    providerType: string,
    providerSettings: Record<string, any>,
    folderName: string
  ) => {
    return testConnection({
      provider_type: providerType,
      provider_settings: providerSettings,
      folder_name: folderName,
    });
  };

  return (
    <>
      <div className="p-6">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">Email Configurations</h1>
            <p className="text-gray-400 mt-2">
              Configure email monitoring for automated PDF processing
            </p>
          </div>
          <button
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
            onClick={() => setShowCreateWizard(true)}
          >
            + Create Configuration
          </button>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="mb-6 bg-blue-900/30 border border-blue-700 rounded-lg p-4">
            <p className="text-blue-200">Loading configurations...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="mb-6 bg-red-900/30 border border-red-700 rounded-lg p-4">
            <p className="text-red-200">{error}</p>
          </div>
        )}

        {/* Configurations Display */}
        <div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {configs.map((config) => (
              <EmailConfigCard
                key={config.id}
                config={config}
                onEdit={handleEditConfig}
                onActivate={config.is_active ? undefined : handleActivate}
                onDeactivate={config.is_active ? handleDeactivate : undefined}
                onDelete={!config.is_active ? handleDelete : undefined}
              />
            ))}
          </div>

          {/* Empty State */}
          {configs.length === 0 && !isLoading && (
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-12 text-center">
              <div className="text-gray-400 mb-4">
                <svg
                  className="mx-auto h-12 w-12 text-gray-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-white mb-2">No configurations yet</h3>
              <p className="text-gray-400 mb-4">
                Get started by creating your first email configuration
              </p>
              <button
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
                onClick={() => setShowCreateWizard(true)}
              >
                Create Configuration
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Create Configuration Wizard */}
      {showCreateWizard && (
        <EmailConfigWizard
          onClose={() => setShowCreateWizard(false)}
          onSave={handleCreateConfig}
          onLoadFolders={handleLoadFolders}
          onTestConnection={handleTestConnection}
        />
      )}

      {/* Edit Configuration Modal */}
      <EditConfigModal
        isOpen={!!editingConfig}
        config={editingConfig}
        onClose={() => setEditingConfig(null)}
        onSave={handleUpdateConfig}
      />
    </>
  );
}

