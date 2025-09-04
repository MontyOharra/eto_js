import React, { useState, useRef, useEffect } from 'react';
import { BaseModuleTemplate, ModuleConfig, ModuleInput, ModuleOutput } from '../types/modules';

interface GraphModuleComponentProps {
  moduleId: string;
  template: BaseModuleTemplate;
  position: { x: number; y: number };
  config?: Record<string, unknown>;
  runtimeInputs?: ModuleInput[];
  runtimeOutputs?: ModuleOutput[];
  onMouseDown?: (e: React.MouseEvent) => void;
  onDelete?: () => void;
  onConfigChange?: (config: Record<string, unknown>) => void;
  onNodeClick?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => (e: React.MouseEvent) => void;
  onLayoutUpdate?: (moduleId: string, layout: { 
    headerHeight: number; 
    descriptionHeight: number; 
    nodesSectionTop: number; 
    moduleWidth: number;
    nodePositions: {
      inputs: { x: number; y: number; }[];
      outputs: { x: number; y: number; }[];
    };
  }) => void;
  onAddInput?: (moduleId: string) => void;
  onRemoveInput?: (moduleId: string, inputIndex: number) => void;
  onAddOutput?: (moduleId: string) => void;
  onRemoveOutput?: (moduleId: string, outputIndex: number) => void;
}

