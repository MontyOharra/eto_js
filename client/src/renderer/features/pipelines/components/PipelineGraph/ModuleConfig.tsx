/**
 * ModuleConfig Component
 * Collapsible configuration section for module settings
 */

import { useState } from "react";
import { ModuleTemplate } from "../../../modules/types"
import { ModuleInstance } from "../../types";
import { ConfigSection } from "./ConfigSection";

export interface ModuleConfigProps {
  moduleInstance: ModuleInstance;
  template: ModuleTemplate;
  onConfigChange?: (moduleId: string, configKey: string, value: any) => void;
}

export function ModuleConfig({
  moduleInstance,
  template,
  onConfigChange,
}: ModuleConfigProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const handleConfigChange = (configKey: string, value: any) => {
    if (onConfigChange) {
      onConfigChange(moduleInstance.module_instance_id, configKey, value);
    }
  };

  // Don't show config section if there are no config properties
  // Check if config_schema exists and has actual properties
  const hasConfigProperties =
    template.config_schema &&
    typeof template.config_schema === "object" &&
    // Either it's a JSON Schema with properties field that has keys
    ((template.config_schema.properties &&
      typeof template.config_schema.properties === "object" &&
      Object.keys(template.config_schema.properties).length > 0) ||
      // Or it's a flat object with keys (not JSON Schema format)
      (!template.config_schema.properties &&
        Object.keys(template.config_schema).length > 0 &&
        !template.config_schema.type)); // Exclude JSON Schema metadata fields

  if (!hasConfigProperties) {
    return null;
  }

  return (
    <div className="border-t border-gray-600">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-700 transition-colors"
      >
        <span className="text-[10px] text-gray-400 uppercase font-semibold">
          Configuration
        </span>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isExpanded && (
        <ConfigSection
          schema={template.config_schema}
          config={moduleInstance.config}
          onConfigChange={handleConfigChange}
        />
      )}
    </div>
  );
}
