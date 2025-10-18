/**
 * PipelineGraph
 * Main pipeline builder component using React Flow
 * Copied from client/src/renderer/components/transformation-pipeline/PipelineGraph.tsx
 */

import { useCallback, useState, useEffect, useRef, useMemo } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Connection,
  ConnectionLineType,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  NodeChange,
  EdgeChange,
  applyNodeChanges,
  applyEdgeChanges,
  OnConnect,
  OnNodesChange,
  OnEdgesChange,
  ReactFlowProvider,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// Component imports - update paths as needed
import { ModuleNodeNew } from './pipeline-graph/ModuleNodeNew';
import { EntryPointNode } from './pipeline-graph/EntryPointNode';
import { ModuleSelectorPane } from './ModuleSelectorPane';

// Type imports - these will need to be imported from your types directory
import type { ModuleTemplate, ModuleInstance, NodePin } from '../../../../../types/moduleTypes';
import type { EntryPoint, PipelineConnection } from '../../../../../types/pipelineTypes';

// Node type registry
const nodeTypes = {
  moduleNode: ModuleNodeNew,
  entryPointNode: EntryPointNode,
};

interface PipelineGraphProps {
  modules: ModuleTemplate[];
  initialModuleInstances?: ModuleInstance[];
  initialEntryPoints?: EntryPoint[];
  initialConnections?: PipelineConnection[];
  initialPositions?: Record<string, { x: number; y: number }>;
  viewOnly?: boolean;
  onStateChange?: (state: {
    moduleInstances: ModuleInstance[];
    entryPoints: EntryPoint[];
    connections: PipelineConnection[];
    positions: Record<string, { x: number; y: number }>;
  }) => void;
}

