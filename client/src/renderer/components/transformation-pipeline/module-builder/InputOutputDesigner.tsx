import React, { useState } from 'react';

interface InputField {
  id: string;
  name: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object';
  description: string;
  required: boolean;
  defaultValue?: any;
}

interface OutputField {
  id: string;
  name: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object';
  description: string;
}

interface InputOutputDesignerProps {
  type: 'input' | 'output';
  fields: InputField[] | OutputField[];
  onChange: (fields: InputField[] | OutputField[]) => void;
}

export const InputOutputDesigner: React.FC<InputOutputDesignerProps> = ({
  type,
  fields,
  onChange
}) => {
  const [editingField, setEditingField] = useState<InputField | OutputField | null>(null);
  const [isAddingField, setIsAddingField] = useState(false);

  const fieldTypes = [
    { value: 'string', label: 'String', color: 'bg-blue-500' },
    { value: 'number', label: 'Number', color: 'bg-green-500' },
    { value: 'boolean', label: 'Boolean', color: 'bg-yellow-500' },
    { value: 'array', label: 'Array', color: 'bg-purple-500' },
    { value: 'object', label: 'Object', color: 'bg-red-500' }
  ];

  const createNewField = (): InputField | OutputField => {
    const baseField = {
      id: `field_${Date.now()}`,
      name: '',
      type: 'string' as const,
      description: ''
    };

    if (type === 'input') {
      return {
        ...baseField,
        required: false,
        defaultValue: undefined
      } as InputField;
    } else {
      return baseField as OutputField;
    }
  };

  const handleAddField = () => {
    const newField = createNewField();
    setEditingField(newField);
    setIsAddingField(true);
  };

  const handleEditField = (field: InputField | OutputField) => {
    setEditingField({ ...field });
    setIsAddingField(false);
  };

  const handleSaveField = () => {
    if (!editingField) return;

    const updatedFields = isAddingField 
      ? [...fields, editingField]
      : fields.map(f => f.id === editingField.id ? editingField : f);

    onChange(updatedFields);
    setEditingField(null);
    setIsAddingField(false);
  };

  const handleCancelEdit = () => {
    setEditingField(null);
    setIsAddingField(false);
  };

  const handleDeleteField = (fieldId: string) => {
    const updatedFields = fields.filter(f => f.id !== fieldId);
    onChange(updatedFields);
  };

  const handleFieldChange = (key: string, value: any) => {
    if (!editingField) return;
    setEditingField({ ...editingField, [key]: value });
  };

  const getTypeColor = (fieldType: string) => {
    return fieldTypes.find(t => t.value === fieldType)?.color || 'bg-gray-500';
  };

  const getTypeLabel = (fieldType: string) => {
    return fieldTypes.find(t => t.value === fieldType)?.label || fieldType;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium text-white mb-2">
            {type === 'input' ? 'Input Fields' : 'Output Fields'}
          </h3>
          <p className="text-gray-400 text-sm">
            Define the {type === 'input' ? 'input parameters' : 'output values'} for your custom module
          </p>
        </div>
        <button
          onClick={handleAddField}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add {type === 'input' ? 'Input' : 'Output'}
        </button>
      </div>

      {/* Fields List */}
      <div className="space-y-3">
        {fields.map((field) => (
          <div key={field.id} className="bg-gray-800 rounded-lg p-4 border border-gray-600">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-3">
                <div className={`w-3 h-3 rounded-full ${getTypeColor(field.type)}`}></div>
                <div>
                  <h4 className="text-white font-medium">{field.name || 'Unnamed Field'}</h4>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className="text-xs text-gray-400">{getTypeLabel(field.type)}</span>
                    {type === 'input' && (field as InputField).required && (
                      <span className="text-xs bg-red-900 text-red-300 px-2 py-0.5 rounded">
                        Required
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleEditField(field)}
                  className="text-gray-400 hover:text-white p-1 rounded transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button
                  onClick={() => handleDeleteField(field.id)}
                  className="text-gray-400 hover:text-red-400 p-1 rounded transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
            {field.description && (
              <p className="text-gray-400 text-sm">{field.description}</p>
            )}
          </div>
        ))}

        {fields.length === 0 && (
          <div className="text-center py-12 border-2 border-dashed border-gray-600 rounded-lg">
            <svg className="w-12 h-12 text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            <p className="text-gray-400 text-lg mb-2">No {type === 'input' ? 'inputs' : 'outputs'} defined</p>
            <p className="text-gray-500 text-sm mb-4">
              Add {type === 'input' ? 'input fields' : 'output fields'} to define your module's interface
            </p>
            <button
              onClick={handleAddField}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
            >
              Add First {type === 'input' ? 'Input' : 'Output'}
            </button>
          </div>
        )}
      </div>

      {/* Edit Modal */}
      {editingField && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg shadow-xl w-full max-w-md">
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-700">
              <h3 className="text-lg font-medium text-white">
                {isAddingField ? 'Add' : 'Edit'} {type === 'input' ? 'Input' : 'Output'} Field
              </h3>
            </div>

            {/* Content */}
            <div className="px-6 py-4 space-y-4">
              {/* Field Name */}
              <div>
                <label className="block text-sm font-medium text-white mb-2">Field Name</label>
                <input
                  type="text"
                  value={editingField.name}
                  onChange={(e) => handleFieldChange('name', e.target.value)}
                  className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400"
                  placeholder="Enter field name"
                />
              </div>

              {/* Field Type */}
              <div>
                <label className="block text-sm font-medium text-white mb-2">Data Type</label>
                <select
                  value={editingField.type}
                  onChange={(e) => handleFieldChange('type', e.target.value)}
                  className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white"
                >
                  {fieldTypes.map(type => (
                    <option key={type.value} value={type.value}>{type.label}</option>
                  ))}
                </select>
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-white mb-2">Description</label>
                <textarea
                  value={editingField.description}
                  onChange={(e) => handleFieldChange('description', e.target.value)}
                  className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400"
                  rows={3}
                  placeholder="Describe this field"
                />
              </div>

              {/* Input-specific fields */}
              {type === 'input' && (
                <>
                  {/* Required checkbox */}
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="required"
                      checked={(editingField as InputField).required}
                      onChange={(e) => handleFieldChange('required', e.target.checked)}
                      className="mr-2"
                    />
                    <label htmlFor="required" className="text-sm text-white">
                      Required field
                    </label>
                  </div>

                  {/* Default Value */}
                  <div>
                    <label className="block text-sm font-medium text-white mb-2">Default Value</label>
                    <input
                      type="text"
                      value={(editingField as InputField).defaultValue || ''}
                      onChange={(e) => handleFieldChange('defaultValue', e.target.value)}
                      className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400"
                      placeholder="Optional default value"
                    />
                  </div>
                </>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-700 flex justify-end space-x-3">
              <button
                onClick={handleCancelEdit}
                className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveField}
                disabled={!editingField.name.trim()}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isAddingField ? 'Add Field' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};