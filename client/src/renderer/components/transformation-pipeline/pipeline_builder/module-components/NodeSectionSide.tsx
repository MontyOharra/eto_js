import React from 'react';
import { IOSideShape, NodePin, NodeSpec, ModuleTemplate } from '../../../../types/pipelineTypes';
import { NodeGroup } from './NodeGroup';

interface NodeSectionSideProps {
  side: 'input' | 'output';
  ioSideShape: IOSideShape;
  currentNodes: NodePin[];
  moduleId: string;
  template: ModuleTemplate; // Add template for TypeVar resolution
  onAddNode: (groupId: string) => void;
  onRemoveNode: (nodeId: string, groupId: string) => void;
  onNodeNameChange: (nodeId: string, newName: string) => void;
  onNodeTypeChange: (nodeId: string, newType: string) => void;
  onNodeClick: (nodeId: string) => void;
  getConnectedOutputName?: (nodeId: string) => string; // Only for input side
  getTypeColor: (type: string) => string;
}

export const NodeSectionSide: React.FC<NodeSectionSideProps> = ({
  side,
  ioSideShape,
  currentNodes,
  moduleId,
  template,
  onAddNode,
  onRemoveNode,
  onNodeNameChange,
  onNodeTypeChange,
  onNodeClick,
  getConnectedOutputName,
  getTypeColor
}) => {
  // Organize nodes into groups using actual node properties
  const organizeNodesIntoGroups = () => {
    const groups: Array<{
      id: string;
      label: string;
      nodes: NodePin[];
      minCount: number;
      maxCount?: number | null;
      nodeSpec: NodeSpec;
      isStatic: boolean;
    }> = [];

    // Separate static and dynamic nodes using node properties
    const staticNodes = currentNodes.filter(node =>
      (node as any).is_static === true
    );
    const dynamicNodes = currentNodes.filter(node =>
      (node as any).is_static === false
    );

    // Handle static nodes - create individual groups for each static node
    if (ioSideShape.static && ioSideShape.static.slots.length > 0) {
      ioSideShape.static.slots.forEach((slot, slotIndex) => {
        // Find the corresponding static node by position index
        const staticNode = staticNodes.find(node =>
          (node as any).position_index === slotIndex
        );
        const nodesInSlot = staticNode ? [staticNode] : [];

        groups.push({
          id: `static-${slotIndex}`,
          label: slot.label,
          nodes: nodesInSlot,
          minCount: 1, // Static nodes are required
          maxCount: 1, // Static nodes are exactly 1
          nodeSpec: slot,
          isStatic: true
        });
      });
    }

    // Handle dynamic groups - organize by group_key
    if (ioSideShape.dynamic && ioSideShape.dynamic.groups.length > 0) {
      ioSideShape.dynamic.groups.forEach((groupConfig) => {
        const groupId = groupConfig.item.label; // Use label as identifier
        // Find nodes that belong to this dynamic group
        const nodesInGroup = dynamicNodes.filter(node =>
          (node as any).group_key === groupId
        );

        groups.push({
          id: groupId,
          label: groupConfig.item.label,
          nodes: nodesInGroup,
          minCount: groupConfig.min_count,
          maxCount: groupConfig.max_count,
          nodeSpec: groupConfig.item,
          isStatic: false
        });
      });
    }

    return groups;
  };

  const groups = organizeNodesIntoGroups();

  const handleAddNode = (groupId: string) => {
    onAddNode(groupId);
  };

  const handleRemoveNode = (nodeId: string) => {
    // Find which group this node belongs to using node properties
    const node = currentNodes.find(n => n.node_id === nodeId);
    if (node) {
      // Use actual group information from node properties
      const groupId = (node as any).is_static
        ? `static-${(node as any).position_index}`
        : (node as any).group_key || 'unknown-group';
      onRemoveNode(nodeId, groupId);
    }
  };

  return (
    <div className="flex-1">
      {groups.map((group, index) => (
        <NodeGroup
          key={group.id}
          label={group.label}
          nodes={group.nodes}
          minCount={group.minCount}
          maxCount={group.maxCount}
          nodeSpec={group.nodeSpec}
          side={side}
          moduleId={moduleId}
          template={template}
          onAddNode={() => handleAddNode(group.id)}
          onRemoveNode={handleRemoveNode}
          onNodeNameChange={onNodeNameChange}
          onNodeTypeChange={onNodeTypeChange}
          onNodeClick={onNodeClick}
          getConnectedOutputName={getConnectedOutputName}
          getTypeColor={getTypeColor}
          isFirstGroup={index === 0}
          isStatic={group.isStatic}
        />
      ))}
    </div>
  );
};