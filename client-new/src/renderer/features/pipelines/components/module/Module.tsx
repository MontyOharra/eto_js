/**
 * Module Component
 * Main module node component composed of ModuleHeader, ModuleNodes, and ModuleConfig
 */

import { useState, useEffect } from 'react';
import { ModuleTemplate, ModuleInstance, NodePin } from '../../../../types/moduleTypes';
import { ModuleHeader } from './ModuleHeader';
import { ModuleNodes } from './ModuleNodes';
import { ModuleConfig } from './ModuleConfig';

export interface ModuleProps {
  data: {
    moduleInstance: ModuleInstance;
    template: ModuleTemplate;
    onDeleteModule?: (moduleId: string) => void;
    onUpdateNode?: (moduleId: string, nodeId: string, updates: Partial<NodePin>) => void;
    onAddNode?: (moduleId: string, direction: 'input' | 'output', groupIndex: number) => void;
    onRemoveNode?: (moduleId: string, nodeId: string) => void;
    onConfigChange?: (moduleId: string, configKey: string, value: any) => void;
    onTextFocus?: () => void;
    onTextBlur?: () => void;
    onHandleClick?: (nodeId: string, handleId: string, handleType: 'source' | 'target') => void;
    pendingConnection?: {
      sourceHandleId: string;
      sourceNodeId: string;
      handleType: 'source' | 'target';
    } | null;
    getEffectiveAllowedTypes?: (moduleId: string, pinId: string, baseAllowedTypes: string[]) => string[];
    getConnectedOutputName?: (moduleId: string, inputPinId: string) => string | undefined;
    failedModuleIds?: string[];  // For execution visualization - highlight failed modules
    executionMode?: boolean;  // When true, hides all editing controls (add/remove/delete buttons)
    executionValues?: Map<string, { value: any; type: string; name: string }>;  // Execution data for each pin
    onModuleMouseEnter?: (moduleId: string) => void;  // For highlighting connected edges
    onModuleMouseLeave?: () => void;  // For removing edge highlights
  };
}

export function Module({ data }: ModuleProps) {
  const {
    moduleInstance,
    template,
    onDeleteModule,
    onUpdateNode,
    onAddNode,
    onRemoveNode,
    onConfigChange,
    onTextFocus,
    onTextBlur,
    onHandleClick,
    pendingConnection,
    getEffectiveAllowedTypes,
    getConnectedOutputName,
    failedModuleIds = [],
    executionMode = false,
    executionValues,
    onModuleMouseEnter,
    onModuleMouseLeave,
  } = data;

  const [highlightedTypeVar, setHighlightedTypeVar] = useState<string | null>(null);

  // Check if this module has failed
  const hasFailed = failedModuleIds.includes(moduleInstance.module_instance_id);

  // Auto-correct types when effective allowed types change and current type becomes invalid
  useEffect(() => {
    if (!getEffectiveAllowedTypes || !onUpdateNode) return;

    const allPins = [...moduleInstance.inputs, ...moduleInstance.outputs];

    allPins.forEach((pin) => {
      const effectiveTypes = getEffectiveAllowedTypes(moduleInstance.module_instance_id, pin.node_id, pin.allowed_types || []);

      // If current type is not in effective types, update to first valid type
      if (effectiveTypes.length > 0 && !effectiveTypes.includes(pin.type)) {
        onUpdateNode(moduleInstance.module_instance_id, pin.node_id, { type: effectiveTypes[0] });
      }
    });
  }, [moduleInstance, getEffectiveAllowedTypes, onUpdateNode]);

  return (
    <div
      className={`bg-gray-800 rounded-lg border-2 ${hasFailed ? 'border-red-600' : 'border-gray-600'} min-w-[400px] w-min nodrag nopan`}
      onMouseEnter={() => onModuleMouseEnter?.(moduleInstance.module_instance_id)}
      onMouseLeave={() => onModuleMouseLeave?.()}
      style={{ pointerEvents: 'auto' }}
    >
      <ModuleHeader
        moduleInstance={moduleInstance}
        template={template}
        onDeleteModule={onDeleteModule}
        executionMode={executionMode}
        onModuleMouseEnter={onModuleMouseEnter}
        onModuleMouseLeave={onModuleMouseLeave}
      />

      <ModuleNodes
        moduleInstance={moduleInstance}
        template={template}
        onUpdateNode={onUpdateNode}
        onAddNode={onAddNode}
        onRemoveNode={onRemoveNode}
        onTextFocus={onTextFocus}
        onTextBlur={onTextBlur}
        onHandleClick={onHandleClick}
        pendingConnection={pendingConnection}
        getEffectiveAllowedTypes={getEffectiveAllowedTypes}
        getConnectedOutputName={getConnectedOutputName}
        highlightedTypeVar={highlightedTypeVar}
        onTypeVarFocus={setHighlightedTypeVar}
        executionMode={executionMode}
        executionValues={executionValues}
        onModuleMouseEnter={onModuleMouseEnter}
        onModuleMouseLeave={onModuleMouseLeave}
      />

      <ModuleConfig
        moduleInstance={moduleInstance}
        template={template}
        onConfigChange={onConfigChange}
        executionMode={executionMode}
      />
    </div>
  );
}
