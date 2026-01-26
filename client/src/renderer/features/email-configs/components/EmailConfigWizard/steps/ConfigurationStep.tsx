/**
 * Configuration Step (Step 3)
 * Allows user to configure settings and filter rules
 */

import type { FilterRule } from '../../../types';

interface ConfigurationStepProps {
  name: string;
  description: string;
  pollInterval: number;
  filterRules: FilterRule[];
  emailAccount: string;
  folderName: string;
  onNameChange: (name: string) => void;
  onDescriptionChange: (description: string) => void;
  onPollIntervalChange: (interval: number) => void;
  onAddFilterRule: () => void;
  onUpdateFilterRule: (index: number, field: keyof FilterRule, value: any) => void;
  onRemoveFilterRule: (index: number) => void;
}

export function ConfigurationStep({
  name,
  description,
  pollInterval,
  filterRules,
  emailAccount,
  folderName,
  onNameChange,
  onDescriptionChange,
  onPollIntervalChange,
  onAddFilterRule,
  onUpdateFilterRule,
  onRemoveFilterRule,
}: ConfigurationStepProps) {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-white">Configuration Settings</h3>

      {/* Basic Info */}
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Configuration Name <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter configuration name"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => onDescriptionChange(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            placeholder="Optional description"
          />
        </div>
      </div>

      {/* Monitoring Settings */}
      <div>
        <h4 className="text-sm font-medium text-gray-300 mb-3">Monitoring Settings</h4>
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-1">
            Poll Interval (seconds)
          </label>
          <input
            type="number"
            value={pollInterval}
            onChange={(e) => {
              const value = parseInt(e.target.value);
              // Allow any number during typing (including below minimum)
              if (!isNaN(value)) {
                onPollIntervalChange(value);
              } else if (e.target.value === '') {
                // Allow empty string during typing
                onPollIntervalChange(0);
              }
            }}
            onBlur={(e) => {
              const value = parseInt(e.target.value);
              // Enforce minimum of 5 when user exits the field
              if (isNaN(value) || value < 5) {
                onPollIntervalChange(5);
              }
            }}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Filter Rules */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <label className="block text-sm font-medium text-gray-300">
            Email Filter Rules
          </label>
          <button
            type="button"
            onClick={onAddFilterRule}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors"
          >
            + Add Rule
          </button>
        </div>

        {filterRules.length === 0 ? (
          <p className="text-gray-400 text-sm py-4 text-center bg-gray-700/30 rounded border border-gray-700">
            No filter rules added. All emails will be processed.
          </p>
        ) : (
          <div className="space-y-3">
            {filterRules.map((rule, index) => (
              <div key={index} className="bg-gray-700 rounded-lg p-3">
                <div className="grid grid-cols-12 gap-2 items-end">
                  <div className="col-span-3">
                    <label className="block text-xs font-medium text-gray-400 mb-1">
                      Field
                    </label>
                    <select
                      value={rule.field}
                      onChange={(e) => onUpdateFilterRule(index, 'field', e.target.value)}
                      className="w-full px-2 py-1.5 bg-gray-600 border border-gray-500 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                    <div className="flex gap-1">
                      <button
                        type="button"
                        onClick={() => onUpdateFilterRule(index, 'negate', !rule.negate)}
                        className={`px-1.5 py-1.5 rounded text-xs font-bold shrink-0 transition-colors ${
                          rule.negate
                            ? 'bg-red-600 text-white'
                            : 'bg-gray-600 text-gray-400 hover:bg-gray-500'
                        }`}
                        title={rule.negate ? 'Negated - click to remove' : 'Click to negate this rule'}
                      >
                        NOT
                      </button>
                      <select
                        value={rule.operation}
                        onChange={(e) => onUpdateFilterRule(index, 'operation', e.target.value)}
                        className="w-full px-2 py-1.5 bg-gray-600 border border-gray-500 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="contains">Contains</option>
                        <option value="equals">Equals</option>
                        <option value="starts_with">Starts With</option>
                        <option value="ends_with">Ends With</option>
                      </select>
                    </div>
                  </div>

                  <div className="col-span-4">
                    <label className="block text-xs font-medium text-gray-400 mb-1">
                      Value
                    </label>
                    <input
                      type="text"
                      value={rule.value}
                      onChange={(e) => onUpdateFilterRule(index, 'value', e.target.value)}
                      placeholder="Filter value..."
                      className="w-full px-2 py-1.5 bg-gray-600 border border-gray-500 rounded text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div className="col-span-2 flex items-center justify-between">
                    <label className="flex items-center text-xs text-gray-300">
                      <input
                        type="checkbox"
                        checked={rule.case_sensitive}
                        onChange={(e) => onUpdateFilterRule(index, 'case_sensitive', e.target.checked)}
                        className="mr-1 rounded bg-gray-600 border-gray-500 text-blue-600 focus:ring-blue-500"
                      />
                      Case
                    </label>
                    <button
                      type="button"
                      onClick={() => onRemoveFilterRule(index)}
                      className="p-1 text-red-400 hover:text-red-300 transition-colors"
                      title="Remove rule"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Configuration Summary */}
      <div className="bg-gray-700/50 border border-gray-600 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Configuration Summary</h4>
        <div className="text-sm text-gray-400 space-y-1">
          <p>
            <strong className="text-gray-300">Email:</strong> {emailAccount}
          </p>
          <p>
            <strong className="text-gray-300">Folder:</strong> {folderName}
          </p>
          <p>
            <strong className="text-gray-300">Poll Interval:</strong> {pollInterval} seconds
          </p>
          <p>
            <strong className="text-gray-300">Filter Rules:</strong> {filterRules.length} rule
            {filterRules.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>
    </div>
  );
}
