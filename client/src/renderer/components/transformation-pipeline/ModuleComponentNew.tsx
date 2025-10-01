import React, { useState } from 'react';
import { ModuleInstance, ModuleTemplate, NodePin } from '../../types/pipelineTypes';
import { canAddNode, canRemoveNode, hasVariableTypes, getAllowedTypes } from '../../utils/moduleFactory';

interface ModuleComponentNewProps {
  module: ModuleInstance;
  template: ModuleTemplate;
  position: { x: number; y: number };
  isSelected: boolean;
  getConnectedOutputName?: (inputNodeId: string) => string;
  onSelect: (moduleId: string) => void;
  onMouseDown?: (e: React.MouseEvent) => void;
  onDelete?: (moduleId: string) => void;
  onAddNode?: (moduleId: string, nodeType: 'input' | 'output') => void;
  onRemoveNode?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => void;
  onNodeTypeChange?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newType: string) => void;
  onNodeNameChange?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newName: string) => void;
  onNodeClick?: (moduleId: string, nodeId: string, nodeType: 'input' | 'output') => void;
  onConfigChange?: (moduleId: string, config: Record<string, any>) => void;
}

// Get color for node type
const getTypeColor = (type: string): string => {
  switch (type) {
    case 'string': return '#3B82F6'; // Blue
    case 'number': return '#EF4444'; // Red
    case 'boolean': return '#10B981'; // Green
    case 'datetime': return '#8B5CF6'; // Purple
    default: return '#6B7280'; // Gray
  }
};

