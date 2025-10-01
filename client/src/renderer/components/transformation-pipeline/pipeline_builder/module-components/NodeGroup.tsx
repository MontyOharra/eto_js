import React from 'react';
import { NodePin, DynamicNodeGroup } from '../../../../types/pipelineTypes';
import { NodeComponent } from './NodeComponent';
import { AddNodeButton } from './AddNodeButton';
import { GroupSeparator } from './GroupSeparator';

interface NodeGroupProps {
  groupId: string;
  groupType: 'static' | 'dynamic';
  nodes: NodePin[];
  groupConfig?: DynamicNodeGroup; // Only for dynamic groups
  side: 'input' | 'output';
  moduleId: string;
  canAddNodes: boolean;
  canRemoveNodes: boolean;
  onAddNode: () => void;
  onRemoveNode: (nodeId: string) => void;
  onNodeNameChange: (nodeId: string, newName: string) => void;
  onNodeClick: (nodeId: string) => void;
  getConnectedOutputName?: (nodeId: string) => string; // Only for input side
  getTypeColor: (type: string) => string;
  isFirstGroup: boolean;
}

export const NodeGroup: React.FC<NodeGroupProps> = ({
  groupId,
  groupType,
  nodes,
  groupConfig,
  side,
  moduleId,
  canAddNodes,
  canRemoveNodes,
  onAddNode,
  onRemoveNode,
  onNodeNameChange,
  onNodeClick,
  getConnectedOutputName,
  getTypeColor,
  isFirstGroup
}) => {
  const handleNodeRemove = (nodeId: string) => {
    onRemoveNode(nodeId);
  };

  const handleNodeNameChange = (nodeId: string, newName: string) => {
    onNodeNameChange(nodeId, newName);
  };

  const handleNodeClick = (nodeId: string) => {
    onNodeClick(nodeId);
  };

  // Determine if we can remove nodes from this specific group
  const canRemoveFromGroup = canRemoveNodes && groupType === 'dynamic' && groupConfig && nodes.length > groupConfig.min_count;

  return (
    <>
      {/* Group separator (not shown for first group) */}
      <GroupSeparator
        groupLabel={groupType === 'dynamic' ? groupConfig?.label : undefined}
        isFirst={isFirstGroup}
      />

      {/* Render nodes in this group */}
      {nodes.map((node) => (
        <NodeComponent
          key={node.node_id}
          node={node}
          side={side}
          moduleId={moduleId}
          canRemove={canRemoveFromGroup}
          onRemove={() => handleNodeRemove(node.node_id)}
          onNameChange={(newName) => handleNodeNameChange(node.node_id, newName)}
          onClick={() => handleNodeClick(node.node_id)}
          connectedOutputName={getConnectedOutputName?.(node.node_id)}
          getTypeColor={getTypeColor}
        />
      ))}

      {/* Add button for dynamic groups that can accept more nodes */}
      {groupType === 'dynamic' && canAddNodes && groupConfig && nodes.length < groupConfig.max_count && (
        <AddNodeButton
          side={side}
          onAdd={onAddNode}
        />
      )}
    </>
  );
};