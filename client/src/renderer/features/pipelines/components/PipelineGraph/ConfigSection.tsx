/**
 * ConfigSection Component
 * Renders individual config fields based on JSON Schema
 */

import React, { useState, useEffect, useRef } from "react";

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
  onConfigChange?: (key: string, value: any) => void;
}

// String field component with local state for responsive typing
const StringField: React.FC<{
  configKey: string;
  value: string;
  label: string;
  description?: string;
  onConfigChange: (key: string, value: any) => void;
  isViewMode?: boolean;
}> = ({ configKey, value, label, description, onConfigChange, isViewMode = false }) => {
  const [localValue, setLocalValue] = useState(value ?? "");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Sync when external value changes
  useEffect(() => {
    setLocalValue(value ?? "");
  }, [value]);

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [localValue]);

  return (
    <div className="mb-2.5">
      <label className="block text-xs text-gray-200 mb-1">{label}</label>
      <textarea
        ref={textareaRef}
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        onMouseDown={(e) => {
          // Prevent ReactFlow from starting pan on mousedown
          e.stopPropagation();
        }}
        onBlur={() => onConfigChange?.(configKey, localValue)}
        disabled={isViewMode}
        rows={1}
        className={`nodrag w-full min-w-0 px-2 py-1 text-xs bg-gray-700 border border-gray-600 rounded text-gray-200 focus:outline-none focus:border-blue-500 resize-none overflow-hidden ${isViewMode ? 'opacity-60 cursor-default' : ''}`}
      />
      {description && (
        <p className="text-[10px] text-gray-400 mt-0.5">{description}</p>
      )}
    </div>
  );
};

// Number field component with local state
const NumberField: React.FC<{
  configKey: string;
  value: number;
  label: string;
  description?: string;
  propertyType: "number" | "integer";
  defaultValue: any;
  onConfigChange: (key: string, value: any) => void;
  isViewMode?: boolean;
}> = ({ configKey, value, label, description, propertyType, defaultValue, onConfigChange, isViewMode = false }) => {
  const [localValue, setLocalValue] = useState(value ?? "");

  // Sync when external value changes
  useEffect(() => {
    setLocalValue(value ?? "");
  }, [value]);

  return (
    <div className="mb-2.5">
      <label className="block text-xs text-gray-200 mb-1">{label}</label>
      <input
        type="number"
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        onMouseDown={(e) => {
          // Prevent ReactFlow from starting pan on mousedown
          e.stopPropagation();
        }}
        onBlur={() => {
          const parsed = propertyType === "integer"
            ? parseInt(String(localValue), 10)
            : parseFloat(String(localValue));
          onConfigChange?.(configKey, isNaN(parsed) ? defaultValue : parsed);
        }}
        step={propertyType === "integer" ? "1" : "any"}
        disabled={isViewMode}
        className={`nodrag w-full min-w-0 px-2 py-1 text-xs bg-gray-700 border border-gray-600 rounded text-gray-200 focus:outline-none focus:border-blue-500 ${isViewMode ? 'opacity-60 cursor-default' : ''}`}
      />
      {description && (
        <p className="text-[10px] text-gray-400 mt-0.5">{description}</p>
      )}
    </div>
  );
};

export const ConfigSection: React.FC<ConfigSectionProps> = ({
  schema,
  config,
  onConfigChange,
}) => {
  if (!schema.properties || Object.keys(schema.properties).length === 0) {
    return null; // No config needed
  }

  // Check if in view mode (no change callback)
  const isViewMode = !onConfigChange;

  const renderField = (key: string, property: JSONSchemaProperty) => {
    const value = config[key] ?? property.default;
    const label = property.title || key;
    const description = property.description;

    const handleChange = (newValue: any) => {
      onConfigChange?.(key, newValue);
    };

    // Boolean checkbox
    if (property.type === "boolean") {
      return (
        <div key={key} className="mb-2.5">
          <label className={`flex items-center gap-2.5 ${isViewMode ? 'cursor-default' : 'cursor-pointer'} group`}>
            <div className="relative flex items-center">
              <input
                type="checkbox"
                checked={value ?? false}
                onChange={(e) => handleChange(e.target.checked)}
                onMouseDown={(e) => {
                  // Prevent ReactFlow from starting pan on mousedown
                  e.stopPropagation();
                }}
                disabled={isViewMode}
                className={`nodrag peer w-4 h-4 rounded border border-gray-600 bg-gray-700 appearance-none ${isViewMode ? 'cursor-default opacity-60' : 'cursor-pointer'} checked:bg-blue-500 checked:border-blue-500 hover:border-gray-500 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800 disabled:hover:border-gray-600`}
              />
              <svg
                className="absolute w-3 h-3 left-0.5 pointer-events-none hidden peer-checked:block text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={3}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <span className="text-xs text-gray-200 group-hover:text-gray-100 transition-colors">
              {label}
            </span>
          </label>
          {description && (
            <p className="text-[10px] text-gray-400 mt-0.5 ml-6.5">
              {description}
            </p>
          )}
        </div>
      );
    }

    // Number input
    if (property.type === "number" || property.type === "integer") {
      return (
        <NumberField
          key={key}
          configKey={key}
          value={value}
          label={label}
          description={description}
          propertyType={property.type}
          defaultValue={property.default}
          onConfigChange={onConfigChange}
          isViewMode={isViewMode}
        />
      );
    }

    // Enum select
    if (property.enum && property.enum.length > 0) {
      return (
        <div key={key} className="mb-2.5">
          <label className="block text-xs text-gray-200 mb-1">{label}</label>
          <select
            value={value ?? ""}
            onChange={(e) => handleChange(e.target.value)}
            onMouseDown={(e) => {
              // Prevent ReactFlow from starting pan on mousedown
              e.stopPropagation();
            }}
            disabled={isViewMode}
            className={`nodrag w-full min-w-0 px-2 py-1 text-xs bg-gray-700 border border-gray-600 rounded text-gray-200 focus:outline-none focus:border-blue-500 ${isViewMode ? 'opacity-60 cursor-default' : ''}`}
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
    return <StringField key={key} configKey={key} value={value} label={label} description={description} onConfigChange={onConfigChange} isViewMode={isViewMode} />;
  };

  return (
    <div className="px-3 pt-2 pb-3">
      {Object.entries(schema.properties).map(([key, property]) =>
        renderField(key, property)
      )}
    </div>
  );
};