export const ModuleComponentNew: React.FC<ModuleComponentNewProps> = ({
  module,
  template,
  position,
  isSelected,
  getConnectedOutputName,
  onSelect,
  onMouseDown,
  onDelete,
  onAddNode,
  onRemoveNode,
  onNodeTypeChange,
  onNodeNameChange,
  onNodeClick,
  onConfigChange
}) => {
  const [editingNodeName, setEditingNodeName] = useState<string | null>(null);
  const [isConfigExpanded, setIsConfigExpanded] = useState(false);

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

  // Check if we can add/remove nodes
  const canAddInputs = canAddNode(module.inputs.length, template.meta.inputs);
  const canRemoveInputs = canRemoveNode(module.inputs.length, template.meta.inputs);
  const canAddOutputs = canAddNode(module.outputs.length, template.meta.outputs);
  const canRemoveOutputs = canRemoveNode(module.outputs.length, template.meta.outputs);

  // Calculate total rows including add button rows
  const inputRowCount = module.inputs.length + (canAddInputs ? 1 : 0);
  const outputRowCount = module.outputs.length + (canAddOutputs ? 1 : 0);
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

      {/* Nodes Section */}
      <div className="border-t border-gray-700 bg-gray-800">
        {Array.from({ length: totalRows }, (_, rowIndex) => {
          const inputNode = module.inputs[rowIndex];
          const outputNode = module.outputs[rowIndex];
          const showAddInput = canAddInputs && rowIndex === module.inputs.length;
          const showAddOutput = canAddOutputs && rowIndex === module.outputs.length;

          return (
            <div key={`row-${rowIndex}`} className="flex border-b border-gray-700 last:border-b-0 min-h-12">
              {/* Input Half */}
              <div className="flex-1 flex items-center relative px-3 py-2">
                {inputNode ? (
                  <>
                    {/* Input Node Circle */}
                    <div
                      className="absolute left-0 top-1/2 transform -translate-y-1/2 -translate-x-1/2"
                      style={{ zIndex: 10 }}
                    >
                      <div
                        className="w-5 h-5 rounded-full border-2 border-gray-800 cursor-pointer hover:scale-110 transition-transform"
                        style={{
                          backgroundColor: getTypeColor(inputNode.type),
                          pointerEvents: 'all'
                        }}
                        title={`${inputNode.name} (${inputNode.type})`}
                        onClick={(e) => {
                          e.stopPropagation();
                          onNodeClick?.(module.module_instance_id, inputNode.node_id, 'input');
                        }}
                        onMouseDown={(e) => {
                          e.stopPropagation();
                          e.preventDefault();
                        }}
                        data-node-id={inputNode.node_id}
                        data-node-direction="input"
                        data-module-id={module.module_instance_id}
                      />
                    </div>
                    {/* Input Content */}
                    <div className="ml-3 flex-1">
                      <div className="flex items-stretch gap-2">
                        <div className="flex-1 flex items-center">
                          <textarea
                            value={getConnectedOutputName ? getConnectedOutputName(inputNode.node_id) : inputNode.name}
                            readOnly
                            className={`text-xs bg-transparent border-0 rounded px-1 py-0.5 focus:outline-none w-full text-left resize-none overflow-hidden ${
                              getConnectedOutputName && getConnectedOutputName(inputNode.node_id) === 'Not Connected'
                                ? 'text-gray-500 italic'
                                : 'text-gray-300'
                            }`}
                            style={{
                              minHeight: '20px',
                              height: 'auto',
                              cursor: 'default'
                            }}
                            rows={1}
                            onInput={(e) => {
                              const target = e.target as HTMLTextAreaElement;
                              target.style.height = 'auto';
                              target.style.height = target.scrollHeight + 'px';
                            }}
                          />
                        </div>
                        {/* Label and Type configuration beside name */}
                        <div className="flex items-center">
                          <div className="flex flex-col items-center gap-1">
                            {/* Label */}
                            <div className="text-xs text-gray-400">
                              label
                            </div>
                            {/* Type indicator */}
                            {(() => {
                              const inputMeta = template.meta.inputs;
                              const hasVariableType = hasVariableTypes(inputMeta.type);
                              const allowedTypes = getAllowedTypes(inputMeta.type);

                              if (hasVariableType && allowedTypes.length > 1) {
                                // Show dropdown for variable types
                                return (
                                  <select
                                    value={inputNode.type}
                                    onChange={(e) => {
                                      onNodeTypeChange?.(module.module_instance_id, 'input', rowIndex, e.target.value);
                                    }}
                                    onMouseDown={(e) => e.stopPropagation()}
                                    className="text-xs bg-gray-700 border border-gray-600 text-gray-300 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500 flex-shrink-0 w-16 text-center"
                                  >
                                    {allowedTypes.map(type => (
                                      <option key={type} value={type}>{type}</option>
                                    ))}
                                  </select>
                                );
                              } else {
                                // Show type badge for fixed type
                                return (
                                  <span className="text-xs bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded inline-block flex-shrink-0 w-16 text-center">
                                    {inputNode.type}
                                  </span>
                                );
                              }
                            })()}
                          </div>
                        </div>
                        {canRemoveInputs && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onRemoveNode?.(module.module_instance_id, 'input', rowIndex);
                            }}
                            className="w-3 h-3 flex-shrink-0 text-red-400 hover:text-red-300 transition-colors"
                            title="Remove input"
                          >
                            <svg className="w-full h-full" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                            </svg>
                          </button>
                        )}
                      </div>
                    </div>
                  </>
                ) : showAddInput ? (
                  <>
                    {/* Add Input Button */}
                    <div
                      className="absolute left-0 top-1/2 transform -translate-y-1/2 -translate-x-1/2"
                      style={{ zIndex: 10 }}
                    >
                      <button
                        className="w-5 h-5 rounded-full border-2 border-gray-600 bg-gray-700 hover:bg-gray-600 cursor-pointer hover:scale-110 transition-all flex items-center justify-center"
                        onClick={(e) => {
                          e.stopPropagation();
                          onAddNode?.(module.module_instance_id, 'input');
                        }}
                        onMouseDown={(e) => {
                          e.stopPropagation();
                          e.preventDefault();
                        }}
                        title="Add Input"
                      >
                        <svg className="w-3 h-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                        </svg>
                      </button>
                    </div>
                    <div className="ml-3 text-xs text-gray-500">Add input</div>
                  </>
                ) : null}
              </div>

              {/* Vertical Separator */}
              <div className="flex justify-center py-3">
                <div className="w-px bg-gray-600 h-full min-h-6"></div>
              </div>

              {/* Output Half */}
              <div className="flex-1 flex items-center justify-end relative px-3 py-2">
                {outputNode ? (
                  <>
                    {/* Output Content */}
                    <div className="mr-3 flex-1">
                      <div className="flex items-stretch justify-end gap-2">
                        {/* Label and Type configuration beside name */}
                        <div className="flex items-center">
                          <div className="flex flex-col items-center gap-1">
                            {/* Label */}
                            <div className="text-xs text-gray-400">
                              label
                            </div>
                            {/* Type indicator */}
                            {(() => {
                              const outputMeta = template.meta.outputs;
                              const hasVariableType = hasVariableTypes(outputMeta.type);
                              const allowedTypes = getAllowedTypes(outputMeta.type);

                              if (hasVariableType && allowedTypes.length > 1) {
                                // Show dropdown for variable types
                                return (
                                  <select
                                    value={outputNode.type}
                                    onChange={(e) => {
                                      onNodeTypeChange?.(module.module_instance_id, 'output', rowIndex, e.target.value);
                                    }}
                                    onMouseDown={(e) => e.stopPropagation()}
                                    className="text-xs bg-gray-700 border border-gray-600 text-gray-300 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500 flex-shrink-0 w-16 text-center"
                                  >
                                    {allowedTypes.map(type => (
                                      <option key={type} value={type}>{type}</option>
                                    ))}
                                  </select>
                                );
                              } else {
                                // Show type badge for fixed type
                                return (
                                  <span className="text-xs bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded inline-block flex-shrink-0 w-16 text-center">
                                    {outputNode.type}
                                  </span>
                                );
                              }
                            })()}
                          </div>
                        </div>
                        <div className="flex-1 flex items-center">
                          <textarea
                            value={outputNode.name}
                            onChange={(e) => {
                              onNodeNameChange?.(module.module_instance_id, 'output', rowIndex, e.target.value);
                            }}
                            onKeyDown={(e) => {
                              // Prevent Enter from creating new line, use Shift+Enter for new line
                              if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                (e.target as HTMLTextAreaElement).blur();
                              }
                            }}
                            onClick={(e) => e.stopPropagation()}
                            onMouseDown={(e) => e.stopPropagation()}
                            className="text-xs bg-gray-700 border border-gray-600 text-gray-300 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500 w-full text-right resize-none overflow-hidden"
                            style={{
                              minHeight: '20px',
                              height: 'auto'
                            }}
                            rows={1}
                            onInput={(e) => {
                              const target = e.target as HTMLTextAreaElement;
                              target.style.height = 'auto';
                              target.style.height = target.scrollHeight + 'px';
                            }}
                          />
                        </div>
                        {canRemoveOutputs && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onRemoveNode?.(module.module_instance_id, 'output', rowIndex);
                            }}
                            className="w-3 h-3 flex-shrink-0 text-red-400 hover:text-red-300 transition-colors"
                            title="Remove output"
                          >
                            <svg className="w-full h-full" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                            </svg>
                          </button>
                        )}
                      </div>
                    </div>
                    {/* Output Node Circle */}
                    <div
                      className="absolute right-0 top-1/2 transform -translate-y-1/2 translate-x-1/2"
                      style={{ zIndex: 10 }}
                    >
                      <div
                        className="w-5 h-5 rounded-full border-2 border-gray-800 cursor-pointer hover:scale-110 transition-transform"
                        style={{
                          backgroundColor: getTypeColor(outputNode.type),
                          pointerEvents: 'all'
                        }}
                        title={`${outputNode.name} (${outputNode.type})`}
                        onClick={(e) => {
                          e.stopPropagation();
                          onNodeClick?.(module.module_instance_id, outputNode.node_id, 'output');
                        }}
                        onMouseDown={(e) => {
                          e.stopPropagation();
                          e.preventDefault();
                        }}
                        data-node-id={outputNode.node_id}
                        data-node-direction="output"
                        data-module-id={module.module_instance_id}
                      />
                    </div>
                  </>
                ) : showAddOutput ? (
                  <>
                    <div className="mr-3 text-xs text-gray-500">Add output</div>
                    {/* Add Output Button */}
                    <div
                      className="absolute right-0 top-1/2 transform -translate-y-1/2 translate-x-1/2"
                      style={{ zIndex: 10 }}
                    >
                      <button
                        className="w-5 h-5 rounded-full border-2 border-gray-600 bg-gray-700 hover:bg-gray-600 cursor-pointer hover:scale-110 transition-all flex items-center justify-center"
                        onClick={(e) => {
                          e.stopPropagation();
                          onAddNode?.(module.module_instance_id, 'output');
                        }}
                        onMouseDown={(e) => {
                          e.stopPropagation();
                          e.preventDefault();
                        }}
                        title="Add Output"
                      >
                        <svg className="w-3 h-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                        </svg>
                      </button>
                    </div>
                  </>
                ) : null}
              </div>
            </div>
          );
        })}
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