import { createFileRoute } from '@tanstack/react-router';
import { useState, useEffect } from 'react';
import {
  useEmailAccountsApi,
  type EmailAccountSummary,
  type ValidationResultResponse,
} from '../../../features/email-accounts';

export const Route = createFileRoute('/dashboard/settings/')({
  component: SettingsPage,
});

const settingsSections = [
  {
    id: 'email-connections',
    name: 'Email Connections',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
  },
];

function SettingsPage() {
  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-64 bg-gray-800 border-r border-gray-700 p-4">
        <h2 className="text-lg font-semibold text-white mb-4 px-3">Settings</h2>
        <nav className="space-y-1">
          {settingsSections.map((section) => (
            <button
              key={section.id}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors bg-gray-700 text-blue-300"
            >
              {section.icon}
              {section.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Content Area */}
      <div className="flex-1 p-6 overflow-auto">
        <EmailConnectionsSettings />
      </div>
    </div>
  );
}

function EmailConnectionsSettings() {
  const {
    getEmailAccounts,
    createEmailAccount,
    deleteEmailAccount,
    validateConnection,
    isLoading,
  } = useEmailAccountsApi();

  const [connections, setConnections] = useState<EmailAccountSummary[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Load connections on mount
  useEffect(() => {
    loadConnections();
  }, []);

  const loadConnections = async () => {
    try {
      setLoadError(null);
      const accounts = await getEmailAccounts();
      setConnections(accounts);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load connections');
    }
  };

  const handleCreate = async (data: {
    name: string;
    provider_type: string;
    email_address: string;
    imap_host: string;
    imap_port: number;
    smtp_host: string;
    smtp_port: number;
    password: string;
    use_ssl: boolean;
    capabilities: string[];
  }) => {
    try {
      await createEmailAccount({
        name: data.name,
        provider_type: data.provider_type,
        email_address: data.email_address,
        provider_settings: {
          imap_host: data.imap_host,
          imap_port: data.imap_port,
          smtp_host: data.smtp_host,
          smtp_port: data.smtp_port,
          use_ssl: data.use_ssl,
        },
        credentials: {
          type: 'password',
          password: data.password,
        },
        capabilities: data.capabilities,
      });
      setShowCreateModal(false);
      await loadConnections();
    } catch (err) {
      // Error is handled in the modal
      throw err;
    }
  };

  const handleDelete = async (id: number) => {
    try {
      setIsDeleting(true);
      await deleteEmailAccount(id);
      setDeletingId(null);
      await loadConnections();
    } catch (err) {
      console.error('Failed to delete connection:', err);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleTestConnection = async (data: {
    provider_type: string;
    email_address: string;
    imap_host: string;
    imap_port: number;
    smtp_host: string;
    smtp_port: number;
    password: string;
    use_ssl: boolean;
  }): Promise<ValidationResultResponse> => {
    return await validateConnection({
      provider_type: data.provider_type,
      email_address: data.email_address,
      provider_settings: {
        imap_host: data.imap_host,
        imap_port: data.imap_port,
        smtp_host: data.smtp_host,
        smtp_port: data.smtp_port,
        use_ssl: data.use_ssl,
      },
      credentials: {
        type: 'password',
        password: data.password,
      },
    });
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Email Connections</h1>
          <p className="text-sm text-gray-400 mt-1">
            Manage email account connections for ingestion configurations
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Connection
        </button>
      </div>

      {/* Error State */}
      {loadError && (
        <div className="mb-6 p-4 bg-red-600/10 border border-red-600/30 rounded-lg">
          <div className="flex items-center gap-3">
            <svg className="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span className="text-red-400">{loadError}</span>
            <button
              onClick={loadConnections}
              className="ml-auto text-sm text-red-400 hover:text-red-300 underline"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        {isLoading && connections.length === 0 ? (
          <div className="p-12 text-center">
            <svg className="animate-spin h-8 w-8 mx-auto text-blue-500 mb-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p className="text-gray-400">Loading connections...</p>
          </div>
        ) : connections.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-gray-500 mb-4">
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-300 mb-2">No email connections</h3>
            <p className="text-gray-500 mb-4">Get started by adding your first email connection.</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium"
            >
              Add Connection
            </button>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-900/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Email Address
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Provider
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {connections.map((connection) => (
                <tr key={connection.id} className="hover:bg-gray-700/50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-medium text-white">{connection.name}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-300">{connection.email_address}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-300 uppercase">{connection.provider_type}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        connection.is_validated
                          ? 'bg-green-600/20 text-green-400'
                          : 'bg-yellow-600/20 text-yellow-400'
                      }`}
                    >
                      {connection.is_validated ? 'Validated' : 'Not Validated'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <button
                      onClick={() => setDeletingId(connection.id)}
                      className="text-red-400 hover:text-red-300 transition-colors"
                      title="Delete connection"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <CreateEmailConnectionModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreate}
          onTestConnection={handleTestConnection}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deletingId !== null && (
        <DeleteConfirmationModal
          connectionName={connections.find((c) => c.id === deletingId)?.name || ''}
          onClose={() => setDeletingId(null)}
          onConfirm={() => handleDelete(deletingId)}
          isDeleting={isDeleting}
        />
      )}
    </div>
  );
}

// Create Email Connection Modal
function CreateEmailConnectionModal({
  onClose,
  onCreate,
  onTestConnection,
}: {
  onClose: () => void;
  onCreate: (data: {
    name: string;
    provider_type: string;
    email_address: string;
    imap_host: string;
    imap_port: number;
    smtp_host: string;
    smtp_port: number;
    password: string;
    use_ssl: boolean;
    capabilities: string[];
  }) => Promise<void>;
  onTestConnection: (data: {
    provider_type: string;
    email_address: string;
    imap_host: string;
    imap_port: number;
    smtp_host: string;
    smtp_port: number;
    password: string;
    use_ssl: boolean;
  }) => Promise<ValidationResultResponse>;
}) {
  const [step, setStep] = useState<'provider' | 'credentials'>('provider');
  const [providerType, setProviderType] = useState<string>('standard');
  const [formData, setFormData] = useState({
    name: '',
    email_address: '',
    imap_host: '',
    imap_port: 993,
    smtp_host: '',
    smtp_port: 587,
    password: '',
    use_ssl: true,
  });
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [connectionTestResult, setConnectionTestResult] = useState<ValidationResultResponse | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);

  const handleFieldChange = (field: string, value: string | number | boolean) => {
    setFormData({ ...formData, [field]: value });
    // Clear test result when credentials change
    setConnectionTestResult(null);
  };

  const handleTestConnection = async () => {
    setIsTestingConnection(true);
    setConnectionTestResult(null);

    try {
      const result = await onTestConnection({
        provider_type: providerType,
        email_address: formData.email_address,
        imap_host: formData.imap_host,
        imap_port: formData.imap_port,
        smtp_host: formData.smtp_host,
        smtp_port: formData.smtp_port,
        password: formData.password,
        use_ssl: formData.use_ssl,
      });
      setConnectionTestResult(result);
    } catch (err) {
      setConnectionTestResult({
        success: false,
        message: err instanceof Error ? err.message : 'Connection test failed',
        capabilities: [],
      });
    } finally {
      setIsTestingConnection(false);
    }
  };

  const handleSubmit = async () => {
    setIsCreating(true);
    setCreateError(null);

    try {
      await onCreate({
        name: formData.name,
        provider_type: providerType,
        email_address: formData.email_address,
        imap_host: formData.imap_host,
        imap_port: formData.imap_port,
        smtp_host: formData.smtp_host,
        smtp_port: formData.smtp_port,
        password: formData.password,
        use_ssl: formData.use_ssl,
        capabilities: connectionTestResult?.capabilities || [],
      });
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Failed to create connection');
    } finally {
      setIsCreating(false);
    }
  };

  const isCredentialsValid =
    formData.name &&
    formData.email_address &&
    formData.imap_host &&
    formData.imap_port &&
    formData.password;

  const canCreate = isCredentialsValid && connectionTestResult?.success;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg mx-4 border border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">
            {step === 'provider' ? 'Choose Provider' : 'Connection Details'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-300 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 max-h-[60vh] overflow-y-auto">
          {step === 'provider' ? (
            <div className="space-y-4">
              <p className="text-sm text-gray-400 mb-4">
                Select how you want to connect to your email account
              </p>

              <button
                onClick={() => setProviderType('standard')}
                className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
                  providerType === 'standard'
                    ? 'border-blue-600 bg-blue-600/10'
                    : 'border-gray-700 bg-gray-900 hover:border-gray-600'
                }`}
              >
                <div className="flex items-center gap-4">
                  <div className="text-3xl">📧</div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="text-base font-semibold text-white">Standard Email</h4>
                      <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">
                        Universal
                      </span>
                    </div>
                    <p className="text-sm text-gray-400 mt-1">
                      Connect using IMAP (receive) and SMTP (send)
                    </p>
                  </div>
                  <div
                    className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                      providerType === 'standard' ? 'border-blue-600 bg-blue-600' : 'border-gray-600'
                    }`}
                  >
                    {providerType === 'standard' && (
                      <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                </div>
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Connection Name */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Connection Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => handleFieldChange('name', e.target.value)}
                  placeholder="e.g., Work Email, Orders Inbox"
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
                />
              </div>

              {/* Incoming Mail (IMAP) Section */}
              <div className="p-4 bg-gray-900/50 rounded-lg border border-gray-700">
                <h4 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                  </svg>
                  Incoming Mail (IMAP)
                </h4>
                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2">
                    <label className="block text-xs font-medium text-gray-400 mb-1">
                      Server <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.imap_host}
                      onChange={(e) => handleFieldChange('imap_host', e.target.value)}
                      placeholder="imap.example.com"
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">
                      Port
                    </label>
                    <input
                      type="text"
                      value={formData.imap_port}
                      onChange={(e) => handleFieldChange('imap_port', parseInt(e.target.value) || 993)}
                      placeholder="993"
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent text-sm"
                    />
                  </div>
                </div>
              </div>

              {/* Outgoing Mail (SMTP) Section */}
              <div className="p-4 bg-gray-900/50 rounded-lg border border-gray-700">
                <h4 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                  Outgoing Mail (SMTP)
                  <span className="text-xs text-gray-500 font-normal">(optional)</span>
                </h4>
                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2">
                    <label className="block text-xs font-medium text-gray-400 mb-1">
                      Server
                    </label>
                    <input
                      type="text"
                      value={formData.smtp_host}
                      onChange={(e) => handleFieldChange('smtp_host', e.target.value)}
                      placeholder="smtp.example.com"
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">
                      Port
                    </label>
                    <input
                      type="text"
                      value={formData.smtp_port}
                      onChange={(e) => handleFieldChange('smtp_port', parseInt(e.target.value) || 587)}
                      placeholder="587"
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent text-sm"
                    />
                  </div>
                </div>
              </div>

              {/* Account Credentials Section */}
              <div className="p-4 bg-gray-900/50 rounded-lg border border-gray-700">
                <h4 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                  Account Credentials
                </h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">
                      Email Address <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="email"
                      value={formData.email_address}
                      onChange={(e) => handleFieldChange('email_address', e.target.value)}
                      placeholder="orders@example.com"
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">
                      Password <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      value={formData.password}
                      onChange={(e) => handleFieldChange('password', e.target.value)}
                      placeholder="••••••••"
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent text-sm"
                    />
                  </div>
                  <div className="flex items-center pt-1">
                    <input
                      type="checkbox"
                      id="use_ssl"
                      checked={formData.use_ssl}
                      onChange={(e) => handleFieldChange('use_ssl', e.target.checked)}
                      className="w-4 h-4 bg-gray-800 border-gray-600 rounded text-blue-600 focus:ring-2 focus:ring-blue-600"
                    />
                    <label htmlFor="use_ssl" className="ml-2 text-sm text-gray-300">
                      Use SSL/TLS (recommended)
                    </label>
                  </div>
                </div>
              </div>

              {/* Test Connection Button */}
              <div className="pt-2">
                <button
                  onClick={handleTestConnection}
                  disabled={isTestingConnection || !isCredentialsValid}
                  className="w-full px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
                >
                  {isTestingConnection ? (
                    <span className="flex items-center justify-center">
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Testing Connection...
                    </span>
                  ) : (
                    'Test Connection'
                  )}
                </button>
              </div>

              {/* Connection Test Result */}
              {connectionTestResult && (
                <div
                  className={`p-4 rounded-lg border ${
                    connectionTestResult.success
                      ? 'bg-green-600/10 border-green-600/30'
                      : 'bg-red-600/10 border-red-600/30'
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <div className={connectionTestResult.success ? 'text-green-400' : 'text-red-400'}>
                      {connectionTestResult.success ? (
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                          <path
                            fillRule="evenodd"
                            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                            clipRule="evenodd"
                          />
                        </svg>
                      ) : (
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                          <path
                            fillRule="evenodd"
                            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                            clipRule="evenodd"
                          />
                        </svg>
                      )}
                    </div>
                    <div className="flex-1">
                      <h5
                        className={`text-sm font-medium mb-1 ${
                          connectionTestResult.success ? 'text-green-400' : 'text-red-400'
                        }`}
                      >
                        {connectionTestResult.success ? 'Connection Successful' : 'Connection Failed'}
                      </h5>
                      <p className="text-sm text-gray-300">{connectionTestResult.message}</p>
                      {connectionTestResult.success && connectionTestResult.folder_count !== undefined && (
                        <p className="text-xs text-gray-400 mt-1">
                          Found {connectionTestResult.folder_count} folders
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Create Error */}
              {createError && (
                <div className="p-4 rounded-lg border bg-red-600/10 border-red-600/30">
                  <div className="flex items-center gap-2 text-red-400">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm">{createError}</span>
                  </div>
                </div>
              )}

              {/* Info: Must test before creating */}
              {!connectionTestResult?.success && isCredentialsValid && (
                <div className="p-3 rounded-lg bg-blue-600/10 border border-blue-600/30">
                  <p className="text-xs text-blue-300">
                    Please test the connection before creating the account.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-700 bg-gray-900/50">
          {step === 'provider' ? (
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 text-gray-400 hover:text-gray-300 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => setStep('credentials')}
                disabled={!providerType}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
              >
                Continue
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setStep('provider')}
                className="px-4 py-2 text-gray-400 hover:text-gray-300 transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleSubmit}
                disabled={!canCreate || isCreating}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
              >
                {isCreating ? (
                  <span className="flex items-center">
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Creating...
                  </span>
                ) : (
                  'Create Connection'
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// Delete Confirmation Modal
function DeleteConfirmationModal({
  connectionName,
  onClose,
  onConfirm,
  isDeleting,
}: {
  connectionName: string;
  onClose: () => void;
  onConfirm: () => void;
  isDeleting: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-gray-800 rounded-xl shadow-2xl w-full max-w-md mx-4 border border-gray-700">
        <div className="p-6">
          <div className="flex items-center justify-center w-12 h-12 mx-auto mb-4 rounded-full bg-red-600/20">
            <svg className="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-white text-center mb-2">Delete Connection</h3>
          <p className="text-sm text-gray-400 text-center mb-6">
            Are you sure you want to delete <span className="font-medium text-white">"{connectionName}"</span>?
            This action cannot be undone.
          </p>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              disabled={isDeleting}
              className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 text-white rounded-lg transition-colors font-medium"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              disabled={isDeleting}
              className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-500 disabled:bg-red-800 text-white rounded-lg transition-colors font-medium"
            >
              {isDeleting ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Deleting...
                </span>
              ) : (
                'Delete'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
