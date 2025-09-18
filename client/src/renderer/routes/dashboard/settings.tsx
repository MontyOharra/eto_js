import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { apiClient, EmailIngestionConfigSummary, EmailIngestionStatus } from "../../services/api";
import { ConfirmationModal } from "../../components/shared/ConfirmationModal";
import { EmailConfigWizard } from "../../components/email/EmailConfigWizard";

export const Route = createFileRoute("/dashboard/settings")({
  component: SettingsPage,
});


function SettingsPage() {
  const [configs, setConfigs] = useState<EmailIngestionConfigSummary[]>([]);
  const [status, setStatus] = useState<EmailIngestionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showWizard, setShowWizard] = useState(false);

  // Confirmation modal state
  const [confirmationModal, setConfirmationModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
  } | null>(null);

  const fetchConfigs = async () => {
    try {
      setLoading(true);
      const response = await apiClient.getEmailIngestionConfigs();
      if (response.success) {
        setConfigs(response.data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch configurations');
    } finally {
      setLoading(false);
    }
  };

  const fetchStatus = async () => {
    try {
      const response = await apiClient.getEmailIngestionStatus();
      if (response.success) {
        setStatus(response.data);
      }
    } catch (err) {
      console.error('Failed to fetch status:', err);
    }
  };


  useEffect(() => {
    fetchConfigs();
    fetchStatus();
  }, []);

  const handleWizardSuccess = () => {
    fetchConfigs();
    fetchStatus();
  };

  const handleActivateConfig = async (configId: number) => {
    try {
      const response = await apiClient.activateEmailIngestionConfig(configId, true);
      if (response.success) {
        fetchConfigs();
        fetchStatus();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate configuration');
    }
  };

  const handleDeleteConfig = (configId: number) => {
    setConfirmationModal({
      isOpen: true,
      title: "Delete Configuration",
      message: "Are you sure you want to delete this configuration? This action cannot be undone.",
      onConfirm: () => confirmDeleteConfig(configId)
    });
  };

  const confirmDeleteConfig = async (configId: number) => {
    try {
      const response = await apiClient.deleteEmailIngestionConfig(configId);
      if (response.success) {
        fetchConfigs();
        setConfirmationModal(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete configuration');
      setConfirmationModal(null);
    }
  };

  const handleStartStop = async () => {
    try {
      if (status?.is_running) {
        await apiClient.stopEmailIngestionService();
      } else {
        await apiClient.startEmailIngestionService();
      }
      fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start/stop service');
    }
  };


  if (loading) {
    return (
      <div className="flex-1 p-6">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading settings...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="flex-1 p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-blue-300 mb-2">Email Ingestion Settings</h1>
          <p className="text-gray-400">Configure email monitoring and processing settings</p>
        </div>

        {error && (
          <div className="bg-red-900/20 border border-red-700 rounded-lg p-4 mb-6">
            <p className="text-red-400">{error}</p>
            <button 
              onClick={() => setError(null)}
              className="mt-2 text-sm text-red-300 hover:text-red-200"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Service Status */}
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-white">Service Status</h2>
            <button
              onClick={handleStartStop}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                status?.is_running 
                  ? 'bg-red-600 hover:bg-red-700 text-white' 
                  : 'bg-green-600 hover:bg-green-700 text-white'
              }`}
            >
              {status?.is_running ? 'Stop Service' : 'Start Service'}
            </button>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-gray-400 text-sm">Status:</span>
              <div className="flex items-center mt-1">
                <div className={`w-2 h-2 rounded-full mr-2 ${
                  status?.is_running ? 'bg-green-400' : 'bg-red-400'
                }`}></div>
                <span className="text-white">
                  {status?.is_running ? 'Running' : 'Stopped'}
                </span>
              </div>
            </div>
            <div>
              <span className="text-gray-400 text-sm">Current Config:</span>
              <p className="text-white">{status?.current_config?.name || 'None'}</p>
            </div>
            <div>
              <span className="text-gray-400 text-sm">Emails Processed:</span>
              <p className="text-white">{status?.stats?.emails_processed || 0}</p>
            </div>
            <div>
              <span className="text-gray-400 text-sm">Connection:</span>
              <p className={status?.connection_status?.is_connected ? 'text-green-400' : 'text-red-400'}>
                {status?.connection_status?.is_connected ? 'Connected' : 'Disconnected'}
              </p>
            </div>
          </div>
        </div>

        {/* Configurations List */}
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-white">Configurations</h2>
            <button
              onClick={() => setShowWizard(true)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium transition-colors"
            >
              Add Configuration
            </button>
          </div>

          {configs.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-400">No configurations found. Create one to get started.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {configs.map((config) => (
                <div key={config.id} className="bg-gray-700 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <h3 className="text-white font-medium">{config.name}</h3>
                        {config.is_active && (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            Active
                          </span>
                        )}
                        {config.is_running && (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            Running
                          </span>
                        )}
                      </div>
                      <p className="text-gray-400 text-sm mt-1">{config.folder_name}</p>
                      <p className="text-gray-500 text-xs mt-1">
                        {config.emails_processed} emails processed
                      </p>
                    </div>
                    <div className="flex items-center space-x-2">
                      {!config.is_active && (
                        <button
                          onClick={() => handleActivateConfig(config.id)}
                          className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded transition-colors"
                        >
                          Activate
                        </button>
                      )}
                      <button
                        onClick={() => handleDeleteConfig(config.id)}
                        className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>

      {/* Email Configuration Wizard */}
      <EmailConfigWizard
        isOpen={showWizard}
        onClose={() => setShowWizard(false)}
        onSuccess={handleWizardSuccess}
      />

      {/* Confirmation Modal */}
      {confirmationModal && (
        <ConfirmationModal
          isOpen={confirmationModal.isOpen}
          title={confirmationModal.title}
          message={confirmationModal.message}
          variant="danger"
          confirmText="Delete"
          onConfirm={confirmationModal.onConfirm}
          onCancel={() => setConfirmationModal(null)}
        />
      )}
    </>
  );
}
