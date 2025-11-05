/**
 * Credentials Step
 * Dynamic credentials form based on selected provider
 */

import { useState } from 'react';

interface ImapCredentials {
  host: string;
  port: number;
  email_address: string;
  password: string;
  use_ssl: boolean;
}

interface CredentialsStepProps {
  providerType: string;
  credentials: ImapCredentials | null;
  onCredentialsChange: (credentials: ImapCredentials) => void;
  onTestConnection: () => Promise<void>;
  isTestingConnection: boolean;
  connectionTestResult: { success: boolean; message: string } | null;
}

export function CredentialsStep({
  providerType,
  credentials,
  onCredentialsChange,
  onTestConnection,
  isTestingConnection,
  connectionTestResult,
}: CredentialsStepProps) {
  const [localCredentials, setLocalCredentials] = useState<ImapCredentials>(
    credentials || {
      host: '',
      port: 993,
      email_address: '',
      password: '',
      use_ssl: true,
    }
  );

  const handleFieldChange = (field: keyof ImapCredentials, value: string | number | boolean) => {
    const updated = { ...localCredentials, [field]: value };
    setLocalCredentials(updated);
    onCredentialsChange(updated);
  };

  const handleTestClick = async () => {
    await onTestConnection();
  };

  if (providerType === 'imap') {
    return (
      <div className="space-y-4">
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-2">IMAP Server Settings</h3>
          <p className="text-sm text-gray-400">
            Enter your email server connection details
          </p>
        </div>

        <div className="space-y-4">
          {/* IMAP Server */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              IMAP Server <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={localCredentials.host}
              onChange={(e) => handleFieldChange('host', e.target.value)}
              placeholder="mail.example.com"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-gray-500">
              Example: mail.yourdomain.com or imap.gmail.com
            </p>
          </div>

          {/* Port */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Port <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              value={localCredentials.port}
              onChange={(e) => handleFieldChange('port', parseInt(e.target.value) || 993)}
              placeholder="993"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-gray-500">
              Default: 993 (SSL/TLS) or 143 (non-SSL)
            </p>
          </div>

          {/* Email Address */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Email Address <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              value={localCredentials.email_address}
              onChange={(e) => handleFieldChange('email_address', e.target.value)}
              placeholder="orders@example.com"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Password <span className="text-red-500">*</span>
            </label>
            <input
              type="password"
              value={localCredentials.password}
              onChange={(e) => handleFieldChange('password', e.target.value)}
              placeholder="••••••••"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            />
          </div>

          {/* SSL/TLS Checkbox */}
          <div className="flex items-center">
            <input
              type="checkbox"
              id="use_ssl"
              checked={localCredentials.use_ssl}
              onChange={(e) => handleFieldChange('use_ssl', e.target.checked)}
              className="w-4 h-4 bg-gray-800 border-gray-700 rounded text-blue-600 focus:ring-2 focus:ring-blue-600"
            />
            <label htmlFor="use_ssl" className="ml-2 text-sm text-gray-300">
              Use SSL/TLS (recommended)
            </label>
          </div>

          {/* Test Connection Button */}
          <div className="pt-4">
            <button
              onClick={handleTestClick}
              disabled={
                isTestingConnection ||
                !localCredentials.host ||
                !localCredentials.email_address ||
                !localCredentials.password
              }
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
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
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Info Box */}
        <div className="mt-6 p-4 rounded-lg bg-gray-800/50 border border-gray-700">
          <div className="flex items-start space-x-3">
            <div className="text-gray-400 flex-shrink-0 mt-0.5">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="flex-1">
              <h5 className="text-sm font-medium text-gray-300 mb-1">Where to find these settings</h5>
              <p className="text-sm text-gray-400 leading-relaxed">
                Contact your email provider or IT administrator for IMAP server settings.
                Common providers: Gmail (imap.gmail.com), Outlook (outlook.office365.com),
                or your custom domain's mail server.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return <div>Provider not supported yet</div>;
}
