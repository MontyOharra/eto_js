import React, { useState, useEffect } from 'react';
import type { EmailIngestionConfig } from '../../services/api';

interface EmailConfigEditModalProps {
  isOpen: boolean;
  config: EmailIngestionConfig | null;
  onClose: () => void;
  onSuccess: () => void;
}

export function EmailConfigEditModal({ isOpen, config, onClose, onSuccess }: EmailConfigEditModalProps) {
  const [formData, setFormData] = useState({
    description: '',
    poll_interval_seconds: 300,
    max_backlog_hours: 24,
    error_retry_attempts: 3,
    filter_rules: [] as Array<{
      field: string;
      operation: string;
      value: string;
      case_sensitive: boolean;
    }>
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when modal opens with new config
  useEffect(() => {
    if (config && isOpen) {
      setFormData({
        description: config.description || '',
        poll_interval_seconds: config.poll_interval_seconds,
        max_backlog_hours: config.max_backlog_hours,
        error_retry_attempts: config.error_retry_attempts,
        filter_rules: config.filter_rules || []
      });
      setError(null);
    }
  }, [config, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!config) return;

    setLoading(true);
    setError(null);

    try {
      // Import API client inside the function to avoid dependency issues
      const { apiClient } = await import('../../services/api');

      const updateData = {
        description: formData.description.trim() || undefined,
        filter_rules: formData.filter_rules,
        poll_interval_seconds: typeof formData.poll_interval_seconds === 'string' ?
          (parseInt(formData.poll_interval_seconds) || 300) : formData.poll_interval_seconds,
        max_backlog_hours: typeof formData.max_backlog_hours === 'string' ?
          (parseInt(formData.max_backlog_hours) || 24) : formData.max_backlog_hours,
        error_retry_attempts: typeof formData.error_retry_attempts === 'string' ?
          (parseInt(formData.error_retry_attempts) || 3) : formData.error_retry_attempts,
      };

      const response = await apiClient.updateEmailIngestionConfig(config.id, updateData);

      if (response.success) {
        onSuccess();
        onClose();
      } else {
        setError('Failed to update configuration');
      }
    } catch (err) {
      console.error('Error updating config:', err);
      setError(err instanceof Error ? err.message : 'Failed to update configuration');
    } finally {
      setLoading(false);
    }
  };

  const addFilterRule = () => {
    setFormData(prev => ({
      ...prev,
      filter_rules: [
        ...prev.filter_rules,
        { field: 'subject', operation: 'contains', value: '', case_sensitive: false }
      ]
    }));
  };

  const removeFilterRule = (index: number) => {
    setFormData(prev => ({
      ...prev,
      filter_rules: prev.filter_rules.filter((_, i) => i !== index)
    }));
  };

  const updateFilterRule = (index: number, field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      filter_rules: prev.filter_rules.map((rule, i) =>
        i === index ? { ...rule, [field]: value } : rule
      )
    }));
  };

  if (!isOpen || !config) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <h2 className="text-xl font-semibold text-white">
            Edit Configuration: {config.name}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="overflow-y-auto max-h-[calc(90vh-180px)]">
          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {error && (
              <div className="bg-red-900/20 border border-red-700 rounded-lg p-4">
                <p className="text-red-400">{error}</p>
              </div>
            )}

            {/* Read-only fields */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Email Address (Read-only)
                </label>
                <input
                  type="text"
                  value={config.email_address}
                  readOnly
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-400 cursor-not-allowed"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Folder (Read-only)
                </label>
                <input
                  type="text"
                  value={config.folder_name}
                  readOnly
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-400 cursor-not-allowed"
                />
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                rows={3}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Optional description for this configuration"
              />
            </div>

            {/* Monitoring Settings */}
            <div>
              <h3 className="text-lg font-medium text-white mb-4">Monitoring Settings</h3>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Poll Interval (seconds)
                  </label>
                  <input
                    type="number"
                    min="5"
                    max="3600"
                    value={formData.poll_interval_seconds}
                    onChange={(e) => {
                      const inputValue = e.target.value;
                      if (inputValue === '') {
                        // Allow empty field while typing
                        setFormData(prev => ({ ...prev, poll_interval_seconds: '' as any }));
                      } else {
                        const numericValue = parseInt(inputValue);
                        if (!isNaN(numericValue)) {
                          setFormData(prev => ({ ...prev, poll_interval_seconds: numericValue }));
                        }
                      }
                    }}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Max Backlog (hours)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="168"
                    value={formData.max_backlog_hours}
                    onChange={(e) => setFormData(prev => ({ ...prev, max_backlog_hours: parseInt(e.target.value) || 24 }))}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Retry Attempts
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="10"
                    value={formData.error_retry_attempts}
                    onChange={(e) => setFormData(prev => ({ ...prev, error_retry_attempts: parseInt(e.target.value) || 3 }))}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>
            </div>

            {/* Filter Rules */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-white">Filter Rules</h3>
                <button
                  type="button"
                  onClick={addFilterRule}
                  className="inline-flex items-center px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors"
                >
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Add Rule
                </button>
              </div>

              {formData.filter_rules.length === 0 ? (
                <p className="text-gray-400 text-sm">No filter rules defined. All emails will be processed.</p>
              ) : (
                <div className="space-y-3">
                  {formData.filter_rules.map((rule, index) => (
                    <div key={index} className="bg-gray-700 rounded p-4">
                      <div className="grid grid-cols-4 gap-3 items-end">
                        <div>
                          <label className="block text-sm font-medium text-gray-300 mb-1">Field</label>
                          <select
                            value={rule.field}
                            onChange={(e) => updateFilterRule(index, 'field', e.target.value)}
                            className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                          >
                            <option value="subject">Subject</option>
                            <option value="sender_email">Sender Email</option>
                            <option value="has_attachments">Has Attachments</option>
                            <option value="received_date">Received Date</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-300 mb-1">Operation</label>
                          <select
                            value={rule.operation}
                            onChange={(e) => updateFilterRule(index, 'operation', e.target.value)}
                            className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                          >
                            <option value="contains">Contains</option>
                            <option value="equals">Equals</option>
                            <option value="starts_with">Starts With</option>
                            <option value="ends_with">Ends With</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-300 mb-1">Value</label>
                          <input
                            type="text"
                            value={rule.value}
                            onChange={(e) => updateFilterRule(index, 'value', e.target.value)}
                            placeholder="Filter value..."
                            className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                        <div className="flex items-center space-x-2">
                          <label className="flex items-center">
                            <input
                              type="checkbox"
                              checked={rule.case_sensitive}
                              onChange={(e) => updateFilterRule(index, 'case_sensitive', e.target.checked)}
                              className="rounded bg-gray-600 border-gray-500 text-blue-600 focus:ring-blue-500"
                            />
                            <span className="ml-2 text-sm text-gray-300">Case sensitive</span>
                          </label>
                          <button
                            type="button"
                            onClick={() => removeFilterRule(index)}
                            className="p-2 text-red-400 hover:text-red-300 transition-colors"
                            title="Remove rule"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </form>
        </div>

        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-700">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-gray-600 text-gray-300 rounded hover:bg-gray-700 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded transition-colors"
          >
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}