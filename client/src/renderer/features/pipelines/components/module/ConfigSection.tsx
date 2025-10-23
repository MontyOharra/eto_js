import React from 'react';

interface JSONSchemaProperty {
  type: string;
  title?: string;
  description?: string;
  default?: any;
  enum?: string[];
}

interface JSONSchema {
  type: string;
  title?: string;
  description?: string;
  properties?: Record<string, JSONSchemaProperty>;
}

interface ConfigSectionProps {
  schema: JSONSchema;
  config: Record<string, any>;
  onConfigChange: (key: string, value: any) => void;
}

export const ConfigSection: React.FC<ConfigSectionProps> = ({ schema, config, onConfigChange }) => {
  if (!schema.properties || Object.keys(schema.properties).length === 0) {
    return null; // No config needed
  }

  const renderField = (key: string, property: JSONSchemaProperty) => {
    const value = config[key] ?? property.default;
    const label = property.title || key;
    const description = property.description;

    const handleChange = (newValue: any) => {
      onConfigChange(key, newValue);
    };

    // Boolean checkbox
    if (property.type === 'boolean') {
      return (
        <div key={key} className="mb-2.5">
          <label className="flex items-center gap-2.5 cursor-pointer group">
            <div className="relative flex items-center">
              <input
                type="checkbox"
                checked={value ?? false}
                onChange={(e) => handleChange(e.target.checked)}
                className="peer w-4 h-4 rounded border border-gray-600 bg-gray-700 appearance-none cursor-pointer checked:bg-blue-500 checked:border-blue-500 hover:border-gray-500 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800"
              />
              <svg
                className="absolute w-3 h-3 left-0.5 pointer-events-none hidden peer-checked:block text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <span className="text-xs text-gray-200 group-hover:text-gray-100 transition-colors">{label}</span>
          </label>
          {description && (
            <p className="text-[10px] text-gray-400 mt-0.5 ml-6.5">{description}</p>
          )}
        </div>
      );
    }

    // Number input
    if (property.type === 'number' || property.type === 'integer') {
      return (
        <div key={key} className="mb-2.5">
          <label className="block text-xs text-gray-200 mb-1">{label}</label>
          <input
            type="number"
            value={value ?? ''}
            onChange={(e) => {
              const parsed = property.type === 'integer'
                ? parseInt(e.target.value, 10)
                : parseFloat(e.target.value);
              handleChange(isNaN(parsed) ? property.default : parsed);
            }}
            step={property.type === 'integer' ? '1' : 'any'}
            className="nodrag w-full px-2 py-1 text-xs bg-gray-700 border border-gray-600 rounded text-gray-200 focus:outline-none focus:border-blue-500"
          />
          {description && (
            <p className="text-[10px] text-gray-400 mt-0.5">{description}</p>
          )}
        </div>
      );
    }

    // Enum select
    if (property.enum && property.enum.length > 0) {
      return (
        <div key={key} className="mb-2.5">
          <label className="block text-xs text-gray-200 mb-1">{label}</label>
          <select
            value={value ?? ''}
            onChange={(e) => handleChange(e.target.value)}
            className="nodrag w-full px-2 py-1 text-xs bg-gray-700 border border-gray-600 rounded text-gray-200 focus:outline-none focus:border-blue-500"
          >
            {property.enum.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          {description && (
            <p className="text-[10px] text-gray-400 mt-0.5">{description}</p>
          )}
        </div>
      );
    }

    // String input (default)
    return (
      <div key={key} className="mb-2.5">
        <label className="block text-xs text-gray-200 mb-1">{label}</label>
        <input
          type="text"
          value={value ?? ''}
          onChange={(e) => handleChange(e.target.value)}
          className="w-full px-2 py-1 text-xs bg-gray-700 border border-gray-600 rounded text-gray-200 focus:outline-none focus:border-blue-500"
        />
        {description && (
          <p className="text-[10px] text-gray-400 mt-0.5">{description}</p>
        )}
      </div>
    );
  };

  return (
    <div className="px-3 pt-2 pb-3">
      {Object.entries(schema.properties).map(([key, property]) =>
        renderField(key, property)
      )}
    </div>
  );
};
