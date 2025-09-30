import React, { useState, useMemo } from "react";
import { NodeListComponentNew } from "../nodes/NodeListComponentNew";
import { ModuleDeletionModal } from "./ModuleDeletionModal";
import { ModuleHeader } from "./ModuleHeader";
import { ModuleConfiguration } from "./ModuleConfiguration";
import {
  ModuleInstance,
  NodePin,
  isNodeSideStatic,
  canAddNode,
  canRemoveNode,
  hasVariableTypes,
  getAllowedTypes
} from "../../../utils/moduleFactory";

interface ModuleTemplate {
  id: string;
  title: string;
  description: string;
  category: string;
  color: string;
  version: string;
  kind: string;
  meta: {
    inputs: {
      allow: boolean;
      min_count: number;
      max_count: number | null;
      type: string | { mode: 'variable'; allowed: string[] };
    };
    outputs: {
      allow: boolean;
      min_count: number;
      max_count: number | null;
      type: string | { mode: 'variable'; allowed: string[] };
    };
  };
  config_schema: any;
}

interface NodeConnection {
  from_node_id: string;
  to_node_id: string;
}

interface ModuleProps {
  moduleData: ModuleInstance;
  template: ModuleTemplate;
  position: { x: number; y: number };
  zoom?: number;
  panOffset?: { x: number; y: number };
  connections?: NodeConnection[];
  placedModules?: ModuleInstance[];
  onMouseDown?: (e: React.MouseEvent) => void;
  onDelete?: () => void;
  onConfigChange?: (moduleId: string, config: Record<string, any>) => void;
  onNodeClick?: (
    moduleId: string,
    nodeType: "input" | "output",
    nodeIndex: number
  ) => (e: React.MouseEvent) => void;
  onAddNode?: (moduleId: string, nodeType: "input" | "output") => void;
  onRemoveNode?: (moduleId: string, nodeType: "input" | "output", nodeIndex: number) => void;
  onNodeTypeChange?: (
    moduleId: string,
    nodeType: "input" | "output",
    nodeIndex: number,
    newType: string
  ) => void;
  onNodePositionUpdate?: (
    moduleId: string,
    nodeType: "input" | "output",
    nodeIndex: number,
    position: { x: number; y: number }
  ) => void;
  onNodeNameChange?: (
    moduleId: string,
    nodeType: "input" | "output",
    nodeIndex: number,
    newName: string
  ) => void;
  getInputDisplayName?: (moduleId: string, nodeIndex: number) => string;
  canChangeType?: (
    moduleId: string,
    nodeType: "input" | "output",
    nodeIndex: number
  ) => boolean;
}

// Convert new node format to old format for compatibility with existing NodeComponent
function convertNodeToOldFormat(node: NodePin): any {
  return {
    id: node.node_id,
    name: node.name,
    type: node.type as any,
    description: '',
    required: true
  };
}

