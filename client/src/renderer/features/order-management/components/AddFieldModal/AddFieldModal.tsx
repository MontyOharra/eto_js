/**
 * AddFieldModal Component
 *
 * Compact modal for manually adding a field value to a pending action.
 * Shows a dropdown to select a field, then displays the appropriate
 * input component based on the field's data type.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import type { OrderFieldDataType } from '../../types';
import { AddressSearchPicker } from './AddressSearchPicker';

// Field metadata passed from parent
interface FieldOption {
  name: string;
  label: string;
  data_type: OrderFieldDataType;
  category?: string;
}

// Value types for different field types
export interface DateTimeValue {
  date: string;
  startTime: string;
  endTime: string;
}

export interface LocationValue {
  mode: 'select' | 'create';
  addressId?: number;
  companyName?: string;
  address?: string;
}

export interface DimRow {
  qty: number;
  length: number;
  width: number;
  height: number;
  weight: number;
}

type FieldValue = string | DateTimeValue | LocationValue | DimRow[];

// Helper to get initial value based on field type
function getInitialValue(dataType: OrderFieldDataType): FieldValue {
  switch (dataType) {
    case 'datetime_range':
      return { date: '', startTime: '', endTime: '' };
    case 'location':
      return { mode: 'select', addressId: undefined, companyName: '', address: '' };
    case 'dims':
      return [{ qty: 1, length: 1, width: 1, height: 1, weight: 1 }];
    case 'string':
    default:
      return '';
  }
}

interface AddFieldModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (fieldName: string, value: unknown) => void;
  /** Available fields that can be added */
  availableFields: FieldOption[];
  /** Fields that already have values (to show indicator) */
  existingFieldNames?: Set<string>;
  isSubmitting?: boolean;
}

