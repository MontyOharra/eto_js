import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { apiClient, EmailIngestionConfigSummary, EmailIngestionStatus } from "../../services/api";
import { ConfirmationModal } from "../../components/shared/ConfirmationModal";

export const Route = createFileRoute("/dashboard/settings")({
  component: SettingsPage,
});

interface FilterRule {
  field: string;
  operation: string;
  value: string;
  case_sensitive: boolean;
}

interface NewConfigForm {
  name: string;
  description: string;
  email_address: string;
  folder_name: string;
  poll_interval_seconds: number;
  max_backlog_hours: number;
  error_retry_attempts: number;
  filter_rules: FilterRule[];
}

function SettingsPage() {
  const [configs, setConfigs] = useState<EmailIngestionConfigSummary[]>([]);
  const [status, setStatus] = useState<EmailIngestionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [availableFolders, setAvailableFolders] = useState<any[]>([]);
  const [loadingFolders, setLoadingFolders] = useState(false);

  // Form state
  const [newConfig, setNewConfig] = useState<NewConfigForm>({
    name: "",
    description: "",
    email_address: "",
    folder_name: "",
    poll_interval_seconds: 60,
    max_backlog_hours: 24,
    error_retry_attempts: 3,
    filter_rules: []
  });

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

  const fetchFolders = async (emailAddress: string) => {
    if (!emailAddress) return;
    
    try {
      setLoadingFolders(true);
      const response = await apiClient.testOutlookFolders(emailAddress);
      if (response.success) {
        setAvailableFolders(response.data.folders);
      }
    } catch (err) {
      console.error('Failed to fetch folders:', err);
    } finally {
      setLoadingFolders(false);
    }
  };

  useEffect(() => {
    fetchConfigs();
    fetchStatus();
  }, []);

  const handleCreateConfig = async () => {
    try {
      const response = await apiClient.createEmailIngestionConfig({
        name: newConfig.name,
        description: newConfig.description || undefined,
        connection: {
          email_address: newConfig.email_address,
          folder_name: newConfig.folder_name
        },
        filter_rules: newConfig.filter_rules.length > 0 ? newConfig.filter_rules : undefined,
        monitoring: {
          poll_interval_seconds: newConfig.poll_interval_seconds,
          max_backlog_hours: newConfig.max_backlog_hours,
          error_retry_attempts: newConfig.error_retry_attempts
        },
        created_by: "user"
      });

      if (response.success) {
        setShowCreateForm(false);
        setNewConfig({
          name: "",
          description: "",
          email_address: "",
          folder_name: "",
          poll_interval_seconds: 60,
          max_backlog_hours: 24,
          error_retry_attempts: 3,
          filter_rules: []
        });
        fetchConfigs();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create configuration');
    }
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

  const addFilterRule = () => {
    setNewConfig(prev => ({
      ...prev,
      filter_rules: [...prev.filter_rules, {
        field: "sender_email",
        operation: "equals",
        value: "",
        case_sensitive: false
      }]
    }));
  };

  const updateFilterRule = (index: number, updates: Partial<FilterRule>) => {
    setNewConfig(prev => ({
      ...prev,
      filter_rules: prev.filter_rules.map((rule, i) => 
        i === index ? { ...rule, ...updates } : rule
      )
    }));
  };

  const removeFilterRule = (index: number) => {
    setNewConfig(prev => ({
      ...prev,
      filter_rules: prev.filter_rules.filter((_, i) => i !== index)
    }));
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
              onClick={() => setShowCreateForm(true)}
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

        {/* Create Configuration Form */}
        {showCreateForm && (
          <div className="bg-gray-800 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-white">Create New Configuration</h2>
              <button
                onClick={() => setShowCreateForm(false)}
                className="text-gray-400 hover:text-gray-200"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Name</label>
                  <input
                    type="text"
                    value={newConfig.name}
                    onChange={(e) => setNewConfig(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
                    placeholder="Configuration name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Description</label>
                  <input
                    type="text"
                    value={newConfig.description}
                    onChange={(e) => setNewConfig(prev => ({ ...prev, description: e.target.value }))}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
                    placeholder="Optional description"
                  />
                </div>
              </div>

              {/* Connection Settings */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Email Address</label>
                  <input
                    type="email"
                    value={newConfig.email_address}
                    onChange={(e) => {
                      setNewConfig(prev => ({ ...prev, email_address: e.target.value }));
                      if (e.target.value) {
                        fetchFolders(e.target.value);
                      }
                    }}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
                    placeholder="your.email@domain.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Folder Name</label>
                  {loadingFolders ? (
                    <div className="flex items-center justify-center py-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-400"></div>
                    </div>
                  ) : (
                    <select
                      value={newConfig.folder_name}
                      onChange={(e) => setNewConfig(prev => ({ ...prev, folder_name: e.target.value }))}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
                    >
                      <option value="">Select folder...</option>
                      {availableFolders.flatMap(account => 
                        account.folders.map((folder: any) => (
                          <option key={`${account.account}-${folder.path}`} value={folder.name}>
                            {folder.path} ({folder.count} emails)
                          </option>
                        ))
                      )}
                    </select>
                  )}
                </div>
              </div>

              {/* Monitoring Settings */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Poll Interval (seconds)</label>
                  <input
                    type="number"
                    value={newConfig.poll_interval_seconds}
                    onChange={(e) => setNewConfig(prev => ({ ...prev, poll_interval_seconds: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
                    min="5"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Max Backlog (hours)</label>
                  <input
                    type="number"
                    value={newConfig.max_backlog_hours}
                    onChange={(e) => setNewConfig(prev => ({ ...prev, max_backlog_hours: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
                    min="1"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Retry Attempts</label>
                  <input
                    type="number"
                    value={newConfig.error_retry_attempts}
                    onChange={(e) => setNewConfig(prev => ({ ...prev, error_retry_attempts: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
                    min="1"
                    max="10"
                  />
                </div>
              </div>

              {/* Filter Rules */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-300">Filter Rules (Optional)</label>
                  <button
                    onClick={addFilterRule}
                    className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors"
                  >
                    Add Rule
                  </button>
                </div>
                
                {newConfig.filter_rules.map((rule, index) => (
                  <div key={index} className="bg-gray-700 rounded p-4 mb-2">
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
              </div>

              {/* Form Actions */}
              <div className="flex justify-end space-x-3 pt-4">
                <button
                  onClick={() => setShowCreateForm(false)}
                  className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateConfig}
                  disabled={!newConfig.name || !newConfig.email_address || !newConfig.folder_name}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded transition-colors"
                >
                  Create Configuration
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

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
