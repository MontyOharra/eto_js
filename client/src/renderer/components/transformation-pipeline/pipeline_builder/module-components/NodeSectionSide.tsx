import React from 'react';
import { IOSideShape, NodePin, DynamicNodeGroup } from '../../../../types/pipelineTypes';
import { NodeGroup } from './NodeGroup';

interface NodeSectionSideProps {
  side: 'input' | 'output';
  ioSideShape: IOSideShape;
  currentNodes: NodePin[];
  moduleId: string;
  onAddNode: (groupId: string) => void;
  onRemoveNode: (nodeId: string, groupId: string) => void;
  onNodeNameChange: (nodeId: string, newName: string) => void;
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
  onNodeClick,
  getConnectedOutputName,
  getTypeColor
}) => {
  // TEMPORARY: Simple organization that works with current NodePin structure
  // TODO: Update when NodePin has is_static and group_id properties
  const organizeNodesIntoGroups = () => {
    const groups: Array<{
      id: string;
      type: 'static' | 'dynamic';
      nodes: NodePin[];
      config?: DynamicNodeGroup;
    }> = [];

    // For now, treat each existing node as its own group
    // This is a simplified version to get things working
    currentNodes.forEach((node, index) => {
      groups.push({
        id: `node-${node.node_id}`,
        type: 'static', // Treat all as static for now
        nodes: [node]
      });
    });

    // Add a simple add button group if we have dynamic config
    if (ioSideShape.dynamic && Object.keys(ioSideShape.dynamic.groups).length > 0) {
      const firstGroupId = Object.keys(ioSideShape.dynamic.groups)[0];
      const firstGroupConfig = ioSideShape.dynamic.groups[firstGroupId];

      groups.push({
        id: `${firstGroupId}-add`,
        type: 'dynamic',
        nodes: [],
        config: firstGroupConfig
      });
    }

    return groups;
  };

  const groups = organizeNodesIntoGroups();

  const handleAddNode = (groupId: string) => {
    // Extract the original dynamic group ID from the group ID
    const dynamicGroupId = groupId.replace('-add', '');
    onAddNode(dynamicGroupId);
  };

  const handleRemoveNode = (nodeId: string) => {
    // Find the node to determine its group
    const node = currentNodes.find(n => n.node_id === nodeId);
    if (node) {
      const groupId = node.is_static ? `static-${node.position_index}` : node.group_id || 'unknown';
      onRemoveNode(nodeId, groupId);
    }
  };

  const canAddNodesForGroup = (group: any) => {
    if (group.type === 'static') return false;
    if (!group.config) return false;

    // Check if this is an "add" group (empty group for showing add button)
    const isAddGroup = group.id.endsWith('-add');
    return isAddGroup;
  };

  const canRemoveNodesForGroup = (group: any) => {
    if (group.type === 'static') return false;
    if (!group.config) return false;

    // Can remove if we have more than min_count nodes in the entire dynamic group
    const dynamicGroupId = group.id.split('-')[0];
    const allNodesInGroup = currentNodes.filter(
      node => !node.is_static && node.group_id === dynamicGroupId
    );

    return allNodesInGroup.length > group.config.min_count;
  };

  return (
    <div className="flex-1">
      {groups.map((group, index) => (
        <NodeGroup
          key={group.id}
          groupId={group.id}
          groupType={group.type}
          nodes={group.nodes}
          groupConfig={group.config}
          side={side}
          moduleId={moduleId}
          canAddNodes={canAddNodesForGroup(group)}
          canRemoveNodes={canRemoveNodesForGroup(group)}
          onAddNode={() => handleAddNode(group.id)}
          onRemoveNode={handleRemoveNode}
          onNodeNameChange={onNodeNameChange}
          onNodeClick={onNodeClick}
          getConnectedOutputName={getConnectedOutputName}
          getTypeColor={getTypeColor}
          isFirstGroup={index === 0}
        />
      ))}
    </div>
  );
};