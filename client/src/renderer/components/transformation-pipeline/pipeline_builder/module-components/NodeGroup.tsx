import React from 'react';
import { NodePin, NodeSpec, ModuleTemplate } from '../../../../types/pipelineTypes';
import { NodeComponent } from './NodeComponent';
import { AddNodeButton } from './AddNodeButton';

interface NodeGroupProps {
  label: string; // From NodeSpec.label
  nodes: NodePin[];
  minCount: number;
  maxCount?: number | null;
  nodeSpec: NodeSpec; // The template spec for this group
  side: 'input' | 'output';
  moduleId: string;
  template: ModuleTemplate; // Add template for TypeVar resolution
  activeTypeVar: string | null; // Currently active TypeVar for highlighting
  onTypeVarFocus: (typeVar: string | undefined) => void; // When TypeVar dropdown is focused
  onTypeVarBlur: () => void; // When TypeVar dropdown is blurred
  onAddNode: () => void;
  onRemoveNode: (nodeId: string) => void;
  onNodeNameChange: (nodeId: string, newName: string) => void;
  onNodeTypeChange: (nodeId: string, newType: string) => void;
  onNodeClick: (nodeId: string) => void;
  getConnectedOutputName?: (nodeId: string) => string; // Only for input side
  getTypeColor: (type: string) => string;
  isFirstGroup: boolean;
  isStatic: boolean; // Whether this is a static group (always shows label)
}

export const NodeGroup: React.FC<NodeGroupProps> = ({
  label,
  nodes,
  minCount,
  maxCount,
  nodeSpec,
  side,
  moduleId,
  template,
  activeTypeVar,
  onTypeVarFocus,
  onTypeVarBlur,
  onAddNode,
  onRemoveNode,
  onNodeNameChange,
  onNodeTypeChange,
  onNodeClick,
  getConnectedOutputName,
  getTypeColor,
  isFirstGroup,
  isStatic
}) => {
  const canAddNodes = maxCount ? nodes.length < maxCount : true;
  const canRemoveNodes = nodes.length > minCount;

  return (
    <div>
      {/* Group label separator */}
      {(isStatic || !isFirstGroup) && (
        <div className="pt-1 pb-1 px-3">
          <div className="flex items-center">
            <div className="flex-1 h-px bg-gray-600"></div>
            <span className="px-2 text-xs text-gray-400 font-bold bg-gray-800">{label}</span>
            <div className="flex-1 h-px bg-gray-600"></div>
          </div>
        </div>
      )}

      {/* Render nodes in this group (no borders between individual nodes) */}
      {nodes.map((node) => (
        <NodeComponent
          key={node.node_id}
          node={node}
          nodeSpec={nodeSpec}
          side={side}
          moduleId={moduleId}
          template={template}
          activeTypeVar={activeTypeVar}
          onTypeVarFocus={onTypeVarFocus}
          onTypeVarBlur={onTypeVarBlur}
          canRemove={canRemoveNodes}
          onRemove={() => onRemoveNode(node.node_id)}
          onNameChange={(newName) => onNodeNameChange(node.node_id, newName)}
          onTypeChange={(newType) => onNodeTypeChange(node.node_id, newType)}
          onClick={() => onNodeClick(node.node_id)}
          connectedOutputName={getConnectedOutputName?.(node.node_id)}
          getTypeColor={getTypeColor}
        />
      ))}

      {/* Add button for groups that can accept more nodes */}
      {canAddNodes && (
        <AddNodeButton
          side={side}
          onAdd={onAddNode}
          disabled={false}
        />
      )}
    </div>
  );
};