/**
 * ExtractionFieldsSidebar
 * Sidebar for managing extraction fields with three view modes:
 * - List: Shows all extraction fields
 * - Create: Form to create new extraction field
 * - Detail: View/delete existing extraction field
 */

import { useRef, useEffect, useState } from 'react';
import { ExtractionField } from '../../../../types';

export type SidebarMode = 'list' | 'create' | 'detail';

interface ExtractionFieldsSidebarProps {
  templateName: string;
  templateDescription: string;
  extractionFields: ExtractionField[];
  mode: SidebarMode;
  selectedFieldId: string | null;
  showSignatureObjects: boolean;

  // Form state for create/edit
  fieldLabel: string;
  fieldDescription: string;
  fieldRequired: boolean;
  fieldValidationRegex: string;
  tempFieldData: { bbox: [number, number, number, number]; page: number } | null;

  // Callbacks
  onTemplateNameChange: (name: string) => void;
  onTemplateDescriptionChange: (description: string) => void;
  onShowSignatureObjectsChange: (show: boolean) => void;
  onFieldLabelChange: (label: string) => void;
  onFieldDescriptionChange: (description: string) => void;
  onFieldRequiredChange: (required: boolean) => void;
  onFieldValidationRegexChange: (regex: string) => void;
  onSaveField: () => void;
  onCancelField: () => void;
  onDeleteField: (fieldId: string) => void;
  onSelectField: (fieldId: string) => void;
  onBackToList: () => void;
  onUpdateField: (fieldId: string, updates: Partial<ExtractionField>) => void;
}

