import React, { useState } from 'react';
import { InputDefiner, OutputDefiner, IODataType } from '../../../types/inputOutputDefiners';

interface InputOutputDefinerComponentProps {
  definer: InputDefiner | OutputDefiner;
  isSelected: boolean;
  onSelect: () => void;
  onUpdate: (definer: InputDefiner | OutputDefiner) => void;
  onDelete: () => void;
}

const DATA_TYPES: { value: IODataType; label: string; color: string }[] = [
  { value: 'string', label: 'String', color: '#3B82F6' },
  { value: 'number', label: 'Number', color: '#10B981' },
  { value: 'boolean', label: 'Boolean', color: '#F59E0B' },
  { value: 'datetime', label: 'DateTime', color: '#8B5CF6' },
  { value: 'variable', label: 'Variable', color: '#6B7280' }
];

export const InputOutputDefinerComponent: React.FC<InputOutputDefinerComponentProps> = ({
  definer,
  isSelected,
  onSelect,
  onUpdate,
  onDelete
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    name: definer.name,
    description: definer.description,
    type: definer.type,
    required: 'required' in definer ? definer.required : false,
    defaultValue: 'defaultValue' in definer ? definer.defaultValue : undefined
  });

  const isInputDefiner = 'required' in definer;
  const typeInfo = DATA_TYPES.find(t => t.value === definer.type) || DATA_TYPES[0];

  const handleSave = () => {
    const updatedDefiner = {
      ...definer,
      name: editForm.name,
      description: editForm.description,
      type: editForm.type,
      ...(isInputDefiner && {
        required: editForm.required,
        defaultValue: editForm.defaultValue
      })
    };
    onUpdate(updatedDefiner);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditForm({
      name: definer.name,
      description: definer.description,
      type: definer.type,
      required: 'required' in definer ? definer.required : false,
      defaultValue: 'defaultValue' in definer ? definer.defaultValue : undefined
    });
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <div 
        className={`absolute bg-gray-800 border-2 border-blue-500 rounded-lg p-4 min-w-[280px] shadow-xl z-10`}
        style={{ left: definer.position.x, top: definer.position.y }}
      >
        <div className="space-y-3">
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-white font-medium">
              Edit {isInputDefiner ? 'Input' : 'Output'} Definer
            </h4>
            <div className="flex items-center space-x-1">
              <button
                onClick={handleSave}
                className="bg-green-600 hover:bg-green-700 text-white p-1 rounded transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </button>
              <button
                onClick={handleCancel}
                className="bg-gray-600 hover:bg-gray-700 text-white p-1 rounded transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Name */}
          <input
            type="text"
            value={editForm.name}
            onChange={(e) => setEditForm(prev => ({ ...prev, name: e.target.value }))}
            className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white text-sm"
            placeholder="Field name"
          />

          {/* Description */}
          <textarea
            value={editForm.description}
            onChange={(e) => setEditForm(prev => ({ ...prev, description: e.target.value }))}
            className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white text-sm"
            rows={2}
            placeholder="Description"
          />

          {/* Type */}
          <select
            value={editForm.type}
            onChange={(e) => setEditForm(prev => ({ ...prev, type: e.target.value as IODataType }))}
            className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white text-sm"
          >
            {DATA_TYPES.map(type => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>

          {/* Input-specific fields */}
          {isInputDefiner && (
            <>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="required"
                  checked={editForm.required}
                  onChange={(e) => setEditForm(prev => ({ ...prev, required: e.target.checked }))}
                  className="rounded"
                />
                <label htmlFor="required" className="text-white text-sm">Required</label>
              </div>

              <input
                type="text"
                value={editForm.defaultValue as string || ''}
                onChange={(e) => setEditForm(prev => ({ ...prev, defaultValue: e.target.value }))}
                className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                placeholder="Default value (optional)"
              />
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className={`absolute cursor-pointer transition-all ${
        isSelected 
          ? 'ring-2 ring-blue-500 transform scale-105' 
          : 'hover:ring-2 hover:ring-gray-500'
      }`}
      style={{ left: definer.position.x, top: definer.position.y }}
      onClick={onSelect}
    >
      <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 min-w-[200px] shadow-lg">
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <div 
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: typeInfo.color }}
            />
            <span className="text-white font-medium text-sm">
              {definer.name || `${isInputDefiner ? 'Input' : 'Output'} Definer`}
            </span>
          </div>
          <div className="flex items-center space-x-1">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsEditing(true);
              }}
              className="text-gray-400 hover:text-white p-1 rounded transition-colors"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="text-gray-400 hover:text-red-400 p-1 rounded transition-colors"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>

        {/* Type badge */}
        <div className="flex items-center justify-between mb-2">
          <span 
            className="text-xs px-2 py-1 rounded text-white"
            style={{ backgroundColor: typeInfo.color }}
          >
            {typeInfo.label}
          </span>
          <span className="text-xs text-gray-400">
            {isInputDefiner ? 'INPUT' : 'OUTPUT'}
          </span>
        </div>

        {/* Description */}
        {definer.description && (
          <p className="text-gray-400 text-xs mb-2 line-clamp-2">
            {definer.description}
          </p>
        )}

        {/* Input-specific info */}
        {isInputDefiner && (definer as InputDefiner).required && (
          <div className="flex items-center space-x-1 mb-1">
            <span className="text-xs bg-red-900 text-red-300 px-1 py-0.5 rounded">
              Required
            </span>
          </div>
        )}

        {/* Connection port */}
        <div className="flex justify-center mt-2">
          <div 
            className={`w-4 h-4 rounded-full border-2 border-white ${
              isInputDefiner ? 'bg-blue-500' : 'bg-green-500'
            }`}
          />
        </div>
      </div>
    </div>
  );
};