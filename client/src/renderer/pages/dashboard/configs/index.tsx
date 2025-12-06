import { createFileRoute } from '@tanstack/react-router';
import { useState, useEffect } from 'react';
import {
  useEmailConfigsApi,
  EmailConfigCard,
  EmailConfigWizard,
  EditConfigModal,
  type IngestionConfigListItem,
  type IngestionConfigDetail,
  type CreateEmailConfigRequest,
} from '../../../features/email-configs';

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
    isLoading,
    error,
  } = useEmailConfigsApi();

  const [configs, setConfigs] = useState<IngestionConfigListItem[]>([]);
  const [showCreateWizard, setShowCreateWizard] = useState(false);
  const [editingConfig, setEditingConfig] = useState<IngestionConfigDetail | null>(null);
  const [activatingId, setActivatingId] = useState<number | null>(null);
  const [deactivatingId, setDeactivatingId] = useState<number | null>(null);

  // Fetch configurations on mount
  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    try {
      const configList = await getEmailConfigs();
      setConfigs(configList);
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
      throw err;
    }
  };

  const handleEditConfig = async (id: number) => {
    try {
      const detail = await getEmailConfigDetail(id);
      setEditingConfig(detail);
    } catch (err) {
      console.error('Failed to load configuration details:', err);
    }
  };

  const handleUpdateConfig = async (
    id: number,
    data: {
      name?: string;
      description?: string | null;
      folder_name?: string;
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

  const handleActivate = async (id: number) => {
    setActivatingId(id);
    try {
      await activateEmailConfig(id);
      await loadConfigs();
    } catch (err) {
      console.error('Failed to activate configuration:', err);
    } finally {
      setActivatingId(null);
    }
  };

  const handleDeactivate = async (id: number) => {
    setDeactivatingId(id);
    try {
      await deactivateEmailConfig(id);
      await loadConfigs();
    } catch (err) {
      console.error('Failed to deactivate configuration:', err);
    } finally {
      setDeactivatingId(null);
    }
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
                onDelete={handleDelete}
                onActivate={handleActivate}
                onDeactivate={handleDeactivate}
                isActivating={activatingId === config.id}
                isDeactivating={deactivatingId === config.id}
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