export function ExtractionFieldsSidebar({
  templateName,
  templateDescription,
  extractionFields,
  mode,
  selectedFieldId,
  showSignatureObjects,
  fieldLabel,
  fieldDescription,
  fieldRequired,
  fieldValidationRegex,
  tempFieldData,
  onTemplateNameChange,
  onTemplateDescriptionChange,
  onShowSignatureObjectsChange,
  onFieldLabelChange,
  onFieldDescriptionChange,
  onFieldRequiredChange,
  onFieldValidationRegexChange,
  onSaveField,
  onCancelField,
  onDeleteField,
  onSelectField,
  onBackToList,
  onUpdateField,
}: ExtractionFieldsSidebarProps) {
  const fieldLabelInputRef = useRef<HTMLInputElement>(null);
  const [isEditingLabel, setIsEditingLabel] = useState(false);
  const [editedLabel, setEditedLabel] = useState('');

  // Auto-focus field label input when entering create mode
  useEffect(() => {
    if (mode === 'create' && fieldLabelInputRef.current) {
      fieldLabelInputRef.current.focus();
      fieldLabelInputRef.current.select();
    }
  }, [mode]);

  // Reset edit mode when selection changes
  useEffect(() => {
    setIsEditingLabel(false);
  }, [selectedFieldId]);

  // Handle Enter key press in form fields
  const handleFieldFormKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (fieldLabel.trim()) {
        onSaveField();
      }
    }
  };

  const selectedField = extractionFields.find(f => f.field_id === selectedFieldId);

  return (
    <div className="flex flex-col h-full">
      {/* Template Information - Editable */}
      <div className="pb-4 mb-4 border-b border-gray-700">
        <h3 className="text-sm font-semibold text-white mb-3">Template Information</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Template Name</label>
            <input
              type="text"
              value={templateName}
              onChange={(e) => onTemplateNameChange(e.target.value)}
              placeholder="Enter template name"
              className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Description</label>
            <textarea
              value={templateDescription}
              onChange={(e) => onTemplateDescriptionChange(e.target.value)}
              placeholder="Enter template description"
              rows={2}
              className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none resize-none"
            />
          </div>
          <div className="flex items-center pt-1">
            <input
              type="checkbox"
              id="showSignatureObjects"
              checked={showSignatureObjects}
              onChange={(e) => onShowSignatureObjectsChange(e.target.checked)}
              className="mr-2"
            />
            <label htmlFor="showSignatureObjects" className="text-xs text-gray-300">Show signature objects</label>
          </div>
        </div>
      </div>

      {/* Dynamic Content Area */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {/* List Mode */}
        {mode === 'list' && (
          <>
            <h3 className="text-sm font-semibold text-white mb-2">
              Extraction Fields ({extractionFields.length})
            </h3>
            <div className="flex-1 overflow-y-auto space-y-2">
              {extractionFields.length === 0 ? (
                <div className="bg-gray-800 rounded p-3 text-center">
                  <div className="text-sm text-gray-400">No fields defined yet</div>
                  <div className="text-xs text-gray-500 mt-1">
                    Draw areas on the PDF to create fields
                  </div>
                </div>
              ) : (
                extractionFields.map((field) => (
                  <button
                    key={field.field_id}
                    onClick={() => onSelectField(field.field_id)}
                    className="w-full text-left px-3 py-2 rounded text-sm bg-gray-800 hover:bg-gray-700 text-gray-300 transition-colors"
                  >
                    <div className="font-medium truncate">{field.label}</div>
                    <div className="text-xs text-gray-400 truncate mt-1">
                      Page {field.page + 1}{field.required && ' • Required'}
                    </div>
                  </button>
                ))
              )}
            </div>
          </>
        )}

        {/* Create Mode */}
        {mode === 'create' && (
          <div className="flex-1 overflow-y-auto">
            <div className="flex items-center mb-4">
              <button
                onClick={onCancelField}
                className="mr-3 p-1 text-gray-400 hover:text-white"
              >
                ← Back
              </button>
              <h3 className="text-sm font-semibold text-white">Create Extraction Field</h3>
            </div>

            {/* Show the drawn area information */}
            {tempFieldData && (
              <div className="mb-4 p-3 bg-gray-800 border border-gray-600 rounded">
                <div className="text-xs text-gray-400 mb-1">Extraction Area:</div>
                <div className="text-sm text-white">Page {tempFieldData.page + 1}</div>
                <div className="text-xs text-gray-500 mt-1">
                  Box: {tempFieldData.bbox.map(n => Math.round(n)).join(', ')}
                </div>
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1">Field Label *</label>
                <input
                  ref={fieldLabelInputRef}
                  type="text"
                  value={fieldLabel}
                  onChange={(e) => onFieldLabelChange(e.target.value)}
                  onKeyDown={handleFieldFormKeyDown}
                  placeholder="e.g., hawb, carrier-name"
                  className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1">Description</label>
                <textarea
                  value={fieldDescription}
                  onChange={(e) => onFieldDescriptionChange(e.target.value)}
                  rows={2}
                  placeholder="Describe what this field contains..."
                  className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none resize-none"
                />
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="required"
                  checked={fieldRequired}
                  onChange={(e) => onFieldRequiredChange(e.target.checked)}
                  className="mr-2"
                />
                <label htmlFor="required" className="text-xs text-gray-300">Required field</label>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1">Validation Regex (Optional)</label>
                <input
                  type="text"
                  value={fieldValidationRegex}
                  onChange={(e) => onFieldValidationRegexChange(e.target.value)}
                  onKeyDown={handleFieldFormKeyDown}
                  placeholder="^[A-Z0-9]+$"
                  className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={onSaveField}
                  disabled={!fieldLabel.trim()}
                  className="flex-1 px-3 py-2 text-sm bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded transition-colors"
                >
                  Save Field
                </button>
                <button
                  onClick={onCancelField}
                  className="px-3 py-2 text-sm bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Detail Mode */}
        {mode === 'detail' && selectedField && (
          <div className="flex-1 overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <button
                onClick={onBackToList}
                className="p-1 text-gray-400 hover:text-white"
              >
                ← Back
              </button>
              <h3 className="text-sm font-semibold text-white flex-1 text-center">Extraction Field</h3>
              <button
                onClick={() => onDeleteField(selectedField.field_id)}
                className="w-8 h-8 bg-red-600 hover:bg-red-700 hover:scale-105 rounded text-white transition-all duration-200 flex items-center justify-center"
                title="Delete field"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-medium text-gray-400">Label</label>
                  {!isEditingLabel && (
                    <button
                      onClick={() => {
                        setIsEditingLabel(true);
                        setEditedLabel(selectedField.label);
                      }}
                      className="text-xs text-blue-400 hover:text-blue-300"
                    >
                      Edit
                    </button>
                  )}
                </div>
                {isEditingLabel ? (
                  <div className="space-y-2">
                    <input
                      type="text"
                      value={editedLabel}
                      onChange={(e) => setEditedLabel(e.target.value)}
                      className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-600 rounded text-white focus:border-blue-500 focus:outline-none"
                      autoFocus
                    />
                    <div className="flex space-x-2">
                      <button
                        onClick={() => {
                          if (editedLabel.trim()) {
                            onUpdateField(selectedField.field_id, { label: editedLabel });
                            setIsEditingLabel(false);
                          }
                        }}
                        disabled={!editedLabel.trim()}
                        className="flex-1 px-3 py-1 text-xs bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded transition-colors"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => setIsEditingLabel(false)}
                        className="px-3 py-1 text-xs bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-white">{selectedField.label}</div>
                )}
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Description</label>
                <div className="text-sm text-gray-300">{selectedField.description || 'No description'}</div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Required</label>
                <div className="text-sm text-gray-300">{selectedField.required ? 'Yes' : 'No'}</div>
              </div>
              {selectedField.validation_regex && (
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1">Validation</label>
                  <div className="text-sm text-gray-300 font-mono">{selectedField.validation_regex}</div>
                </div>
              )}
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Extraction Area</label>
                <div className="text-sm text-gray-300">
                  Page {selectedField.page + 1}<br/>
                  Box: {selectedField.bbox.map(n => Math.round(n)).join(', ')}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
