/**
 * PipelineGraph
 * Interactive pipeline editor and viewer with support for:
 * - View mode: Read-only visualization with pan/zoom and config expansion
 * - Edit mode: Full editing capabilities (add/remove modules, edit connections, etc.)
 */

import { useCallback, useMemo } from 'react';
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
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { PipelineState, VisualState } from '../../types';

interface PipelineGraphProps {
  pipelineState?: PipelineState;
  visualState?: VisualState;
  mode?: 'view' | 'edit';
  onPipelineStateChange?: (newState: PipelineState) => void;
  onVisualStateChange?: (newState: VisualState) => void;
}

const nodeTypes = {
  // TODO: Add custom node types (module, entryPoint)
};

const edgeTypes = {
  // TODO: Add custom edge types
};

function PipelineGraphInner({
  pipelineState,
  visualState,
  mode = 'view',
  onPipelineStateChange,
  onVisualStateChange,
}: PipelineGraphProps) {
  const { fitView } = useReactFlow();

  // Convert pipeline state to React Flow nodes
  const nodes: Node[] = useMemo(() => {
    if (!pipelineState) {
      return [];
    }

    const nodes: Node[] = [];

    // TODO: Create entry point nodes
    // pipelineState.entry_points.forEach((entryPoint) => {
    //   nodes.push({
    //     id: entryPoint.entry_point_id,
    //     type: 'entryPoint',
    //     position: visualState?.[entryPoint.entry_point_id] || { x: 0, y: 0 },
    //     data: entryPoint,
    //   });
    // });

    // TODO: Create module nodes
    // pipelineState.modules.forEach((moduleInstance) => {
    //   nodes.push({
    //     id: moduleInstance.module_instance_id,
    //     type: 'module',
    //     position: visualState?.[moduleInstance.module_instance_id] || { x: 0, y: 0 },
    //     data: moduleInstance,
    //   });
    // });

    return nodes;
  }, [pipelineState, visualState]);

  // Convert pipeline state connections to React Flow edges
  const edges: Edge[] = useMemo(() => {
    if (!pipelineState) {
      return [];
    }

    // TODO: Create edges from connections
    // return pipelineState.connections.map((connection, index) => ({
    //   id: `edge-${index}`,
    //   source: sourceModuleId,
    //   target: targetModuleId,
    //   sourceHandle: connection.from_node_id,
    //   targetHandle: connection.to_node_id,
    // }));

    return [];
  }, [pipelineState]);

  // Handle node position changes
  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      if (mode === 'view') return; // Ignore in view mode

      // TODO: Update visual state with new node positions
      console.log('Nodes changed:', changes);
    },
    [mode, onVisualStateChange]
  );

  // Handle edge changes
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      if (mode === 'view') return; // Ignore in view mode

      // TODO: Update pipeline state with edge changes
      console.log('Edges changed:', changes);
    },
    [mode, onPipelineStateChange]
  );

  // Handle new connections
  const onConnect = useCallback(
    (connection: Connection) => {
      if (mode === 'view') return; // Ignore in view mode

      // TODO: Add new connection to pipeline state
      console.log('New connection:', connection);
    },
    [mode, onPipelineStateChange]
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
    <div className="w-full h-full bg-gray-900">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodesDraggable={mode === 'edit'}
        nodesConnectable={mode === 'edit'}
        elementsSelectable={mode === 'edit'}
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
  );
}

export function PipelineGraph(props: PipelineGraphProps) {
  return (
    <ReactFlowProvider>
      <PipelineGraphInner {...props} />
    </ReactFlowProvider>
  );
}
