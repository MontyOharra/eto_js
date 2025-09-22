import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
// Icons are inline SVG components
import { Link } from "@tanstack/react-router";
// Use existing API client for now
import { apiClient } from "../../../services/api";
import type { EmailIngestionConfig } from "../../../services/api";
import { EmailConfigWizard } from "../../../components/email/EmailConfigWizard";

export const Route = createFileRoute("/dashboard/settings/email-configs")({
  component: EmailConfigsPage,
});

function EmailConfigsPage() {
  const [configs, setConfigs] = useState<EmailIngestionConfig[]>([]);
  const [serviceStatus, setServiceStatus] = useState<any>(null); // Use any for now
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const fetchServiceStatus = async () => {
    try {
      // For now, just set as up since we're using the old API client
      setServiceStatus({ service: "email_configs", status: "up", message: "Service operational" });
    } catch (err) {
      console.error('Failed to fetch service status:', err);
      setServiceStatus({ service: "email_configs", status: "down", message: "Service unavailable" });
    }
  };

  const fetchConfigs = async () => {
    try {
      setLoading(true);
      const response = await apiClient.getEmailIngestionConfigs();
      if (response.success) {
        setConfigs(response.data);
      }
      setError(null);
    } catch (err) {
      console.error('Error fetching configs:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch configurations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchServiceStatus();
    fetchConfigs();
  }, []);

  const handleToggleActivation = async (config: EmailIngestionConfig) => {
    try {
      if (config.is_active) {
        await apiClient.deactivateEmailIngestionConfig(config.id);
      } else {
        await apiClient.activateEmailIngestionConfig(config.id, true);
      }
      fetchConfigs(); // Refresh the configs list
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle configuration');
    }
  };

  const handleCreateSuccess = () => {
    setShowCreateModal(false);
    fetchConfigs(); // Refresh the configs list
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="flex-1 p-6">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading email configurations...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="flex-1 p-6">
        {/* Header with back button */}
        <div className="mb-6">
          <div className="flex items-center space-x-4 mb-4">
            <Link
              to="/dashboard/settings"
              className="inline-flex items-center text-gray-400 hover:text-blue-300 transition-colors"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Settings
            </Link>
          </div>
          <h1 className="text-2xl font-semibold text-blue-300 mb-2">Email Ingestion Configuration</h1>
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
          <h2 className="text-lg font-medium text-white mb-4">Service Status</h2>
          <div className="flex items-center space-x-4">
            <div className="flex items-center">
              <div className={`w-3 h-3 rounded-full mr-2 ${
                serviceStatus?.status === 'up' ? 'bg-green-400' : 'bg-red-400'
              }`}></div>
              <span className="text-white font-medium">
                {serviceStatus?.status === 'up' ? 'Service Running' : 'Service Down'}
              </span>
            </div>
            {serviceStatus?.message && (
              <span className="text-gray-400 text-sm">
                {serviceStatus.message}
              </span>
            )}
          </div>
        </div>

        {/* Configurations List */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-medium text-white">Email Configurations</h2>
            <button
              className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
              onClick={() => setShowCreateModal(true)}
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Create Configuration
            </button>
          </div>

          {configs.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-400 mb-4">No email configurations found.</p>
              <p className="text-gray-500 text-sm">Create your first configuration to start monitoring emails.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {configs.map((config) => (
                <div key={config.id} className="bg-gray-700 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="text-white font-medium">{config.name}</h3>
                        {config.is_active && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-900/30 border border-green-700 text-green-300">
                            Active
                          </span>
                        )}
                        {config.is_running && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-900/30 border border-blue-700 text-blue-300">
                            Running
                          </span>
                        )}
                      </div>

                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-400">Folder:</span>
                          <p className="text-white">{config.folder_name}</p>
                        </div>
                        <div>
                          <span className="text-gray-400">Emails Processed:</span>
                          <p className="text-white">{config.emails_processed}</p>
                        </div>
                        <div>
                          <span className="text-gray-400">PDFs Found:</span>
                          <p className="text-white">{config.pdfs_found}</p>
                        </div>
                        <div>
                          <span className="text-gray-400">Last Used:</span>
                          <p className="text-white">{formatDate(config.last_used_at)}</p>
                        </div>
                        <div>
                          <span className="text-gray-400">Created:</span>
                          <p className="text-white">{formatDate(config.created_at)}</p>
                        </div>
                      </div>

                      {/* Note: Description and error info not available in summary */}
                    </div>

                    <div className="flex items-center space-x-2 ml-4">
                      <button
                        onClick={() => alert('Edit functionality coming soon!')}
                        className="inline-flex items-center px-3 py-1.5 bg-gray-600 hover:bg-gray-500 text-white text-sm rounded transition-colors"
                      >
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                        Edit
                      </button>

                      <button
                        onClick={() => handleToggleActivation(config)}
                        className={`inline-flex items-center px-3 py-1.5 text-white text-sm rounded transition-colors ${
                          config.is_active
                            ? 'bg-red-600 hover:bg-red-700'
                            : 'bg-green-600 hover:bg-green-700'
                        }`}
                      >
                        {config.is_active ? (
                          <>
                            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 6h12v12H6z" />
                            </svg>
                            Deactivate
                          </>
                        ) : (
                          <>
                            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5v14l11-7z" />
                            </svg>
                            Activate
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create Config Wizard Modal */}
      <EmailConfigWizard
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={handleCreateSuccess}
      />
    </>
  );
}