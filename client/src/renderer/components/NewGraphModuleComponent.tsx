import React, { useState, useRef, useEffect } from 'react';
import { BaseModuleTemplate } from '../data/testModules';
import { NodeListComponent } from './NodeListComponent';

interface NodeState {
  id: string;
  name: string;
  type: 'string' | 'number' | 'boolean' | 'datetime';
  description: string;
  required: boolean;
}

interface ModuleNodeState {
  inputs: NodeState[];
  outputs: NodeState[];
}

interface NodeConnection {
  id: string;
  fromModuleId: string;
  fromOutputIndex: number;
  toModuleId: string;
  toInputIndex: number;
}

interface PlacedModule {
  id: string;
  template: any;
  position: { x: number; y: number };
  config: any;
  nodes: {
    inputs: any[];
    outputs: any[];
  };
}

interface NewGraphModuleComponentProps {
  moduleId: string;
  template: BaseModuleTemplate;
  position: { x: number; y: number };
  config?: Record<string, any>;
  nodes: ModuleNodeState;
  zoom?: number; // Add zoom level
  panOffset?: { x: number; y: number }; // Add pan offset
  connections?: NodeConnection[]; // Add connections
  placedModules?: PlacedModule[]; // Add placed modules
  onMouseDown?: (e: React.MouseEvent) => void;
  onDelete?: () => void;
  onConfigChange?: (config: Record<string, any>) => void;
  onNodeClick?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => (e: React.MouseEvent) => void;
  onAddInput?: (moduleId: string) => void;
  onRemoveInput?: (moduleId: string, inputIndex: number) => void;
  onAddOutput?: (moduleId: string) => void;
  onRemoveOutput?: (moduleId: string, outputIndex: number) => void;
  onNodeTypeChange?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newType: 'string' | 'number' | 'boolean' | 'datetime') => void;
  onNodePositionUpdate?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, position: { x: number; y: number }) => void;
  onNameChange?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newName: string) => void;
  getInputDisplayName?: (moduleId: string, nodeIndex: number) => string;
  canChangeType?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => boolean;
}


export const NewGraphModuleComponent: React.FC<NewGraphModuleComponentProps> = ({
  moduleId,
  template,
  position,
  config = {},
  nodes,
  zoom,
  panOffset,
  connections,
  placedModules,
  onMouseDown,
  onDelete,
  onConfigChange,
  onNodeClick,
  onAddInput,
  onRemoveInput,
  onAddOutput,
  onRemoveOutput,
  onNodeTypeChange,
  onNodePositionUpdate,
  onNameChange,
  getInputDisplayName,
  canChangeType
}) => {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isConfigExpanded, setIsConfigExpanded] = useState(true);

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

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    if (onMouseDown) {
      onMouseDown(e);
    }
  };

  const handleConfigChange = (configName: string, value: any) => {
    const newConfig = { ...config, [configName]: value };
    if (onConfigChange) {
      onConfigChange(newConfig);
    }
  };

  const canAddInputs = template.dynamicInputs?.enabled && 
    (!template.dynamicInputs.maxNodes || nodes.inputs.length < template.dynamicInputs.maxNodes);
  
  const canAddOutputs = template.dynamicOutputs?.enabled && 
    (!template.dynamicOutputs.maxNodes || nodes.outputs.length < template.dynamicOutputs.maxNodes);

  const canRemoveInputs = template.dynamicInputs?.enabled && 
    nodes.inputs.length > (template.dynamicInputs.minNodes || 0);
  
  const canRemoveOutputs = template.dynamicOutputs?.enabled && 
    nodes.outputs.length > (template.dynamicOutputs.minNodes || 0);

  return (
    <div
      className="absolute bg-gray-800 rounded-lg shadow-lg border-2 border-gray-600 cursor-pointer select-none"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        minWidth: '240px',
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
      <div className="px-4 py-2 bg-gray-750">
        <div className="text-gray-300 text-xs leading-relaxed">
          {template.description}
        </div>
      </div>

      {/* Nodes Section */}
      {(nodes.inputs.length > 0 || nodes.outputs.length > 0 || canAddInputs || canAddOutputs) && (
        <NodeListComponent
          moduleId={moduleId}
          modulePosition={position}
          zoom={zoom}
          panOffset={panOffset}
          connections={connections}
          placedModules={placedModules}
          inputNodes={nodes.inputs}
          outputNodes={nodes.outputs}
          canAddInputs={canAddInputs}
          canAddOutputs={canAddOutputs}
          canRemoveInputs={canRemoveInputs}
          canRemoveOutputs={canRemoveOutputs}
          allowInputTypeConfiguration={template.dynamicInputs?.allowTypeConfiguration || false}
          allowOutputTypeConfiguration={template.dynamicOutputs?.allowTypeConfiguration || false}
          onNodeClick={onNodeClick}
          onRemoveInput={onRemoveInput}
          onRemoveOutput={onRemoveOutput}
          onAddInput={onAddInput}
          onAddOutput={onAddOutput}
          onNodeTypeChange={onNodeTypeChange}
          onNodePositionUpdate={onNodePositionUpdate}
          onNameChange={onNameChange}
          getInputDisplayName={getInputDisplayName}
          canChangeType={canChangeType}
        />
      )}

      {/* Configuration Section */}
      {template.config && template.config.filter(c => !c.hidden).length > 0 && (
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
              {template.config.filter(c => !c.hidden).map((configItem) => (
                <div key={configItem.name}>
                  <label className="block text-gray-300 text-xs mb-1">
                    {configItem.description}
                    {configItem.required && <span className="text-red-400 ml-1">*</span>}
                  </label>
                  {configItem.type === 'select' ? (
                    <select
                      value={config[configItem.name] || configItem.defaultValue || ''}
                      onChange={(e) => handleConfigChange(configItem.name, e.target.value)}
                      onMouseDown={(e) => e.stopPropagation()}
                      className="w-full bg-gray-700 border border-gray-600 text-white text-xs rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {configItem.options?.map(option => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={configItem.type === 'number' ? 'number' : 'text'}
                      value={config[configItem.name] || configItem.defaultValue || ''}
                      onChange={(e) => handleConfigChange(configItem.name, e.target.value)}
                      onMouseDown={(e) => e.stopPropagation()}
                      placeholder={configItem.placeholder}
                      className="w-full bg-gray-700 border border-gray-600 text-white text-xs rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  )}
                </div>
              ))}
            </div>
          )}
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