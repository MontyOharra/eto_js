import React from 'react';
import { IOSideShape, NodePin, NodeSpec } from '../../../../types/pipelineTypes';
import { NodeGroup } from './NodeGroup';

interface NodeSectionSideProps {
  side: 'input' | 'output';
  ioSideShape: IOSideShape;
  currentNodes: NodePin[];
  moduleId: string;
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
  onAddNode,
  onRemoveNode,
  onNodeNameChange,
  onNodeTypeChange,
  onNodeClick,
  getConnectedOutputName,
  getTypeColor
}) => {
  // Organize nodes into groups based on backend structure
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

    let nodeIndex = 0;

    // Handle static nodes - each slot becomes its own group
    if (ioSideShape.static && ioSideShape.static.slots.length > 0) {
      ioSideShape.static.slots.forEach((slot, slotIndex) => {
        const nodesInSlot = currentNodes.slice(nodeIndex, nodeIndex + 1); // Static slots have exactly 1 node
        nodeIndex += 1;

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

    // Handle dynamic groups
    if (ioSideShape.dynamic && Object.keys(ioSideShape.dynamic.groups).length > 0) {
      Object.entries(ioSideShape.dynamic.groups).forEach(([groupId, groupConfig]) => {
        // Count remaining nodes for this group
        const remainingNodes = currentNodes.slice(nodeIndex);

        groups.push({
          id: groupId,
          label: groupConfig.item.label,
          nodes: remainingNodes, // For now, all remaining nodes go to first dynamic group
          minCount: groupConfig.min_count,
          maxCount: groupConfig.max_count,
          nodeSpec: groupConfig.item,
          isStatic: false
        });

        nodeIndex = currentNodes.length; // All remaining nodes consumed
      });
    }

    return groups;
  };

  const groups = organizeNodesIntoGroups();

  const handleAddNode = (groupId: string) => {
    onAddNode(groupId);
  };

  const handleRemoveNode = (nodeId: string) => {
    // Find which group this node belongs to
    const node = currentNodes.find(n => n.node_id === nodeId);
    if (node) {
      // For now, pass a generic group ID - this needs to be improved when NodePin has group info
      const groupId = 'dynamic-group'; // TODO: Use actual group tracking
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