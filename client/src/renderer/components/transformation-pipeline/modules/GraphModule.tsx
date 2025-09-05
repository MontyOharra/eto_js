import React, { useState } from 'react';
import { BaseModuleTemplate } from '../../../types/modules';
import { NodeListComponent } from '../nodes/NodeListComponent';
import { ModuleDeletionModal } from '../ui/ModuleDeletionModal';
import { GraphModuleHeader } from './GraphModuleHeader';
import { GraphModuleConfiguration } from './GraphModuleConfiguration';

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

interface GraphModuleProps {
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


export const GraphModule: React.FC<GraphModuleProps> = ({
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


  const canAddInputs = (template.dynamicInputs?.enabled && 
    (!template.dynamicInputs.maxNodes || nodes.inputs.length < template.dynamicInputs.maxNodes)) || false;
  
  const canAddOutputs = (template.dynamicOutputs?.enabled && 
    (!template.dynamicOutputs.maxNodes || nodes.outputs.length < template.dynamicOutputs.maxNodes)) || false;

  const canRemoveInputs = (template.dynamicInputs?.enabled && 
    nodes.inputs.length > (template.dynamicInputs.minNodes || 0)) || false;
  
  const canRemoveOutputs = (template.dynamicOutputs?.enabled && 
    nodes.outputs.length > (template.dynamicOutputs.minNodes || 0)) || false;

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
      <GraphModuleHeader 
        template={template}
        onDeleteClick={handleDeleteClick}
      />

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

      <GraphModuleConfiguration
        template={template}
        config={config}
        onConfigChange={onConfigChange || (() => {})}
      />

      {/* Delete Confirmation Modal */}
      <ModuleDeletionModal
        isVisible={showDeleteModal}
        moduleName={template.name}
        onConfirm={handleConfirmDelete}
        onCancel={handleCancelDelete}
      />
    </div>
  );
};