function PipelineGraphInner({
  modules,
  initialModuleInstances = [],
  initialEntryPoints = [],
  initialConnections = [],
  initialPositions = {},
  viewOnly = false,
  onStateChange,
}: PipelineGraphProps) {
  const reactFlowInstance = useReactFlow();
  const [moduleInstances, setModuleInstances] = useState<ModuleInstance[]>(initialModuleInstances);
  const [pipelineConnections, setPipelineConnections] = useState<PipelineConnection[]>(initialConnections);
  const [nodePositions, setNodePositions] = useState<Record<string, { x: number; y: number }>>(initialPositions);

  // Use entry points from props (driven by extraction fields)
  const entryPoints = initialEntryPoints;

  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);
  const [pendingConnection, setPendingConnection] = useState<{
    sourceHandleId: string;
    sourceNodeId: string;
    handleType: 'source' | 'target';
  } | null>(null);
  const [isTextFocused, setIsTextFocused] = useState(false);

  // Handle node position changes
  const handleNodesChange = useCallback((changes: NodeChange[]) => {
    changes.forEach((change) => {
      if (change.type === 'position' && change.position) {
        setNodePositions((prev) => ({
          ...prev,
          [change.id]: change.position!,
        }));
      }
    });
  }, []);

  // Handle module deletion
  const handleDeleteModule = useCallback((moduleId: string) => {
    setModuleInstances((prev) => prev.filter((m) => m.module_instance_id !== moduleId));

    // Remove connections involving this module
    setPipelineConnections((prev) =>
      prev.filter((conn) => conn.source_node_id !== moduleId && conn.target_node_id !== moduleId)
    );

    // Remove position
    setNodePositions((prev) => {
      const { [moduleId]: _, ...rest } = prev;
      return rest;
    });
  }, []);

  // Handle node updates (name, type changes)
  const handleUpdateNode = useCallback((moduleId: string, nodeId: string, updates: Partial<NodePin>) => {
    setModuleInstances((prev) =>
      prev.map((instance) => {
        if (instance.module_instance_id !== moduleId) return instance;

        return {
          ...instance,
          inputs: instance.inputs.map((node) =>
            node.node_id === nodeId ? { ...node, ...updates } : node
          ),
          outputs: instance.outputs.map((node) =>
            node.node_id === nodeId ? { ...node, ...updates } : node
          ),
        };
      })
    );
  }, []);

  // Handle adding new node to a module
  const handleAddNode = useCallback((moduleId: string, direction: 'input' | 'output', groupIndex: number) => {
    setModuleInstances((prev) =>
      prev.map((instance) => {
        if (instance.module_instance_id !== moduleId) return instance;

        const template = modules.find((m) => m.id === instance.module_id);
        if (!template) return instance;

        const ioShape = direction === 'input'
          ? template.meta?.io_shape?.inputs
          : template.meta?.io_shape?.outputs;

        const nodeGroup = ioShape?.nodes[groupIndex];
        if (!nodeGroup) return instance;

        const existingNodes = direction === 'input' ? instance.inputs : instance.outputs;
        const groupNodes = existingNodes.filter((n) => n.group_index === groupIndex);

        const newNode: NodePin = {
          node_id: `${moduleId}_${direction}_${groupIndex}_${Date.now()}`,
          name: '',
          type: nodeGroup.default_type || 'str',
          allowed_types: nodeGroup.allowed_types,
          group_index: groupIndex,
          label: nodeGroup.label,
          type_var: nodeGroup.type_var,
        };

        return {
          ...instance,
          [direction === 'input' ? 'inputs' : 'outputs']: [...existingNodes, newNode],
        };
      })
    );
  }, [modules]);

  // Handle removing a node
  const handleRemoveNode = useCallback((moduleId: string, nodeId: string) => {
    setModuleInstances((prev) =>
      prev.map((instance) => {
        if (instance.module_instance_id !== moduleId) return instance;

        return {
          ...instance,
          inputs: instance.inputs.filter((n) => n.node_id !== nodeId),
          outputs: instance.outputs.filter((n) => n.node_id !== nodeId),
        };
      })
    );

    // Remove connections involving this node
    setPipelineConnections((prev) =>
      prev.filter((conn) => conn.source_pin_id !== nodeId && conn.target_pin_id !== nodeId)
    );
  }, []);

  // Handle config changes
  const handleConfigChange = useCallback((moduleId: string, configKey: string, value: any) => {
    setModuleInstances((prev) =>
      prev.map((instance) => {
        if (instance.module_instance_id !== moduleId) return instance;

        return {
          ...instance,
          config: {
            ...instance.config,
            [configKey]: value,
          },
        };
      })
    );
  }, []);

  // Handle click-to-connect
  const handleHandleClick = useCallback((nodeId: string, handleId: string, handleType: 'source' | 'target') => {
    if (!pendingConnection) {
      // Start a new connection
      setPendingConnection({ sourceHandleId: handleId, sourceNodeId: nodeId, handleType });
    } else {
      // Complete the connection
      if (pendingConnection.handleType !== handleType) {
        const source = handleType === 'source' ? handleId : pendingConnection.sourceHandleId;
        const target = handleType === 'target' ? handleId : pendingConnection.sourceHandleId;
        const sourceNodeId = handleType === 'source' ? nodeId : pendingConnection.sourceNodeId;
        const targetNodeId = handleType === 'target' ? nodeId : pendingConnection.sourceNodeId;

        const newConnection: PipelineConnection = {
          connection_id: `conn_${Date.now()}`,
          source_node_id: sourceNodeId,
          target_node_id: targetNodeId,
          source_pin_id: source,
          target_pin_id: target,
        };

        setPipelineConnections((prev) => [...prev, newConnection]);
      }

      setPendingConnection(null);
    }
  }, [pendingConnection]);

  // Get effective allowed types for a pin based on connections
  const getEffectiveAllowedTypes = useCallback((moduleId: string, pinId: string, baseAllowedTypes: string[]) => {
    // Find connections to this pin
    const connection = pipelineConnections.find(
      (conn) => conn.target_pin_id === pinId || conn.source_pin_id === pinId
    );

    if (!connection) return baseAllowedTypes;

    // Find the connected pin's type
    const connectedPinId = connection.target_pin_id === pinId ? connection.source_pin_id : connection.target_pin_id;
    const connectedModuleId = connection.target_pin_id === pinId ? connection.source_node_id : connection.target_node_id;

    // Check if it's an entry point
    const entryPoint = entryPoints.find((ep) => ep.node_id === connectedPinId);
    if (entryPoint) {
      return [entryPoint.type];
    }

    // Find the connected module and pin
    const connectedModule = moduleInstances.find((m) => m.module_instance_id === connectedModuleId);
    if (!connectedModule) return baseAllowedTypes;

    const connectedPin = [...connectedModule.inputs, ...connectedModule.outputs].find(
      (p) => p.node_id === connectedPinId
    );

    if (!connectedPin) return baseAllowedTypes;

    // Return only the connected pin's type
    return [connectedPin.type];
  }, [pipelineConnections, entryPoints, moduleInstances]);

  // Get connected output name for an input pin
  const getConnectedOutputName = useCallback((moduleId: string, inputPinId: string) => {
    const connection = pipelineConnections.find((conn) => conn.target_pin_id === inputPinId);
    if (!connection) return undefined;

    // Check if it's an entry point
    const entryPoint = entryPoints.find((ep) => ep.node_id === connection.source_pin_id);
    if (entryPoint) {
      return entryPoint.name;
    }

    // Find the source module and pin
    const sourceModule = moduleInstances.find((m) => m.module_instance_id === connection.source_node_id);
    if (!sourceModule) return undefined;

    const sourcePin = sourceModule.outputs.find((p) => p.node_id === connection.source_pin_id);
    return sourcePin?.name;
  }, [pipelineConnections, entryPoints, moduleInstances]);

  // Handle drag and drop from module selector
  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const data = event.dataTransfer.getData('application/reactflow');
      if (!data) return;

      const { moduleId } = JSON.parse(data);
      const template = modules.find((m) => m.id === moduleId);
      if (!template) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const instanceId = `${moduleId}_${Date.now()}`;

      // Create initial inputs and outputs based on template io_shape
      const inputs: NodePin[] = [];
      const outputs: NodePin[] = [];

      if (template.meta?.io_shape?.inputs) {
        template.meta.io_shape.inputs.nodes.forEach((nodeGroup, groupIndex) => {
          for (let i = 0; i < nodeGroup.min_count; i++) {
            inputs.push({
              node_id: `${instanceId}_input_${groupIndex}_${i}`,
              name: '',
              type: nodeGroup.default_type || 'str',
              allowed_types: nodeGroup.allowed_types,
              group_index: groupIndex,
              label: nodeGroup.label,
              type_var: nodeGroup.type_var,
            });
          }
        });
      }

      if (template.meta?.io_shape?.outputs) {
        template.meta.io_shape.outputs.nodes.forEach((nodeGroup, groupIndex) => {
          for (let i = 0; i < nodeGroup.min_count; i++) {
            outputs.push({
              node_id: `${instanceId}_output_${groupIndex}_${i}`,
              name: '',
              type: nodeGroup.default_type || 'str',
              allowed_types: nodeGroup.allowed_types,
              group_index: groupIndex,
              label: nodeGroup.label,
              type_var: nodeGroup.type_var,
            });
          }
        });
      }

      const newInstance: ModuleInstance = {
        module_instance_id: instanceId,
        module_id: moduleId,
        inputs,
        outputs,
        config: {},
      };

      setModuleInstances((prev) => [...prev, newInstance]);
      setNodePositions((prev) => ({ ...prev, [instanceId]: position }));
    },
    [reactFlowInstance, modules]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Convert module instances and entry points to React Flow nodes
  const nodes = useMemo(() => {
    const moduleNodes: Node[] = moduleInstances.map((instance) => {
      const template = modules.find((m) => m.id === instance.module_id);
      if (!template) return null;

      const position = nodePositions[instance.module_instance_id] || { x: 0, y: 0 };

      return {
        id: instance.module_instance_id,
        type: 'moduleNode',
        position,
        data: {
          moduleInstance: instance,
          template,
          onDeleteModule: handleDeleteModule,
          onUpdateNode: handleUpdateNode,
          onAddNode: handleAddNode,
          onRemoveNode: handleRemoveNode,
          onConfigChange: handleConfigChange,
          onTextFocus: () => setIsTextFocused(true),
          onTextBlur: () => setIsTextFocused(false),
          onHandleClick: handleHandleClick,
          pendingConnection,
          getEffectiveAllowedTypes,
          getConnectedOutputName,
        },
      };
    }).filter(Boolean) as Node[];

    const entryPointNodes: Node[] = entryPoints.map((entryPoint) => {
      const position = nodePositions[entryPoint.node_id] || { x: 0, y: 0 };

      return {
        id: entryPoint.node_id,
        type: 'entryPointNode',
        position,
        data: {
          entryPoint,
          onHandleClick: handleHandleClick,
        },
      };
    });

    return [...moduleNodes, ...entryPointNodes];
  }, [moduleInstances, entryPoints, modules, nodePositions, pendingConnection]);

  // Convert pipeline connections to React Flow edges
  const edges = useMemo(() => {
    return pipelineConnections.map((conn) => ({
      id: conn.connection_id,
      source: conn.source_node_id,
      target: conn.target_node_id,
      sourceHandle: conn.source_pin_id,
      targetHandle: conn.target_pin_id,
      type: 'default',
      animated: false,
    }));
  }, [pipelineConnections]);

  // Notify parent of state changes
  useEffect(() => {
    if (onStateChange) {
      onStateChange({
        moduleInstances,
        entryPoints,
        connections: pipelineConnections,
        positions: nodePositions,
      });
    }
  }, [moduleInstances, entryPoints, pipelineConnections, nodePositions, onStateChange]);

  return (
    <div className="h-full w-full flex">
      {!viewOnly && (
        <ModuleSelectorPane
          modules={modules}
          selectedModuleId={selectedModuleId}
          onModuleSelect={setSelectedModuleId}
        />
      )}

      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={handleNodesChange}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={nodeTypes}
          connectionLineType={ConnectionLineType.Bezier}
          fitView
          nodesDraggable={!viewOnly}
          nodesConnectable={!viewOnly}
          elementsSelectable={!viewOnly}
          deleteKeyCode={isTextFocused ? null : 'Delete'}
        >
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>
    </div>
  );
}

export function PipelineGraph(props: PipelineGraphProps) {
  return (
    <ReactFlowProvider>
      <PipelineGraphInner {...props} />
    </ReactFlowProvider>
  );
}
