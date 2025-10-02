import React, { useState } from 'react';
import { ModuleInstance, ModuleTemplate, NodePin } from '../../../types/moduleTypes';
import { NodeConnection } from '../../../types/pipelineTypes';
import { canAddNode, canRemoveNode, hasVariableTypes, getAllowedTypes } from '../../../utils/moduleFactory';
import { NodeSectionSide } from './module-components';
import { calculateTypePropagation, getNodeTypeConstraints, getNodeTypeInfo } from '../../../utils/typeConstraints';

interface ModuleComponentProps {
  module: ModuleInstance;
  template: ModuleTemplate;
  position: { x: number; y: number };
  isSelected: boolean;
  // Type constraint system data
  allModules: ModuleInstance[];
  allTemplates: ModuleTemplate[];
  connections: NodeConnection[];
  getConnectedOutputName?: (inputNodeId: string) => string;
  onSelect: (moduleId: string) => void;
  onMouseDown?: (e: React.MouseEvent) => void;
  onDelete?: (moduleId: string) => void;
  onAddNode?: (moduleId: string, nodeType: 'input' | 'output', groupId?: string) => void;
  onRemoveNode?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => void;
  onNodeTypeChange?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newType: string) => void;
  onNodeNameChange?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newName: string) => void;
  onNodeClick?: (moduleId: string, nodeId: string, nodeType: 'input' | 'output') => void;
  onConfigChange?: (moduleId: string, config: Record<string, any>) => void;
  // New callback for coordinated type changes
  onCoordinatedTypeChange?: (updates: Array<{ moduleId: string; nodeId: string; newType: string }>) => void;
}

// Get color for node type (Python type names)
const getTypeColor = (type: string): string => {
  switch (type) {
    case 'str': return '#3B82F6'; // Blue
    case 'int': return '#EF4444'; // Red
    case 'float': return '#F59E0B'; // Orange (different from int)
    case 'bool': return '#10B981'; // Green
    case 'datetime': return '#8B5CF6'; // Purple

    default: return '#6B7280'; // Gray
  }
};

