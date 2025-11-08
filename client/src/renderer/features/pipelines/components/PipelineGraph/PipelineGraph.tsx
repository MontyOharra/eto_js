/**
 * PipelineGraph
 * Interactive pipeline editor and viewer with support for:
 * - View mode: Read-only visualization with pan/zoom and config expansion
 * - Edit mode: Full editing capabilities (add/remove modules, edit connections, etc.)
 */

import { useCallback, useState, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  Background,
  ReactFlowProvider,
  useReactFlow,
  BackgroundVariant,
  NodeChange,
  EdgeChange,
  Connection,
  applyNodeChanges,
  applyEdgeChanges,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { PipelineState, VisualState, EntryPoint, NodePin } from '../../types';
import type { ModuleTemplate } from '../../../modules/types';
import {
  createModuleInstance,
  addPinToModule,
  removePinFromModule,
  updatePinInModule,
} from '../../utils/moduleFactory';
import { getTypeColor } from '../../utils/edgeUtils';
import { findPinInPipeline, synchronizeTypeVarUpdate, pinsCanConnect } from '../../utils/moduleUtils';
import { calculateNewEntryPointPosition } from '../../utils/layoutUtils';
import { Module } from './Module';
import { EntryPoint as EntryPointComponent } from './EntryPoint';

interface PipelineGraphProps {
  pipelineState?: PipelineState;
  visualState?: VisualState;
  entryPoints?: EntryPoint[]; // External entry points (overrides pipelineState.entry_points)
  mode?: 'view' | 'edit';
  modules?: ModuleTemplate[];
  selectedModuleId?: string | null;
  onModulePlaced?: () => void;
  onPipelineStateChange?: (newState: PipelineState) => void;
  onVisualStateChange?: (newState: VisualState) => void;
}

const nodeTypes = {
  module: Module,
  entryPoint: EntryPointComponent,
};

const edgeTypes = {
  // TODO: Add custom edge types
};

function PipelineGraphInner({
  pipelineState,
  visualState,
  entryPoints,
  mode = 'view',
  modules = [],
  selectedModuleId,
  onModulePlaced,
  onPipelineStateChange,
  onVisualStateChange,
}: PipelineGraphProps) {
  const { fitView, screenToFlowPosition } = useReactFlow();

  // Internal state - React Flow manages positions
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  // Use external entry points if provided, otherwise use pipelineState.entry_points
  // Memoized to prevent unnecessary re-renders
  const effectiveEntryPoints = useMemo(
    () => entryPoints ?? pipelineState?.entry_points ?? [],
    [entryPoints, pipelineState?.entry_points]
  );

  // Helper to find a pin by its node_id
  const findPin = useCallback(
    (nodeId: string): NodePin | undefined => {
      if (!pipelineState) return undefined;
      return findPinInPipeline(nodeId, effectiveEntryPoints, pipelineState.modules);
    },
    [pipelineState, effectiveEntryPoints]
  );

  // Handle updating a node (type or name change)
  const handleUpdateNode = useCallback(
    (moduleId: string, nodeId: string, updates: Partial<NodePin>) => {
      if (!pipelineState || !onPipelineStateChange) return;

      // Find the module to update
      const moduleIndex = pipelineState.modules.findIndex(
        (m) => m.module_instance_id === moduleId
      );
      if (moduleIndex === -1) return;

      const module = pipelineState.modules[moduleIndex];

      // Handle type changes with type_var synchronization
      let updatedModule = module;
      if (updates.type) {
        const result = synchronizeTypeVarUpdate(module, nodeId, updates.type);
        updatedModule = result.updatedModule;
      } else {
        // Non-type update (e.g., name change)
        updatedModule = updatePinInModule(module, nodeId, updates);
      }

      // Update pipeline state
      const updatedModules = [...pipelineState.modules];
      updatedModules[moduleIndex] = updatedModule;

      onPipelineStateChange({
        ...pipelineState,
        modules: updatedModules,
      });
    },
    [pipelineState, onPipelineStateChange]
  );

  // Handle adding a new node to a module
  const handleAddNode = useCallback(
    (moduleId: string, direction: 'input' | 'output', groupIndex: number) => {
      if (!pipelineState || !onPipelineStateChange) return;

      // Find the module to update
      const moduleIndex = pipelineState.modules.findIndex(
        (m) => m.module_instance_id === moduleId
      );
      if (moduleIndex === -1) return;

      const module = pipelineState.modules[moduleIndex];
      const template = modules.find((t) => t.id === module.module_ref.split(':')[0]);
      if (!template) return;

      const updatedModule = addPinToModule(module, template, direction, groupIndex);

      // Update pipeline state
      const updatedModules = [...pipelineState.modules];
      updatedModules[moduleIndex] = updatedModule;

      onPipelineStateChange({
        ...pipelineState,
        modules: updatedModules,
      });
    },
    [pipelineState, onPipelineStateChange, modules]
  );

  // Handle removing a node from a module
  const handleRemoveNode = useCallback(
    (moduleId: string, nodeId: string) => {
      if (!pipelineState || !onPipelineStateChange) return;

      // Find the module to update
      const moduleIndex = pipelineState.modules.findIndex(
        (m) => m.module_instance_id === moduleId
      );
      if (moduleIndex === -1) return;

      const module = pipelineState.modules[moduleIndex];
      const updatedModule = removePinFromModule(module, nodeId);

      // Update pipeline state
      const updatedModules = [...pipelineState.modules];
      updatedModules[moduleIndex] = updatedModule;

      onPipelineStateChange({
        ...pipelineState,
        modules: updatedModules,
      });

      // TODO: Also remove any connections involving this node
    },
    [pipelineState, onPipelineStateChange]
  );

  // Handle deleting an entire module
  const handleDeleteModule = useCallback(
    (moduleId: string) => {
      if (!pipelineState || !onPipelineStateChange || !onVisualStateChange) return;

      // Remove module from pipeline state
      const updatedModules = pipelineState.modules.filter(
        (m) => m.module_instance_id !== moduleId
      );

      onPipelineStateChange({
        ...pipelineState,
        modules: updatedModules,
      });

      // Remove from visual state
      const updatedVisualState = { ...visualState };
      delete updatedVisualState[moduleId];
      onVisualStateChange(updatedVisualState);

      // TODO: Also remove any connections involving this module
    },
    [pipelineState, visualState, onPipelineStateChange, onVisualStateChange]
  );

  // Initialize/update nodes when pipeline state or modules change
  useEffect(() => {
    if (!pipelineState) {
      setNodes([]);
      return;
    }

    const newNodes: Node[] = [];

    // Create entry point nodes from effectiveEntryPoints
    effectiveEntryPoints.forEach((entryPoint) => {
      newNodes.push({
        id: entryPoint.entry_point_id,
        type: 'entryPoint',
        position: visualState?.[entryPoint.entry_point_id] || calculateNewEntryPointPosition(newNodes),
        data: {
          entryPoint,
        },
        draggable: mode === 'edit',
      });
    });

    // Create module nodes
    pipelineState.modules.forEach((moduleInstance) => {
      // Find the template for this module
      const [templateId] = moduleInstance.module_ref.split(':');
      const template = modules.find((t) => t.id === templateId);

      // Skip if template not found
      if (!template) {
        console.warn(`Template not found for module: ${moduleInstance.module_ref}`);
        return;
      }

      newNodes.push({
        id: moduleInstance.module_instance_id,
        type: 'module',
        position: visualState?.[moduleInstance.module_instance_id] || { x: 0, y: 0 },
        data: {
          moduleInstance,
          template,
          // Edit callbacks
          onDeleteModule: mode === 'edit' ? handleDeleteModule : undefined,
          onUpdateNode: mode === 'edit' ? handleUpdateNode : undefined,
          onAddNode: mode === 'edit' ? handleAddNode : undefined,
          onRemoveNode: mode === 'edit' ? handleRemoveNode : undefined,
        },
        draggable: mode === 'edit',
      });
    });

    setNodes(newNodes);
  }, [pipelineState, visualState, modules, mode, effectiveEntryPoints, handleDeleteModule, handleUpdateNode, handleAddNode, handleRemoveNode]);

  // Initialize/update edges when pipeline state changes
  useEffect(() => {
    if (!pipelineState) {
      setEdges([]);
      return;
    }

    // Create edges from connections
    const newEdges: Edge[] = pipelineState.connections.map((connection, index) => {
      // Find source and target nodes by searching for pins
      let sourceNodeId = '';
      let targetNodeId = '';

      // Check entry points for source
      effectiveEntryPoints.forEach((ep) => {
        if (ep.outputs.some((out) => out.node_id === connection.from_node_id)) {
          sourceNodeId = ep.entry_point_id;
        }
      });

      // Check modules for source/target
      pipelineState.modules.forEach((module) => {
        if (module.outputs.some((out) => out.node_id === connection.from_node_id)) {
          sourceNodeId = module.module_instance_id;
        }
        if (module.inputs.some((inp) => inp.node_id === connection.to_node_id)) {
          targetNodeId = module.module_instance_id;
        }
      });

      // Get the source pin to determine edge color
      const sourcePin = findPin(connection.from_node_id);
      const edgeColor = sourcePin ? getTypeColor(sourcePin.type) : '#6B7280';

      return {
        id: `${connection.from_node_id}-${connection.to_node_id}`,
        source: sourceNodeId,
        target: targetNodeId,
        sourceHandle: connection.from_node_id,
        targetHandle: connection.to_node_id,
        type: 'default',
        reconnectable: mode === 'edit',
        style: {
          stroke: edgeColor,
          strokeWidth: 2,
        },
        data: {
          sourcePin,
        },
      };
    });

    setEdges(newEdges);
  }, [pipelineState, mode, effectiveEntryPoints, findPin]);

  // Handle node position changes
  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      if (mode === 'view') return; // Ignore in view mode

      // Apply changes to internal node state (enables smooth dragging)
      setNodes((nds) => applyNodeChanges(changes, nds));

      // Only update visual state when drag ends (for persistence)
      const isDragEnd = changes.some(
        (change) => change.type === 'position' && change.dragging === false
      );

      if (isDragEnd && onVisualStateChange) {
        // Extract final positions from changes
        setNodes((currentNodes) => {
          const updatedVisualState = { ...visualState };

          currentNodes.forEach((node) => {
            updatedVisualState[node.id] = node.position;
          });

          onVisualStateChange(updatedVisualState);
          return currentNodes;
        });
      }
    },
    [mode, visualState, onVisualStateChange]
  );

  // Handle edge changes
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      if (mode === 'view') return; // Ignore in view mode

      // Apply changes to internal edge state and update selection styling
      setEdges((eds) => {
        const updatedEdges = applyEdgeChanges(changes, eds);

        // Update styling based on selection
        return updatedEdges.map((edge) => ({
          ...edge,
          animated: edge.selected || false,
          className: edge.selected ? 'selected-edge' : '',
        }));
      });

      // Handle edge deletion
      if (pipelineState && onPipelineStateChange) {
        const removedEdges = changes.filter((c) => c.type === 'remove');
        if (removedEdges.length > 0) {
          const edgeIdsToRemove = removedEdges.map((c) => (c as any).id);
          const updatedConnections = pipelineState.connections.filter((conn) => {
            const edgeId = `${conn.from_node_id}-${conn.to_node_id}`;
            return !edgeIdsToRemove.includes(edgeId);
          });

          onPipelineStateChange({
            ...pipelineState,
            connections: updatedConnections,
          });
        }
      }
    },
    [mode, pipelineState, onPipelineStateChange]
  );

  // Validate connection based on shared allowed types
  const isValidConnection = useCallback(
    (connection: Connection) => {
      if (!connection.sourceHandle || !connection.targetHandle) return false;

      const sourcePin = findPin(connection.sourceHandle);
      const targetPin = findPin(connection.targetHandle);

      if (!sourcePin || !targetPin) return false;

      // Check if pins can connect (share at least one allowed type)
      return pinsCanConnect(sourcePin, targetPin);
    },
    [findPin]
  );

  // Handle new connections
  const onConnect = useCallback(
    (connection: Connection) => {
      if (mode === 'view' || !pipelineState || !onPipelineStateChange) return;
      if (!connection.source || !connection.target || !connection.sourceHandle || !connection.targetHandle) return;

      const sourceHandle = connection.sourceHandle;
      const targetHandle = connection.targetHandle;

      // Check if this exact connection already exists (prevent duplicates)
      const isDuplicate = pipelineState.connections.some(
        (conn) => conn.from_node_id === sourceHandle && conn.to_node_id === targetHandle
      );
      if (isDuplicate) return;

      // Remove any existing connections from this source or to this target (enforce 1-to-1)
      const updatedConnections = pipelineState.connections.filter(
        (conn) => conn.from_node_id !== sourceHandle && conn.to_node_id !== targetHandle
      );

      // Create new connection
      const newConnection = {
        from_node_id: sourceHandle,
        to_node_id: targetHandle,
      };

      // Add to pipeline state
      onPipelineStateChange({
        ...pipelineState,
        connections: [...updatedConnections, newConnection],
      });
    },
    [mode, pipelineState, onPipelineStateChange]
  );

  // Handle edge reconnection
  const onReconnect = useCallback(
    (oldEdge: Edge, newConnection: Connection) => {
      if (mode === 'view' || !pipelineState || !onPipelineStateChange) return;
      if (!newConnection.source || !newConnection.target || !newConnection.sourceHandle || !newConnection.targetHandle) return;

      const newSourceHandle = newConnection.sourceHandle;
      const newTargetHandle = newConnection.targetHandle;

      // Check if this exact connection already exists (prevent duplicates)
      const isDuplicate = pipelineState.connections.some(
        (conn) => conn.from_node_id === newSourceHandle && conn.to_node_id === newTargetHandle
      );
      if (isDuplicate) return;

      // Remove old connection
      let updatedConnections = pipelineState.connections.filter(
        (conn) => !(conn.from_node_id === oldEdge.sourceHandle && conn.to_node_id === oldEdge.targetHandle)
      );

      // Remove any existing connections that would conflict with new connection (enforce 1-to-1)
      updatedConnections = updatedConnections.filter(
        (conn) => conn.from_node_id !== newSourceHandle && conn.to_node_id !== newTargetHandle
      );

      const newConn = {
        from_node_id: newSourceHandle,
        to_node_id: newTargetHandle,
      };

      onPipelineStateChange({
        ...pipelineState,
        connections: [...updatedConnections, newConn],
      });
    },
    [mode, pipelineState, onPipelineStateChange]
  );

  // Handle drag over to enable drop
  const onDragOver = useCallback(
    (event: React.DragEvent) => {
      if (mode === 'view') return;
      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';
    },
    [mode]
  );

  // Handle module drop from selector pane
  const onDrop = useCallback(
    (event: React.DragEvent) => {
      if (mode === 'view' || !pipelineState || !onPipelineStateChange || !onVisualStateChange) return;

      event.preventDefault();

      const data = event.dataTransfer.getData('application/reactflow');
      if (!data) return;

      const { moduleId } = JSON.parse(data);
      const template = modules.find((t) => t.id === moduleId);
      if (!template) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      // Create new module instance
      const newModule = createModuleInstance(template);

      // Add module to pipeline state
      const updatedPipelineState: PipelineState = {
        ...pipelineState,
        modules: [...pipelineState.modules, newModule],
      };

      // Add position to visual state
      const updatedVisualState: VisualState = {
        ...visualState,
        [newModule.module_instance_id]: position,
      };

      // Create new node for immediate rendering
      const newNode: Node = {
        id: newModule.module_instance_id,
        type: 'module',
        position,
        data: {
          moduleInstance: newModule,
          template,
        },
        draggable: mode === 'edit',
      };

      // Add to internal nodes state immediately (for smooth rendering)
      setNodes((nds) => [...nds, newNode]);

      // Update parent states (for persistence)
      onPipelineStateChange(updatedPipelineState);
      onVisualStateChange(updatedVisualState);

      onModulePlaced?.();
    },
    [mode, modules, screenToFlowPosition, pipelineState, visualState, onPipelineStateChange, onVisualStateChange, onModulePlaced]
  );

  // Show message if no pipeline state provided
  if (!pipelineState) {
    return (
      <div className="w-full h-full bg-gray-900 flex items-center justify-center">
        <div className="text-gray-400">No pipeline data provided</div>
      </div>
    );
  }

  return (
    <>
      <style>{`
        .selected-edge path {
          stroke-dasharray: 5 5;
          filter: drop-shadow(0 0 8px currentColor);
        }
      `}</style>
      <div
        className="w-full h-full bg-gray-900"
        onDragOver={onDragOver}
        onDrop={onDrop}
      >
        <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onReconnect={onReconnect}
        isValidConnection={isValidConnection}
        nodesDraggable={mode === 'edit'}
        nodesConnectable={mode === 'edit'}
        elementsSelectable={mode === 'edit'}
        edgesReconnectable={mode === 'edit'}
        reconnectRadius={20}
        panOnDrag={true}
        zoomOnScroll={true}
        minZoom={0.1}
        maxZoom={4}
        fitView
        fitViewOptions={{
          padding: 0.2,
          maxZoom: 1,
        }}
        >
            <Controls />
            <Background variant={BackgroundVariant.Dots} />
        </ReactFlow>
        </div>
    </>
  );
}

export function PipelineGraph(props: PipelineGraphProps) {
  return (
    <ReactFlowProvider>
      <PipelineGraphInner {...props} />
    </ReactFlowProvider>
  );
}
