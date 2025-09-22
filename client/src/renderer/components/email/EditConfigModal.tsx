import { useState, useEffect } from 'react';
// Icons are inline SVG components
import { apiClient } from '../../services/api';
import type { EmailConfig, EmailConfigUpdate, EmailFilterRule } from '../../services/api';

interface EditConfigModalProps {
  config: EmailConfig;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function EditConfigModal({ config, isOpen, onClose, onSuccess }: EditConfigModalProps) {
  const [formData, setFormData] = useState<EmailConfigUpdate>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && config) {
      // Initialize form with current config values
      setFormData({
        name: config.name,
        description: config.description || '',
        email_address: config.email_address,
        folder_name: config.folder_name,
        filter_rules: [...config.filter_rules],
        poll_interval_seconds: config.poll_interval_seconds,
        max_backlog_hours: config.max_backlog_hours,
        error_retry_attempts: config.error_retry_attempts,
      });
      setError(null);
    }
  }, [isOpen, config]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await apiClient.emailConfigs.updateConfig(config.id, formData);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterRuleChange = (index: number, field: keyof EmailFilterRule, value: string | boolean) => {
    const newFilterRules = [...(formData.filter_rules || [])];
    newFilterRules[index] = { ...newFilterRules[index], [field]: value };
    setFormData({ ...formData, filter_rules: newFilterRules });
  };

  const addFilterRule = () => {
    const newFilterRules = [...(formData.filter_rules || [])];
    newFilterRules.push({
      field: 'sender_email',
      operation: 'contains',
      value: '',
      case_sensitive: false,
    });
    setFormData({ ...formData, filter_rules: newFilterRules });
  };

  const removeFilterRule = (index: number) => {
    const newFilterRules = [...(formData.filter_rules || [])];
    newFilterRules.splice(index, 1);
    setFormData({ ...formData, filter_rules: newFilterRules });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen p-4">
        <div className="fixed inset-0 bg-black bg-opacity-50" onClick={onClose}></div>

        <div className="relative bg-gray-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-between p-6 border-b border-gray-700">
            <h2 className="text-xl font-semibold text-white">Edit Email Configuration</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="p-6">
            {error && (
              <div className="bg-red-900/20 border border-red-700 rounded-lg p-3 mb-4">
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}

            <div className="space-y-4">
              {/* Basic Information */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Configuration Name *
                </label>
                <input
                  type="text"
                  value={formData.name || ''}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Description
                </label>
                <textarea
                  value={formData.description || ''}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={2}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Email Address *
                </label>
                <input
                  type="email"
                  value={formData.email_address || ''}
                  onChange={(e) => setFormData({ ...formData, email_address: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Folder Name *
                </label>
                <input
                  type="text"
                  value={formData.folder_name || ''}
                  onChange={(e) => setFormData({ ...formData, folder_name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              </div>

              {/* Advanced Settings */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Poll Interval (seconds)
                  </label>
                  <input
                    type="number"
                    min="5"
                    value={formData.poll_interval_seconds || 5}
                    onChange={(e) => setFormData({ ...formData, poll_interval_seconds: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Max Backlog (hours)
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={formData.max_backlog_hours || 24}
                    onChange={(e) => setFormData({ ...formData, max_backlog_hours: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Retry Attempts
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={formData.error_retry_attempts || 3}
                    onChange={(e) => setFormData({ ...formData, error_retry_attempts: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              {/* Filter Rules */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-300">
                    Filter Rules
                  </label>
                  <button
                    type="button"
                    onClick={addFilterRule}
                    className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors"
                  >
                    Add Rule
                  </button>
                </div>

                {formData.filter_rules && formData.filter_rules.length > 0 && (
                  <div className="space-y-2">
                    {formData.filter_rules.map((rule, index) => (
                      <div key={index} className="flex items-center space-x-2 p-3 bg-gray-700 rounded-md">
                        <select
                          value={rule.field}
                          onChange={(e) => handleFilterRuleChange(index, 'field', e.target.value)}
                          className="px-2 py-1 bg-gray-600 border border-gray-500 rounded text-white text-sm"
                        >
                          <option value="sender_email">Sender Email</option>
                          <option value="subject">Subject</option>
                          <option value="has_attachments">Has Attachments</option>
                          <option value="received_date">Received Date</option>
                        </select>

                        <select
                          value={rule.operation}
                          onChange={(e) => handleFilterRuleChange(index, 'operation', e.target.value)}
                          className="px-2 py-1 bg-gray-600 border border-gray-500 rounded text-white text-sm"
                        >
                          <option value="contains">Contains</option>
                          <option value="equals">Equals</option>
                          <option value="starts_with">Starts With</option>
                          <option value="ends_with">Ends With</option>
                          <option value="before">Before</option>
                          <option value="after">After</option>
                        </select>

                        <input
                          type="text"
                          value={rule.value}
                          onChange={(e) => handleFilterRuleChange(index, 'value', e.target.value)}
                          placeholder="Value"
                          className="flex-1 px-2 py-1 bg-gray-600 border border-gray-500 rounded text-white text-sm placeholder-gray-400"
                        />

                        <label className="flex items-center text-sm text-gray-300">
                          <input
                            type="checkbox"
                            checked={rule.case_sensitive}
                            onChange={(e) => handleFilterRuleChange(index, 'case_sensitive', e.target.checked)}
                            className="mr-1"
                          />
                          Case sensitive
                        </label>

                        <button
                          type="button"
                          onClick={() => removeFilterRule(index)}
                          className="px-2 py-1 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors"
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center justify-end space-x-3 mt-6 pt-4 border-t border-gray-700">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}