export const GraphModuleComponent: React.FC<GraphModuleComponentProps> = ({
  moduleId,
  template,
  position,
  config = {},
  runtimeInputs,
  runtimeOutputs,
  onMouseDown,
  onDelete,
  onConfigChange,
  onNodeClick,
  onLayoutUpdate,
  onAddInput,
  onRemoveInput,
  onAddOutput,
  onRemoveOutput
}) => {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isConfigExpanded, setIsConfigExpanded] = useState(true);
  
  // Get current inputs and outputs (runtime or template)
  const currentInputs = runtimeInputs || template.inputs;
  const currentOutputs = runtimeOutputs || template.outputs;
  
  // Refs for measuring component sections
  const moduleRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLDivElement>(null);
  const descriptionRef = useRef<HTMLDivElement>(null);
  const nodesSectionRef = useRef<HTMLDivElement>(null);
  
  // Refs for tracking individual node rows
  const inputNodeRefs = useRef<(HTMLDivElement | null)[]>([]);
  const outputNodeRefs = useRef<(HTMLDivElement | null)[]>([]);

  // Measure and report layout dimensions
  useEffect(() => {
    if (moduleRef.current && headerRef.current && descriptionRef.current && onLayoutUpdate) {
      const moduleRect = moduleRef.current.getBoundingClientRect();
      const moduleWidth = moduleRef.current.offsetWidth;
      const headerHeight = headerRef.current.offsetHeight;
      const descriptionHeight = descriptionRef.current.offsetHeight;
      
      // Calculate the top position of the nodes section relative to the module top
      const nodesSectionTop = headerHeight + descriptionHeight;
      
      // Calculate individual node positions
      const nodePositions = {
        inputs: [] as { x: number; y: number; }[],
        outputs: [] as { x: number; y: number; }[]
      };
      
      // Measure input node positions
      inputNodeRefs.current.forEach((nodeRef, index) => {
        if (nodeRef && index < currentInputs.length) {
          const nodeRect = nodeRef.getBoundingClientRect();
          const nodeCenterX = nodeRect.left + (nodeRect.width / 2) - moduleRect.left;
          const nodeCenterY = nodeRect.top + (nodeRect.height / 2) - moduleRect.top;
          nodePositions.inputs.push({ 
            x: nodeCenterX - (moduleWidth / 2), // Relative to module center
            y: nodeCenterY 
          });
        }
      });
      
      // Measure output node positions  
      outputNodeRefs.current.forEach((nodeRef, index) => {
        if (nodeRef && index < currentOutputs.length) {
          const nodeRect = nodeRef.getBoundingClientRect();
          const nodeCenterX = nodeRect.left + (nodeRect.width / 2) - moduleRect.left;
          const nodeCenterY = nodeRect.top + (nodeRect.height / 2) - moduleRect.top;
          nodePositions.outputs.push({ 
            x: nodeCenterX - (moduleWidth / 2), // Relative to module center
            y: nodeCenterY 
          });
        }
      });
      
      onLayoutUpdate(moduleId, {
        headerHeight,
        descriptionHeight,
        nodesSectionTop,
        moduleWidth,
        nodePositions
      });
    }
  }, [moduleId, template.description, currentInputs.length, currentOutputs.length, onLayoutUpdate]); // Include node counts in dependencies

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowDeleteModal(true);
  };

  const handleConfirmDelete = () => {
    if (onDelete) {
      onDelete();
    }
    setShowDeleteModal(false);
  };

  const handleCancelDelete = () => {
    setShowDeleteModal(false);
  };

  const handleConfigToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsConfigExpanded(!isConfigExpanded);
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'string': return '#3B82F6'; // Blue
      case 'number': return '#10B981'; // Green  
      case 'boolean': return '#8B5CF6'; // Purple
      case 'array': return '#F59E0B'; // Orange
      case 'object': return '#EF4444'; // Red
      case 'file': return '#6B7280'; // Gray
      default: return '#9CA3AF'; // Default gray
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault(); // Prevent text selection
    if (onMouseDown) {
      onMouseDown(e);
    }
  };

  const handleConfigChange = (configName: string, value: any) => { // eslint-disable-line @typescript-eslint/no-explicit-any
    const newConfig = { ...config, [configName]: value };
    if (onConfigChange) {
      onConfigChange(newConfig);
    }
  };

  const renderConfigInput = (configItem: ModuleConfig) => {
    const value = config[configItem.name] ?? configItem.defaultValue;

    switch (configItem.type) {
      case 'boolean':
        return (
          <div key={configItem.name} className="mb-3">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={value || false}
                onChange={(e) => handleConfigChange(configItem.name, e.target.checked)}
                onMouseDown={(e) => e.stopPropagation()}
                onFocus={(e) => e.stopPropagation()}
                onClick={(e) => e.stopPropagation()}
                className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2"
              />
              <span className="text-white text-sm">{configItem.description}</span>
              {configItem.required && <span className="text-red-400 text-xs">*</span>}
            </label>
          </div>
        );

      case 'select':
        return (
          <div key={configItem.name} className="mb-3">
            <label className="block text-white text-sm mb-1">
              {configItem.description}
              {configItem.required && <span className="text-red-400 text-xs ml-1">*</span>}
            </label>
            <select
              value={value || ''}
              onChange={(e) => handleConfigChange(configItem.name, e.target.value)}
              onMouseDown={(e) => e.stopPropagation()}
              onFocus={(e) => e.stopPropagation()}
              onClick={(e) => e.stopPropagation()}
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {!configItem.required && <option value="">Select option...</option>}
              {configItem.options?.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
        );

      case 'textarea':
        return (
          <div key={configItem.name} className="mb-3">
            <label className="block text-white text-sm mb-1">
              {configItem.description}
              {configItem.required && <span className="text-red-400 text-xs ml-1">*</span>}
            </label>
            <textarea
              value={value || ''}
              onChange={(e) => handleConfigChange(configItem.name, e.target.value)}
              onMouseDown={(e) => e.stopPropagation()}
              onFocus={(e) => e.stopPropagation()}
              onClick={(e) => e.stopPropagation()}
              placeholder={configItem.placeholder}
              rows={3}
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>
        );

      case 'number':
        return (
          <div key={configItem.name} className="mb-3">
            <label className="block text-white text-sm mb-1">
              {configItem.description}
              {configItem.required && <span className="text-red-400 text-xs ml-1">*</span>}
            </label>
            <input
              type="number"
              value={value || ''}
              onChange={(e) => handleConfigChange(configItem.name, e.target.value ? Number(e.target.value) : '')}
              onMouseDown={(e) => e.stopPropagation()}
              onFocus={(e) => e.stopPropagation()}
              onClick={(e) => e.stopPropagation()}
              placeholder={configItem.placeholder}
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        );

      case 'string':
      default:
        return (
          <div key={configItem.name} className="mb-3">
            <label className="block text-white text-sm mb-1">
              {configItem.description}
              {configItem.required && <span className="text-red-400 text-xs ml-1">*</span>}
            </label>
            <input
              type="text"
              value={value || ''}
              onChange={(e) => handleConfigChange(configItem.name, e.target.value)}
              onMouseDown={(e) => e.stopPropagation()}
              onFocus={(e) => e.stopPropagation()}
              onClick={(e) => e.stopPropagation()}
              placeholder={configItem.placeholder}
              className="w-full bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        );
    }
  };

  return (
    <div
      ref={moduleRef}
      className="absolute bg-gray-800 rounded-lg shadow-lg border-2 border-gray-600 cursor-pointer select-none"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        minWidth: '220px',
        width: 'max-content',
        maxWidth: '320px',
        transform: 'translate(-50%, 0)',
        userSelect: 'none',
        WebkitUserSelect: 'none',
        MozUserSelect: 'none',
        msUserSelect: 'none'
      }}
      onMouseDown={handleMouseDown}
    >
      {/* Header */}
      <div 
        ref={headerRef}
        className="px-4 py-3 rounded-t-lg flex items-center justify-between gap-4"
        style={{ backgroundColor: template.color }}
      >
        <div className="text-white font-medium text-sm flex-1">{template.name}</div>
        <button
          onClick={handleDeleteClick}
          className="w-7 h-7 flex items-center justify-center text-white hover:bg-red-600 hover:text-white rounded transition-colors"
          title="Delete module"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      {/* Description */}
      <div ref={descriptionRef} className="px-4 py-2">
        <div className="text-gray-400 text-xs leading-relaxed">
          {template.description}
        </div>
      </div>

      {/* Input/Output Section */}
      {(currentInputs.length > 0 || currentOutputs.length > 0) && (
        <div ref={nodesSectionRef} className="py-3 border-t border-gray-700 relative">
          {(() => {
            const maxNodes = Math.max(currentInputs.length, currentOutputs.length);
            
            // Only add extra row if we can add more inputs or outputs
            const canAddInput = template.maxInputs === undefined || currentInputs.length < template.maxInputs;
            const canAddOutput = template.maxOutputs === undefined || currentOutputs.length < template.maxOutputs;
            const needsAddButtonRow = canAddInput || canAddOutput;
            
            const totalRows = maxNodes + (needsAddButtonRow ? 1 : 0);
            const rows = [];
            
            for (let i = 0; i < totalRows; i++) {
              const input = currentInputs[i];
              const output = currentOutputs[i];
              
              // Check if we should show add buttons based on dynamic config or legacy maxInputs/maxOutputs
              const canAddInput = template.dynamicInputs?.enabled 
                ? (!template.dynamicInputs.maxNodes || currentInputs.length < template.dynamicInputs.maxNodes)
                : (template.maxInputs === undefined || currentInputs.length < template.maxInputs);
              
              const canAddOutput = template.dynamicOutputs?.enabled 
                ? (!template.dynamicOutputs.maxNodes || currentOutputs.length < template.dynamicOutputs.maxNodes)
                : (template.maxOutputs === undefined || currentOutputs.length < template.maxOutputs);
              
              const needsInputAddButton = i === currentInputs.length && canAddInput;
              const needsOutputAddButton = i === currentOutputs.length && canAddOutput;
              
              rows.push(
                <div key={`node-row-${i}`} className="flex relative min-h-8">
                  {/* Input Half */}
                  <div className="flex-1 flex items-center relative px-4">
                    {input ? (
                      <>
                        {/* Input Node - Circle centered on left edge */}
                        <div 
                          className="absolute w-5 h-8 flex items-center justify-center"
                          style={{ left: '-10px' }}
                        >
                          <div
                            ref={(el) => { inputNodeRefs.current[i] = el; }}
                            className="w-5 h-5 rounded-full border-2 border-gray-800 cursor-pointer hover:scale-110 transition-transform"
                            style={{ 
                              backgroundColor: getTypeColor(input.type),
                              pointerEvents: 'all',
                              zIndex: 1000 // Ensure nodes are above SVG overlay
                            }}
                            title={`${input.name} (${input.type}): ${input.description}`}
                            onClick={onNodeClick ? onNodeClick(moduleId, 'input', i) : undefined}
                            onMouseDown={(e) => {
                              e.stopPropagation();
                              e.preventDefault();
                            }}
                          />
                        </div>
                        {/* Input Text */}
                        <div className="ml-4 flex-1">
                          <div className="text-xs text-gray-300 break-words leading-tight flex items-center gap-1">
                            {input.name}
                            {/* Remove button for dynamic inputs */}
                            {template.dynamicInputs?.enabled && currentInputs.length > (template.dynamicInputs.minNodes || 0) && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onRemoveInput?.(moduleId, i);
                                }}
                                className="w-3 h-3 text-red-400 hover:text-red-300 transition-colors"
                                title="Remove input"
                              >
                                <svg className="w-full h-full" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                                </svg>
                              </button>
                            )}
                          </div>
                          <div className="text-xs text-gray-500">
                            {input.dynamicType ? (
                              <select
                                value={config[input.dynamicType?.configKey || ''] || input.type}
                                onChange={(e) => handleConfigChange(input.dynamicType.configKey, e.target.value)}
                                onMouseDown={(e) => e.stopPropagation()}
                                onFocus={(e) => e.stopPropagation()}
                                onClick={(e) => e.stopPropagation()}
                                className="bg-gray-700 border border-gray-600 text-gray-300 text-xs rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
                              >
                                {input.dynamicType.options.map(option => (
                                  <option key={option} value={option}>
                                    {option}
                                  </option>
                                ))}
                              </select>
                            ) : (
                              `(${input.type})`
                            )}
                          </div>
                        </div>
                      </>
                    ) : needsInputAddButton ? (
                      <>
                        {/* Add Input Button - Circle centered on left edge */}
                        <div 
                          className="absolute w-5 h-8 flex items-center justify-center"
                          style={{ left: '-10px' }}
                        >
                          <button
                            className="w-5 h-5 rounded-full border-2 border-gray-600 bg-gray-700 hover:bg-gray-600 cursor-pointer hover:scale-110 transition-all flex items-center justify-center"
                            onClick={(e) => {
                              e.stopPropagation();
                              onAddInput?.(moduleId);
                            }}
                            title="Add Input"
                          >
                            <svg className="w-3 h-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                            </svg>
                          </button>
                        </div>
                      </>
                    ) : null}
                  </div>
                  
                  {/* Output Half */}
                  <div className="flex-1 flex items-center justify-end relative px-4">
                    {output ? (
                      <>
                        {/* Output Text */}
                        <div className="mr-4 flex-1 text-right">
                          <div className="text-xs text-gray-300 break-words leading-tight flex items-center justify-end gap-1">
                            {output.name}
                            {/* Remove button for dynamic outputs */}
                            {template.dynamicOutputs?.enabled && currentOutputs.length > (template.dynamicOutputs.minNodes || 0) && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onRemoveOutput?.(moduleId, i);
                                }}
                                className="w-3 h-3 text-red-400 hover:text-red-300 transition-colors"
                                title="Remove output"
                              >
                                <svg className="w-full h-full" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                                </svg>
                              </button>
                            )}
                          </div>
                          <div className="text-xs text-gray-500">
                            {output.dynamicType ? (
                              <select
                                value={config[output.dynamicType?.configKey || ''] || output.type}
                                onChange={(e) => handleConfigChange(output.dynamicType.configKey, e.target.value)}
                                onMouseDown={(e) => e.stopPropagation()}
                                onFocus={(e) => e.stopPropagation()}
                                onClick={(e) => e.stopPropagation()}
                                className="bg-gray-700 border border-gray-600 text-gray-300 text-xs rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
                              >
                                {output.dynamicType.options.map(option => (
                                  <option key={option} value={option}>
                                    {option}
                                  </option>
                                ))}
                              </select>
                            ) : (
                              `(${output.type})`
                            )}
                          </div>
                        </div>
                        {/* Output Node - Circle centered on right edge */}
                        <div 
                          className="absolute w-5 h-8 flex items-center justify-center"
                          style={{ right: '-10px' }}
                        >
                          <div
                            ref={(el) => { outputNodeRefs.current[i] = el; }}
                            className="w-5 h-5 rounded-full border-2 border-gray-800 cursor-pointer hover:scale-110 transition-transform"
                            style={{ 
                              backgroundColor: getTypeColor(output.type),
                              pointerEvents: 'all',
                              zIndex: 1000 // Ensure nodes are above SVG overlay
                            }}
                            title={`${output.name} (${output.type}): ${output.description}`}
                            onClick={onNodeClick ? onNodeClick(moduleId, 'output', i) : undefined}
                            onMouseDown={(e) => {
                              e.stopPropagation();
                              e.preventDefault();
                            }}
                          />
                        </div>
                      </>
                    ) : needsOutputAddButton ? (
                      <>
                        {/* Add Output Button - Circle centered on right edge */}
                        <div 
                          className="absolute w-5 h-8 flex items-center justify-center"
                          style={{ right: '-10px' }}
                        >
                          <button
                            className="w-5 h-5 rounded-full border-2 border-gray-600 bg-gray-700 hover:bg-gray-600 cursor-pointer hover:scale-110 transition-all flex items-center justify-center"
                            onClick={(e) => {
                              e.stopPropagation();
                              onAddOutput?.(moduleId);
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
            }
            
            return rows;
          })()}
        </div>
      )}

      {/* Configuration Section */}
      {template.config && template.config.length > 0 && (
        <div 
          className="border-t border-gray-700"
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Configuration Header */}
          <div 
            className="px-4 py-2 flex items-center justify-between cursor-pointer hover:bg-gray-750 transition-colors"
            onClick={handleConfigToggle}
          >
            <div className="text-white text-sm font-medium">Configuration</div>
            <svg 
              className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${
                isConfigExpanded ? 'transform rotate-180' : ''
              }`}
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
          
          {/* Configuration Content */}
          <div 
            className={`overflow-hidden transition-all duration-300 ease-in-out ${
              isConfigExpanded ? 'max-h-screen opacity-100' : 'max-h-0 opacity-0'
            }`}
          >
            <div className="px-4 pb-2">
              <div className="space-y-2">
                {template.config.filter(configItem => !configItem.hidden).map((configItem) => renderConfigInput(configItem))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="absolute -top-24 left-1/2 transform -translate-x-1/2 z-50">
          <div className="bg-gray-800 rounded-lg shadow-xl border border-gray-700 p-4 w-64">
            <h3 className="text-white font-semibold text-sm mb-2">Delete Module</h3>
            <p className="text-gray-300 text-xs mb-4">
              Are you sure you want to delete "{template.name}"?
            </p>
            <div className="flex space-x-2">
              <button
                onClick={handleCancelDelete}
                className="flex-1 px-3 py-1.5 bg-gray-600 hover:bg-gray-700 text-white text-xs rounded transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                className="flex-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs rounded transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};