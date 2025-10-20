/**
 * ModuleNodes Component
 * Displays inputs and outputs sections side by side
 */

import { ModuleTemplate, ModuleInstance, NodePin } from '../../../../types/moduleTypes';
import { groupNodesByIndex } from '../../../../utils/pipeline/moduleUtils';
import { NodeGroupSection } from './nodes/NodeGroupSection';

export interface ModuleNodesProps {
  moduleInstance: ModuleInstance;
  template: ModuleTemplate;
  onUpdateNode?: (moduleId: string, nodeId: string, updates: Partial<NodePin>) => void;
  onAddNode?: (moduleId: string, direction: 'input' | 'output', groupIndex: number) => void;
  onRemoveNode?: (moduleId: string, nodeId: string) => void;
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
  highlightedTypeVar: string | null;
  onTypeVarFocus: (typeVar: string | null) => void;
  executionMode?: boolean;
  executionValues?: Map<string, { value: any; type: string; name: string }>;
  onModuleMouseEnter?: (moduleId: string) => void;
  onModuleMouseLeave?: () => void;
}

export function ModuleNodes({
  moduleInstance,
  template,
  onUpdateNode,
  onAddNode,
  onRemoveNode,
  onTextFocus,
  onTextBlur,
  onHandleClick,
  pendingConnection,
  getEffectiveAllowedTypes,
  getConnectedOutputName,
  highlightedTypeVar,
  onTypeVarFocus,
  executionMode = false,
  executionValues,
  onModuleMouseEnter,
  onModuleMouseLeave,
}: ModuleNodesProps) {
  // Group inputs and outputs
  const inputGroups = groupNodesByIndex(moduleInstance.inputs);
  const outputGroups = groupNodesByIndex(moduleInstance.outputs);

  const handleTypeChange = (nodeId: string, newType: string) => {
    if (!onUpdateNode) return;

    // Find the node being changed to get its typevar
    const allNodes = [...moduleInstance.inputs, ...moduleInstance.outputs];
    const changedNode = allNodes.find((n) => n.node_id === nodeId);

    if (!changedNode || !changedNode.type_var) {
      // No typevar, just update this node
      onUpdateNode(moduleInstance.module_instance_id, nodeId, { type: newType });
      return;
    }

    // Update all nodes with the same typevar
    const typeVar = changedNode.type_var;
    allNodes.forEach((node) => {
      if (node.type_var === typeVar) {
        onUpdateNode(moduleInstance.module_instance_id, node.node_id, { type: newType });
      }
    });
  };

  const handleNameChange = (nodeId: string, newName: string) => {
    if (onUpdateNode) {
      onUpdateNode(moduleInstance.module_instance_id, nodeId, { name: newName });
    }
  };

  // Wrapper to get connected output name
  const getConnectedName = (inputNodeId: string): string | undefined => {
    if (!getConnectedOutputName) return undefined;
    return getConnectedOutputName(moduleInstance.module_instance_id, inputNodeId);
  };

  return (
    <div
      className="flex relative nodrag nopan"
      style={{ pointerEvents: 'auto' }}
      onMouseEnter={() => onModuleMouseEnter?.(moduleInstance.module_instance_id)}
      onMouseLeave={() => onModuleMouseLeave?.()}
    >
      {/* Inputs Section */}
      <div className="w-1/2 p-3 border-r border-gray-600">
        {Array.from(inputGroups.entries()).map(([groupIndex, nodes]) => (
          <NodeGroupSection
            key={groupIndex}
            groupIndex={groupIndex}
            groupLabel={nodes[0]?.label || 'Group'}
            nodes={nodes}
            direction="input"
            moduleId={moduleInstance.module_instance_id}
            template={template}
            onTypeChange={handleTypeChange}
            onNameChange={handleNameChange}
            onAddNode={onAddNode}
            onRemoveNode={onRemoveNode}
            getConnectedOutputName={getConnectedName}
            highlightedTypeVar={highlightedTypeVar}
            onTypeVarFocus={onTypeVarFocus}
            onTextFocus={onTextFocus}
            onTextBlur={onTextBlur}
            onHandleClick={onHandleClick}
            pendingConnection={pendingConnection}
            getEffectiveAllowedTypes={getEffectiveAllowedTypes}
            executionMode={executionMode}
            executionValues={executionValues}
          />
        ))}
      </div>

      {/* Outputs Section */}
      <div className="w-1/2 p-3">
        {Array.from(outputGroups.entries()).map(([groupIndex, nodes]) => (
          <NodeGroupSection
            key={groupIndex}
            groupIndex={groupIndex}
            groupLabel={nodes[0]?.label || 'Group'}
            nodes={nodes}
            direction="output"
            moduleId={moduleInstance.module_instance_id}
            template={template}
            onTypeChange={handleTypeChange}
            onNameChange={handleNameChange}
            onAddNode={onAddNode}
            onRemoveNode={onRemoveNode}
            highlightedTypeVar={highlightedTypeVar}
            onTypeVarFocus={onTypeVarFocus}
            onTextFocus={onTextFocus}
            onTextBlur={onTextBlur}
            onHandleClick={onHandleClick}
            pendingConnection={pendingConnection}
            getEffectiveAllowedTypes={getEffectiveAllowedTypes}
            executionMode={executionMode}
            executionValues={executionValues}
          />
        ))}
      </div>
    </div>
  );
}