export const ModuleComponent: React.FC<ModuleComponentProps> = ({
  module,
  template,
  position,
  isSelected,
  allModules,
  allTemplates,
  connections,
  getConnectedOutputName,
  onSelect,
  onMouseDown,
  onDelete,
  onAddNode,
  onRemoveNode,
  onNodeTypeChange,
  onNodeNameChange,
  onNodeClick,
  onConfigChange,
  onCoordinatedTypeChange
}) => {
  const [editingNodeName, setEditingNodeName] = useState<string | null>(null);
  const [isConfigExpanded, setIsConfigExpanded] = useState(false);
  const [activeTypeVar, setActiveTypeVar] = useState<string | null>(null);

  // TypeVar highlighting handlers
  const handleTypeVarFocus = (typeVar: string | undefined) => {
    if (typeVar) {
      setActiveTypeVar(typeVar);
    }
  };

  const handleTypeVarBlur = () => {
    setActiveTypeVar(null);
  };

  // Click-outside handler to clear TypeVar highlighting
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      // Only clear if there's an active TypeVar and the click is outside any select element
      if (activeTypeVar && event.target) {
        const target = event.target as Element;
        // Check if the click was on a select element or its children
        const isSelectClick = target.closest('select') !== null;
        if (!isSelectClick) {
          setActiveTypeVar(null);
        }
      }
    };

    if (activeTypeVar) {
      document.addEventListener('click', handleClickOutside);
    }

    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  }, [activeTypeVar]);

  // Enhanced type change handler with constraint propagation
  const handleCoordinatedNodeTypeChange = (nodeId: string, newType: string) => {
    // Calculate all the type changes that need to happen
    const propagation = calculateTypePropagation(
      nodeId,
      newType,
      allModules,
      allTemplates,
      connections
    );

    // Add the original node change
    const allUpdates = [
      { moduleId: module.module_instance_id, nodeId, newType },
      ...propagation.nodesToUpdate
    ];

    // Use the coordinated type change callback if available
    if (onCoordinatedTypeChange) {
      onCoordinatedTypeChange(allUpdates);
    } else {
      // Fallback to individual changes
      // Helper to get all nodes from NodeGroup structure
      const allInputs = [...(module.inputs?.static || []), ...(module.inputs?.dynamic || [])];
      const allOutputs = [...(module.outputs?.static || []), ...(module.outputs?.dynamic || [])];
      const nodeIndex = [...allInputs, ...allOutputs].findIndex(n => n.node_id === nodeId);
      const nodeType = allInputs.find(n => n.node_id === nodeId) ? 'input' : 'output';
      if (nodeIndex !== -1) {
        onNodeTypeChange?.(module.module_instance_id, nodeType, nodeIndex, newType);
      }
    }
  };

  // Function to get type constraints for a node (considering connections)
  const getRestrictedTypesForNode = (nodeId: string): { allowedTypes: string[]; disabledTypes: string[]; allTypes: string[] } => {
    return getNodeTypeConstraints(nodeId, allModules, allTemplates, connections);
  };

  // Auto-resize textareas on mount and when content changes
  React.useEffect(() => {
    const textareas = document.querySelectorAll(`[data-module-id="${module.module_instance_id}"] textarea`);
    textareas.forEach((textarea) => {
      const target = textarea as HTMLTextAreaElement;
      target.style.height = 'auto';
      target.style.height = target.scrollHeight + 'px';
    });
  }, [module.outputs, module.inputs, getConnectedOutputName]);

  // Helper function to determine if a color is light or dark
  const isLightColor = (hexColor: string): boolean => {
    const color = hexColor.replace('#', '');
    const r = parseInt(color.substring(0, 2), 16);
    const g = parseInt(color.substring(2, 4), 16);
    const b = parseInt(color.substring(4, 6), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.5;
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    if (onMouseDown) {
      onMouseDown(e);
    }
    onSelect(module.module_instance_id);
  };

  const handleConfigChange = (key: string, value: any) => {
    if (onConfigChange) {
      const newConfig = { ...module.config, [key]: value };
      onConfigChange(module.module_instance_id, newConfig);
    }
  };

  const textColor = isLightColor(template.color) ? '#000000' : '#FFFFFF';
  const borderColor = isSelected ? '#60A5FA' : '#4B5563';

  // Check if we can add/remove nodes (now using NodeGroup structure)
  const canAddInputs = canAddNode(module.inputs, template.meta.io_shape.inputs);
  const canRemoveInputs = canRemoveNode(module.inputs, template.meta.io_shape.inputs);
  const canAddOutputs = canAddNode(module.outputs, template.meta.io_shape.outputs);
  const canRemoveOutputs = canRemoveNode(module.outputs, template.meta.io_shape.outputs);

  // Calculate total rows including add button rows (using NodeGroup structure)
  const inputNodeCount = (module.inputs?.static || []).length + (module.inputs?.dynamic || []).length;
  const outputNodeCount = (module.outputs?.static || []).length + (module.outputs?.dynamic || []).length;
  const inputRowCount = inputNodeCount + (canAddInputs ? 1 : 0);
  const outputRowCount = outputNodeCount + (canAddOutputs ? 1 : 0);
  const totalRows = Math.max(inputRowCount, outputRowCount, 1);

  // Get visible config properties from schema
  const configProperties = template.config_schema?.properties || {};
  const visibleConfigKeys = Object.keys(configProperties).filter(key =>
    !configProperties[key].hidden
  );
  const hasConfig = visibleConfigKeys.length > 0;

  return (
    <div
      className="absolute bg-gray-800 rounded-lg shadow-lg border-2 select-none"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        width: '400px', // Fixed width (increased for side-by-side layout)
        transform: 'translate(-50%, 0)',
        borderColor,
        userSelect: 'none',
        WebkitUserSelect: 'none',
        MozUserSelect: 'none',
        msUserSelect: 'none',
        pointerEvents: 'auto',
        cursor: 'move'
      }}
      data-module-id={module.module_instance_id}
      onMouseDown={handleMouseDown}
    >
      {/* Header */}
      <div
        className="px-3 py-2 flex items-center justify-between rounded-t-lg"
        style={{ backgroundColor: template.color, color: textColor }}
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="font-semibold text-sm truncate">{template.title}</span>
          <span className="text-xs opacity-75">({module.module_instance_id})</span>
        </div>
        {onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(module.module_instance_id);
            }}
            className="p-1 rounded hover:bg-black hover:bg-opacity-20 transition-colors"
            title="Delete module"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* OLD Nodes Section - COMMENTED OUT FOR NEW COMPONENT ARCHITECTURE */}
      {/*
      <div className="border-t border-gray-700 bg-gray-800">
        {Array.from({ length: totalRows }, (_, rowIndex) => {
          const inputNode = module.inputs[rowIndex];
          const outputNode = module.outputs[rowIndex];
          const showAddInput = canAddInputs && rowIndex === module.inputs.length;
          const showAddOutput = canAddOutputs && rowIndex === module.outputs.length;

          return (
            <div key={`row-${rowIndex}`} className="flex border-b border-gray-700 last:border-b-0 min-h-12">
              Input/Output rendering logic here...
            </div>
          );
        })}
      </div>
      */}

      {/* NEW Nodes Section - Clean Side-by-Side Architecture */}
      <div className="border-t border-gray-700 bg-gray-800">
        <div className="flex">
          {/* Input Side - Exactly half width */}
          <div className="flex-1">
            <NodeSectionSide
              side="input"
              ioSideShape={template.meta.io_shape.inputs}
              currentNodes={module.inputs}
              moduleId={module.module_instance_id}
              template={template}
              activeTypeVar={activeTypeVar}
              onTypeVarFocus={handleTypeVarFocus}
              onTypeVarBlur={handleTypeVarBlur}
              getRestrictedTypesForNode={getRestrictedTypesForNode}
              onAddNode={(groupId: string) => {
                // Pass the groupId to enable group-specific node addition
                onAddNode?.(module.module_instance_id, 'input', groupId);
              }}
              onRemoveNode={(nodeId: string, groupId: string) => {
                // Find the node index for the old API (using NodeGroup structure)
                const allInputs = [...(module.inputs?.static || []), ...(module.inputs?.dynamic || [])];
                const nodeIndex = allInputs.findIndex(n => n.node_id === nodeId);
                if (nodeIndex !== -1) {
                  onRemoveNode?.(module.module_instance_id, 'input', nodeIndex);
                }
              }}
              onNodeNameChange={(nodeId: string, newName: string) => {
                // Find the node index for the old API (using NodeGroup structure)
                const allInputs = [...(module.inputs?.static || []), ...(module.inputs?.dynamic || [])];
                const nodeIndex = allInputs.findIndex(n => n.node_id === nodeId);
                if (nodeIndex !== -1) {
                  onNodeNameChange?.(module.module_instance_id, 'input', nodeIndex, newName);
                }
              }}
              onNodeTypeChange={handleCoordinatedNodeTypeChange}
              onNodeClick={(nodeId: string) => {
                onNodeClick?.(module.module_instance_id, nodeId, 'input');
              }}
              getConnectedOutputName={getConnectedOutputName}
              getTypeColor={getTypeColor}
            />
          </div>

          {/* Vertical Separator */}
          <div className="w-px bg-gray-600"></div>

          {/* Output Side - Exactly half width */}
          <div className="flex-1">
            <NodeSectionSide
              side="output"
              ioSideShape={template.meta.io_shape.outputs}
              currentNodes={module.outputs}
              moduleId={module.module_instance_id}
              template={template}
              activeTypeVar={activeTypeVar}
              onTypeVarFocus={handleTypeVarFocus}
              onTypeVarBlur={handleTypeVarBlur}
              getRestrictedTypesForNode={getRestrictedTypesForNode}
              onAddNode={(groupId: string) => {
                // Pass the groupId to enable group-specific node addition
                onAddNode?.(module.module_instance_id, 'output', groupId);
              }}
              onRemoveNode={(nodeId: string, groupId: string) => {
                // Find the node index for the old API (using NodeGroup structure)
                const allOutputs = [...(module.outputs?.static || []), ...(module.outputs?.dynamic || [])];
                const nodeIndex = allOutputs.findIndex(n => n.node_id === nodeId);
                if (nodeIndex !== -1) {
                  onRemoveNode?.(module.module_instance_id, 'output', nodeIndex);
                }
              }}
              onNodeNameChange={(nodeId: string, newName: string) => {
                // Find the node index for the old API (using NodeGroup structure)
                const allOutputs = [...(module.outputs?.static || []), ...(module.outputs?.dynamic || [])];
                const nodeIndex = allOutputs.findIndex(n => n.node_id === nodeId);
                if (nodeIndex !== -1) {
                  onNodeNameChange?.(module.module_instance_id, 'output', nodeIndex, newName);
                }
              }}
              onNodeTypeChange={handleCoordinatedNodeTypeChange}
              onNodeClick={(nodeId: string) => {
                onNodeClick?.(module.module_instance_id, nodeId, 'output');
              }}
              getTypeColor={getTypeColor}
            />
          </div>
        </div>
      </div>

      {/* Configuration Section */}
      {hasConfig && (
        <div className="border-t border-gray-700">
          <div
            className="px-4 py-2 flex items-center justify-between cursor-pointer hover:bg-gray-750 transition-colors"
            onClick={() => setIsConfigExpanded(!isConfigExpanded)}
          >
            <span className="text-gray-300 text-sm font-medium">Configuration</span>
            <svg
              className={`w-4 h-4 text-gray-400 transition-transform ${isConfigExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>

          {isConfigExpanded && (
            <div className="px-4 pb-2 space-y-2">
              {visibleConfigKeys.map((key) => {
                const prop = configProperties[key];
                const value = module.config[key];
                const type = prop.type;

                return (
                  <div key={key}>
                    <label className="block text-gray-300 text-xs mb-1">
                      {prop.title || key}
                      {prop.required && <span className="text-red-400 ml-1">*</span>}
                    </label>

                    {prop.enum ? (
                      <select
                        value={value || prop.default || ''}
                        onChange={(e) => handleConfigChange(key, e.target.value)}
                        onMouseDown={(e) => e.stopPropagation()}
                        className="w-full bg-gray-700 border border-gray-600 text-white text-xs rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        {prop.enum.map((option: any) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    ) : type === 'boolean' ? (
                      <select
                        value={String(value ?? prop.default ?? false)}
                        onChange={(e) => handleConfigChange(key, e.target.value === 'true')}
                        onMouseDown={(e) => e.stopPropagation()}
                        className="w-full bg-gray-700 border border-gray-600 text-white text-xs rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="false">False</option>
                        <option value="true">True</option>
                      </select>
                    ) : type === 'number' || type === 'integer' ? (
                      <input
                        type="number"
                        value={value || prop.default || ''}
                        onChange={(e) => handleConfigChange(key, Number(e.target.value))}
                        onMouseDown={(e) => e.stopPropagation()}
                        placeholder={prop.description}
                        className="w-full bg-gray-700 border border-gray-600 text-white text-xs rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    ) : (
                      <input
                        type="text"
                        value={value || prop.default || ''}
                        onChange={(e) => handleConfigChange(key, e.target.value)}
                        onMouseDown={(e) => e.stopPropagation()}
                        placeholder={prop.description}
                        className="w-full bg-gray-700 border border-gray-600 text-white text-xs rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};