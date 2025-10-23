/**
 * Edit Email Configuration Modal
 * Allows editing configuration settings (must be deactivated first)
 */

import { useState, useEffect } from 'react';
import type { EmailConfigDetail, FilterRule } from '../types';

interface EditConfigModalProps {
  isOpen: boolean;
  config: EmailConfigDetail | null;
  onClose: () => void;
  onSave: (
    id: number,
    data: {
      description?: string | null;
      filter_rules?: FilterRule[];
      poll_interval_seconds?: number;
      max_backlog_hours?: number;
      error_retry_attempts?: number;
    }
  ) => Promise<void>;
}

export function EditConfigModal({
  isOpen,
  config,
  onClose,
  onSave,
}: EditConfigModalProps) {
  const [description, setDescription] = useState('');
  const [pollInterval, setPollInterval] = useState(60);
  const [maxBacklog, setMaxBacklog] = useState(24);
  const [retryAttempts, setRetryAttempts] = useState(3);
  const [filterRules, setFilterRules] = useState<FilterRule[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  // Reset form when modal opens with new config
  useEffect(() => {
    if (config && isOpen) {
      setDescription(config.description || '');
      setPollInterval(config.poll_interval_seconds);
      setMaxBacklog(config.max_backlog_hours);
      setRetryAttempts(config.error_retry_attempts);
      setFilterRules(config.filter_rules || []);
    }
  }, [config, isOpen]);

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

  const handleSave = async () => {
    if (!config) return;

    setIsSaving(true);
    try {
      await onSave(config.id, {
        description: description.trim() || null,
        filter_rules: filterRules,
        poll_interval_seconds: pollInterval,
        max_backlog_hours: maxBacklog,
        error_retry_attempts: retryAttempts,
      });
      onClose();
    } catch (err) {
      console.error('Failed to save configuration:', err);
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen || !config) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-gray-900 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden border border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-xl font-semibold text-white">Edit Configuration: {config.name}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-160px)] p-6 space-y-6">
          {/* Warning if active */}
          {config.is_active && (
            <div className="bg-yellow-900/20 border border-yellow-700 rounded-lg p-4">
              <div className="flex items-start space-x-2">
                <svg
                  className="w-5 h-5 text-yellow-400 mt-0.5 flex-shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                <div>
                  <p className="text-sm font-medium text-yellow-300">
                    Configuration is currently active
                  </p>
                  <p className="text-xs text-yellow-400 mt-1">
                    You must deactivate this configuration before editing.
                  </p>
                </div>
              </div>
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
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-gray-400 cursor-not-allowed"
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
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-gray-400 cursor-not-allowed"
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              disabled={config.is_active}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none disabled:opacity-50 disabled:cursor-not-allowed"
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
                  value={pollInterval}
                  onChange={(e) => setPollInterval(parseInt(e.target.value) || 60)}
                  disabled={config.is_active}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
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
                  value={maxBacklog}
                  onChange={(e) => setMaxBacklog(parseInt(e.target.value) || 24)}
                  disabled={config.is_active}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
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
                  value={retryAttempts}
                  onChange={(e) => setRetryAttempts(parseInt(e.target.value) || 3)}
                  disabled={config.is_active}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
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
                onClick={handleAddFilterRule}
                disabled={config.is_active}
                className="inline-flex items-center px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
              >
                <svg
                  className="w-4 h-4 mr-1"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 4v16m8-8H4"
                  />
                </svg>
                Add Rule
              </button>
            </div>

            {filterRules.length === 0 ? (
              <p className="text-gray-400 text-sm py-4 text-center bg-gray-800/30 rounded border border-gray-700">
                No filter rules defined. All emails will be processed.
              </p>
            ) : (
              <div className="space-y-3">
                {filterRules.map((rule, index) => (
                  <div key={index} className="bg-gray-800 rounded p-3 border border-gray-700">
                    <div className="grid grid-cols-12 gap-2 items-end">
                      <div className="col-span-3">
                        <label className="block text-xs font-medium text-gray-400 mb-1">
                          Field
                        </label>
                        <select
                          value={rule.field}
                          onChange={(e) => handleUpdateFilterRule(index, 'field', e.target.value)}
                          disabled={config.is_active}
                          className="w-full px-2 py-1.5 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <option value="sender_email">Sender Email</option>
                          <option value="subject">Subject</option>
                          <option value="has_attachments">Has Attachments</option>
                          <option value="attachment_types">Attachment Types</option>
                        </select>
                      </div>
                      <div className="col-span-3">
                        <label className="block text-xs font-medium text-gray-400 mb-1">
                          Operation
                        </label>
                        <select
                          value={rule.operation}
                          onChange={(e) =>
                            handleUpdateFilterRule(index, 'operation', e.target.value)
                          }
                          disabled={config.is_active}
                          className="w-full px-2 py-1.5 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <option value="contains">Contains</option>
                          <option value="equals">Equals</option>
                          <option value="starts_with">Starts With</option>
                          <option value="ends_with">Ends With</option>
                        </select>
                      </div>
                      <div className="col-span-4">
                        <label className="block text-xs font-medium text-gray-400 mb-1">
                          Value
                        </label>
                        <input
                          type="text"
                          value={rule.value}
                          onChange={(e) => handleUpdateFilterRule(index, 'value', e.target.value)}
                          disabled={config.is_active}
                          placeholder="Filter value..."
                          className="w-full px-2 py-1.5 bg-gray-700 border border-gray-600 rounded text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                        />
                      </div>
                      <div className="col-span-2 flex items-center justify-between">
                        <label className="flex items-center text-xs text-gray-300">
                          <input
                            type="checkbox"
                            checked={rule.case_sensitive}
                            onChange={(e) =>
                              handleUpdateFilterRule(index, 'case_sensitive', e.target.checked)
                            }
                            disabled={config.is_active}
                            className="mr-1 rounded bg-gray-700 border-gray-600 text-blue-600 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                          />
                          Case
                        </label>
                        <button
                          type="button"
                          onClick={() => handleRemoveFilterRule(index)}
                          disabled={config.is_active}
                          className="p-1 text-red-400 hover:text-red-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Remove rule"
                        >
                          <svg
                            className="w-4 h-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M6 18L18 6M6 6l12 12"
                            />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-4 border-t border-gray-700">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-gray-600 text-gray-300 rounded hover:bg-gray-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving || config.is_active}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded transition-colors"
          >
            {isSaving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}