export function AddFieldModal({
  isOpen,
  onClose,
  onSubmit,
  availableFields,
  existingFieldNames = new Set(),
  isSubmitting = false,
}: AddFieldModalProps) {
  const [selectedFieldName, setSelectedFieldName] = useState<string>('');
  const [fieldValue, setFieldValue] = useState<FieldValue>('');

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setSelectedFieldName('');
      setFieldValue('');
    }
  }, [isOpen]);

  // Get the selected field's metadata
  const selectedField = useMemo(() => {
    return availableFields.find((f) => f.name === selectedFieldName) ?? null;
  }, [availableFields, selectedFieldName]);

  // Handle field selection change - reset value to appropriate type
  const handleFieldChange = useCallback((fieldName: string) => {
    setSelectedFieldName(fieldName);
    const field = availableFields.find((f) => f.name === fieldName);
    if (field) {
      setFieldValue(getInitialValue(field.data_type));
    } else {
      setFieldValue('');
    }
  }, [availableFields]);

  // Reset state when modal closes
  const handleClose = () => {
    setSelectedFieldName('');
    setFieldValue('');
    onClose();
  };

  // Validate if value is complete based on field type
  const isValueComplete = useMemo(() => {
    if (!selectedField) return false;

    switch (selectedField.data_type) {
      case 'datetime_range': {
        const v = fieldValue as DateTimeValue;
        return v.date && v.startTime && v.endTime;
      }
      case 'location': {
        const v = fieldValue as LocationValue;
        if (v.mode === 'select') {
          return v.addressId !== undefined;
        } else {
          return (v.companyName?.trim() || '') && (v.address?.trim() || '');
        }
      }
      case 'dims': {
        const v = fieldValue as DimRow[];
        return v.length > 0 && v.every(row =>
          row.qty > 0 && row.length > 0 && row.width > 0 && row.height > 0 && row.weight > 0
        );
      }
      case 'string':
      default:
        return typeof fieldValue === 'string' && fieldValue.trim().length > 0;
    }
  }, [selectedField, fieldValue]);

  // Handle form submission
  const handleSubmit = () => {
    if (!selectedFieldName || !isValueComplete) return;

    // Transform value based on field type for backend
    let submittedValue: unknown = fieldValue;

    if (selectedField?.data_type === 'string' && typeof fieldValue === 'string') {
      submittedValue = fieldValue.trim();
    }
    // Other types are already in structured format

    onSubmit(selectedFieldName, submittedValue);
  };

  // Check if we can submit
  const canSubmit = selectedFieldName && isValueComplete && !isSubmitting;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-800 rounded-lg shadow-xl w-full max-w-md border border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white">Add Field Value</h3>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Field Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Field
            </label>
            <select
              value={selectedFieldName}
              onChange={(e) => handleFieldChange(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select a field...</option>
              {availableFields.map((field) => (
                <option key={field.name} value={field.name}>
                  {field.label}
                </option>
              ))}
            </select>
          </div>

          {/* Input Area - changes based on field type */}
          {selectedField && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Value
              </label>
              {renderInputForFieldType(
                selectedField,
                fieldValue,
                setFieldValue
              )}
            </div>
          )}

          {/* Placeholder when no field selected */}
          {!selectedField && (
            <div className="py-8 text-center text-gray-500 text-sm">
              Select a field above to enter a value
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-4 py-3 border-t border-gray-700">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-sm text-gray-300 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
          >
            {isSubmitting ? 'Adding...' : 'Add Value'}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Render the appropriate input component based on field type.
 */
function renderInputForFieldType(
  field: FieldOption,
  value: FieldValue,
  onChange: (value: FieldValue) => void
) {
  const inputClass = "w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500";
  const smallInputClass = "px-2 py-1.5 bg-gray-700 border border-gray-600 rounded text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 w-full";

  switch (field.data_type) {
    case 'datetime_range': {
      const v = value as DateTimeValue;
      return (
        <div className="space-y-3">
          {/* Date input */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">Date</label>
            <input
              type="date"
              value={v.date}
              onChange={(e) => onChange({ ...v, date: e.target.value })}
              className={inputClass}
            />
          </div>
          {/* Time inputs */}
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs text-gray-400 mb-1">Start Time</label>
              <input
                type="time"
                value={v.startTime}
                onChange={(e) => onChange({ ...v, startTime: e.target.value })}
                className={inputClass}
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs text-gray-400 mb-1">End Time</label>
              <input
                type="time"
                value={v.endTime}
                onChange={(e) => onChange({ ...v, endTime: e.target.value })}
                className={inputClass}
              />
            </div>
          </div>
        </div>
      );
    }

    case 'location': {
      const v = value as LocationValue;
      return (
        <div className="space-y-3">
          {/* Mode toggle */}
          <div className="flex rounded-lg overflow-hidden border border-gray-600">
            <button
              type="button"
              onClick={() => onChange({ ...v, mode: 'select' })}
              className={`flex-1 px-3 py-1.5 text-sm transition-colors ${
                v.mode === 'select'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Select Existing
            </button>
            <button
              type="button"
              onClick={() => onChange({ ...v, mode: 'create' })}
              className={`flex-1 px-3 py-1.5 text-sm transition-colors ${
                v.mode === 'create'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Create New
            </button>
          </div>

          {v.mode === 'select' ? (
            /* Searchable address picker */
            <AddressSearchPicker
              selectedAddressId={v.addressId}
              onSelect={(addressId) => onChange({ ...v, addressId })}
            />
          ) : (
            /* Create new address form */
            <div className="space-y-2">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Company Name</label>
                <input
                  type="text"
                  value={v.companyName ?? ''}
                  onChange={(e) => onChange({ ...v, companyName: e.target.value })}
                  placeholder="Enter company name..."
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Address</label>
                <input
                  type="text"
                  value={v.address ?? ''}
                  onChange={(e) => onChange({ ...v, address: e.target.value })}
                  placeholder="Enter full address..."
                  className={inputClass}
                />
              </div>
            </div>
          )}
        </div>
      );
    }

    case 'dims': {
      const rows = value as DimRow[];

      const updateRow = (index: number, updates: Partial<DimRow>) => {
        const newRows = [...rows];
        newRows[index] = { ...newRows[index], ...updates };
        onChange(newRows);
      };

      const addRow = () => {
        onChange([...rows, { qty: 1, length: 1, width: 1, height: 1, weight: 1 }]);
      };

      const removeRow = (index: number) => {
        if (rows.length > 1) {
          onChange(rows.filter((_, i) => i !== index));
        }
      };

      return (
        <div className="space-y-2">
          {/* Header */}
          <div className="grid grid-cols-[50px_1fr_1fr_1fr_1fr_28px] gap-1.5 text-xs text-gray-400">
            <span>Qty</span>
            <span>L</span>
            <span>W</span>
            <span>H</span>
            <span>Wt</span>
            <span></span>
          </div>

          {/* Rows */}
          {rows.map((row, index) => (
            <div key={index} className="grid grid-cols-[50px_1fr_1fr_1fr_1fr_28px] gap-1.5">
              <input
                type="number"
                min="1"
                value={row.qty || ''}
                onChange={(e) => updateRow(index, { qty: Number(e.target.value) || 0 })}
                placeholder="1"
                className={smallInputClass}
              />
              <input
                type="number"
                min="0"
                step="0.1"
                value={row.length || ''}
                onChange={(e) => updateRow(index, { length: Number(e.target.value) || 0 })}
                placeholder="0"
                className={smallInputClass}
              />
              <input
                type="number"
                min="0"
                step="0.1"
                value={row.width || ''}
                onChange={(e) => updateRow(index, { width: Number(e.target.value) || 0 })}
                placeholder="0"
                className={smallInputClass}
              />
              <input
                type="number"
                min="0"
                step="0.1"
                value={row.height || ''}
                onChange={(e) => updateRow(index, { height: Number(e.target.value) || 0 })}
                placeholder="0"
                className={smallInputClass}
              />
              <input
                type="number"
                min="0"
                step="0.1"
                value={row.weight || ''}
                onChange={(e) => updateRow(index, { weight: Number(e.target.value) || 0 })}
                placeholder="0"
                className={smallInputClass}
              />
              <button
                type="button"
                onClick={() => removeRow(index)}
                disabled={rows.length <= 1}
                className="p-1 text-gray-400 hover:text-red-400 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title="Remove row"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}

          {/* Add row button */}
          <button
            type="button"
            onClick={addRow}
            className="w-full py-1.5 text-sm text-blue-400 hover:text-blue-300 border border-dashed border-gray-600 hover:border-blue-500 rounded transition-colors"
          >
            + Add Row
          </button>
        </div>
      );
    }

    case 'string':
    default:
      // Simple text input for string fields
      return (
        <input
          type="text"
          value={value as string}
          onChange={(e) => onChange(e.target.value)}
          placeholder={`Enter ${field.label.toLowerCase()}...`}
          className={inputClass}
        />
      );
  }
}

export default AddFieldModal;