export const ModuleNew: React.FC<ModuleProps> = ({
  moduleData,
  template,
  position,
  zoom,
  panOffset,
  connections,
  placedModules,
  onMouseDown,
  onDelete,
  onConfigChange,
  onNodeClick,
  onAddNode,
  onRemoveNode,
  onNodeTypeChange,
  onNodePositionUpdate,
  onNodeNameChange,
  getInputDisplayName,
  canChangeType,
}) => {
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  // Determine if nodes are static or dynamic
  const inputsStatic = isNodeSideStatic(template.meta.inputs);
  const outputsStatic = isNodeSideStatic(template.meta.outputs);

  // Can add/remove nodes
  const canAddInputs = canAddNode(moduleData.inputs.length, template.meta.inputs);
  const canRemoveInputs = canRemoveNode(moduleData.inputs.length, template.meta.inputs);
  const canAddOutputs = canAddNode(moduleData.outputs.length, template.meta.outputs);
  const canRemoveOutputs = canRemoveNode(moduleData.outputs.length, template.meta.outputs);

  // Check if types are variable
  const inputTypesVariable = hasVariableTypes(template.meta.inputs.type);
  const outputTypesVariable = hasVariableTypes(template.meta.outputs.type);

  // Get allowed types
  const allowedInputTypes = getAllowedTypes(template.meta.inputs.type);
  const allowedOutputTypes = getAllowedTypes(template.meta.outputs.type);

  // Convert nodes to old format for compatibility
  const inputNodes = useMemo(() =>
    moduleData.inputs.map(convertNodeToOldFormat),
    [moduleData.inputs]
  );

  const outputNodes = useMemo(() =>
    moduleData.outputs.map(convertNodeToOldFormat),
    [moduleData.outputs]
  );

  // Create a template-like object for ModuleHeader
  const headerTemplate = {
    name: template.title || template.id,
    description: template.description,
    category: template.category,
    color: template.color
  };

  // Convert config_schema to config array for ModuleConfiguration
  const configArray = useMemo(() => {
    if (!template.config_schema?.properties) return [];

    return Object.entries(template.config_schema.properties).map(([key, prop]: [string, any]) => {
      let uiType = prop.type || 'string';

      // Determine UI type
      if (prop.enum) {
        uiType = 'select';
      } else if (prop['x-ui']?.widget === 'textarea') {
        uiType = 'textarea';
      } else if (prop.type === 'boolean') {
        uiType = 'boolean';
      } else if (prop.type === 'integer' || prop.type === 'number') {
        uiType = 'number';
      }

      return {
        name: key,
        type: uiType,
        description: prop.description || prop.title || '',
        required: template.config_schema.required?.includes(key) || false,
        defaultValue: prop.default,
        options: prop.enum,
        placeholder: prop['x-ui']?.placeholder,
        hidden: prop['x-ui']?.hidden || false
      };
    });
  }, [template.config_schema]);

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

  const handleConfigChange = (config: Record<string, any>) => {
    if (onConfigChange) {
      onConfigChange(moduleData.module_instance_id, config);
    }
  };

  const handleAddInput = () => {
    if (onAddNode) {
      onAddNode(moduleData.module_instance_id, 'input');
    }
  };

  const handleAddOutput = () => {
    if (onAddNode) {
      onAddNode(moduleData.module_instance_id, 'output');
    }
  };

  const handleRemoveInput = (moduleId: string, inputIndex: number) => {
    if (onRemoveNode) {
      onRemoveNode(moduleData.module_instance_id, 'input', inputIndex);
    }
  };

  const handleRemoveOutput = (moduleId: string, outputIndex: number) => {
    if (onRemoveNode) {
      onRemoveNode(moduleData.module_instance_id, 'output', outputIndex);
    }
  };

  // Custom type change handler that respects allowed types
  const handleNodeTypeChange = (
    moduleId: string,
    nodeType: "input" | "output",
    nodeIndex: number,
    newType: string
  ) => {
    // Check if the new type is allowed
    const allowedTypes = nodeType === 'input' ? allowedInputTypes : allowedOutputTypes;
    if (!allowedTypes.includes(newType)) {
      console.warn(`Type ${newType} not allowed for ${nodeType}`);
      return;
    }

    if (onNodeTypeChange) {
      onNodeTypeChange(moduleData.module_instance_id, nodeType, nodeIndex, newType);
    }
  };

  // Override canChangeType to check if types are variable
  const canChangeNodeType = (
    moduleId: string,
    nodeType: "input" | "output",
    nodeIndex: number
  ): boolean => {
    // First check if the node side allows variable types
    const isVariable = nodeType === 'input' ? inputTypesVariable : outputTypesVariable;
    if (!isVariable) return false;

    // Then check any custom logic
    if (canChangeType) {
      return canChangeType(moduleId, nodeType, nodeIndex);
    }

    return true;
  };

  // Template-like object for compatibility
  const compatTemplate = {
    ...headerTemplate,
    config: configArray
  };

  return (
    <div
      className="absolute bg-gray-800 rounded-lg shadow-lg border-2 border-gray-600 cursor-pointer select-none"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        minWidth: "240px",
        width: "max-content",
        maxWidth: "320px",
        transform: "translate(-50%, 0)",
        userSelect: "none",
        WebkitUserSelect: "none",
        MozUserSelect: "none",
        msUserSelect: "none",
      }}
      onMouseDown={handleMouseDown}
    >
      <ModuleHeader template={compatTemplate as any} onDeleteClick={handleDeleteClick} />

      {/* Nodes Section */}
      {(inputNodes.length > 0 ||
        outputNodes.length > 0 ||
        canAddInputs ||
        canAddOutputs) && (
        <NodeListComponentNew
          moduleId={moduleData.module_instance_id}
          modulePosition={position}
          zoom={zoom}
          panOffset={panOffset}
          connections={connections as any}
          placedModules={placedModules as any}
          inputNodes={inputNodes}
          outputNodes={outputNodes}
          canAddInputs={canAddInputs}
          canAddOutputs={canAddOutputs}
          canRemoveInputs={canRemoveInputs}
          canRemoveOutputs={canRemoveOutputs}
          allowInputTypeConfiguration={inputTypesVariable}
          allowOutputTypeConfiguration={outputTypesVariable}
          allowedInputTypes={allowedInputTypes}
          allowedOutputTypes={allowedOutputTypes}
          onNodeClick={onNodeClick}
          onRemoveInput={handleRemoveInput}
          onRemoveOutput={handleRemoveOutput}
          onAddInput={onAddNode ? handleAddInput : undefined}
          onAddOutput={onAddNode ? handleAddOutput : undefined}
          onNodeTypeChange={handleNodeTypeChange}
          onNodePositionUpdate={onNodePositionUpdate}
          onNameChange={onNodeNameChange}
          getInputDisplayName={getInputDisplayName}
          canChangeType={canChangeNodeType}
        />
      )}

      <ModuleConfiguration
        template={compatTemplate as any}
        config={moduleData.config}
        onConfigChange={handleConfigChange}
      />

      {/* Delete Confirmation Modal */}
      <ModuleDeletionModal
        isVisible={showDeleteModal}
        moduleName={template.title || template.id}
        onConfirm={handleConfirmDelete}
        onCancel={handleCancelDelete}
      />
    </div>
  );
};