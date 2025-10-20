/**
 * ExecutedPipelineGraph Component
 * Read-only pipeline visualization with execution data overlay
 * Purpose-built for viewing pipeline execution results (not for editing)
 */

import { useState, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  Background,
  ReactFlowProvider,
  useReactFlow,
  useNodesInitialized,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';

import { ModuleTemplate } from '../../../types/moduleTypes';
import { PipelineState, VisualState, EntryPoint } from '../../../types/pipelineTypes';
import { Module } from './module/Module';
import { ExecutionEdge } from './ExecutionEdge';
import { createEdgesFromConnections } from '../utils/edgeUtils';
import { createModuleInstance } from '../utils/moduleFactory';

export interface ExecutedPipelineGraphProps {
  moduleTemplates: ModuleTemplate[];
  pipelineState: PipelineState;
  visualState: VisualState;
  failedModuleIds: string[];
  executionValues?: Map<string, { value: any; type: string; name: string }>;
}

const nodeTypes = {
  module: Module,
};

const edgeTypes = {
  execution: ExecutionEdge,
};

// Use dagre to calculate node positions
const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'LR') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const nodeWidth = 400;
  const nodeHeight = 200;

  dagreGraph.setGraph({ rankdir: direction, ranksep: 300, nodesep: 100 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

export function ExecutedPipelineGraph(props: ExecutedPipelineGraphProps) {
  return (
    <ReactFlowProvider>
      <ExecutedPipelineGraphInner {...props} />
    </ReactFlowProvider>
  );
}

function ExecutedPipelineGraphInner({
  moduleTemplates,
  pipelineState,
  visualState,
  failedModuleIds,
  executionValues = new Map(),
}: ExecutedPipelineGraphProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  // Convert pipeline state to React Flow nodes and edges
  useEffect(() => {
    console.log('[ExecutedPipelineGraph] Building nodes and edges from pipeline state');

    const newNodes: Node[] = [];
    const templateMap = new Map(moduleTemplates.map((t) => [t.id, t]));

    // Create entry point nodes (initial position doesn't matter, dagre will position them)
    pipelineState.entry_points.forEach((entryPoint: EntryPoint) => {
      const position = { x: 0, y: 0 };

      newNodes.push({
        id: `entry-${entryPoint.node_id}`,
        type: 'module',
        position,
        data: {
          moduleInstance: {
            module_instance_id: `entry-${entryPoint.node_id}`,
            module_ref: 'entry_point',
            module_kind: 'entry_point',
            config: {},
            inputs: [],
            outputs: [{
              node_id: entryPoint.node_id,
              direction: 'out' as const,
              type: entryPoint.type || 'str',
              name: entryPoint.name,
              label: entryPoint.name,
              position_index: 0,
              group_index: 0,
              allowed_types: [entryPoint.type || 'str'],
            }],
          },
          template: {
            id: 'entry_point',
            version: '1.0.0',
            title: 'Entry Point',
            description: 'Pipeline entry point',
            kind: 'entry_point',
            color: '#6B7280',
            meta: { io_shape: { inputs: { nodes: [] }, outputs: { nodes: [] }, type_params: {} } },
            config_schema: {},
          },
          executionMode: true,  // Execution view mode
          failedModuleIds,
          executionValues,  // Pass execution data for value display
        },
        draggable: false,
        selectable: false,
      });
    });

    // Create module nodes
    pipelineState.modules.forEach((moduleInstance) => {
      const [templateId] = moduleInstance.module_ref.split(':');
      const template = templateMap.get(templateId);

      if (!template) {
        console.warn(`[ExecutedPipelineGraph] Template not found for module: ${moduleInstance.module_ref}`);
        return;
      }

      const position = { x: 0, y: 0 }; // dagre will calculate actual position

      newNodes.push({
        id: moduleInstance.module_instance_id,
        type: 'module',
        position,
        data: {
          moduleInstance,
          template,
          executionMode: true,  // Execution view mode
          failedModuleIds,
          executionValues,  // Pass execution data for value display
        },
        draggable: false,
        selectable: false,
      });
    });

    // Create edges from connections
    const baseEdges = createEdgesFromConnections(
      pipelineState.connections,
      pipelineState.modules,
      pipelineState.entry_points
    );

    // Add execution data to edges
    const edgesWithData = baseEdges.map((edge) => {
      // The edge sourceHandle is the node_id of the output pin
      const executionData = executionValues.get(edge.sourceHandle || '');

      console.log('[ExecutedPipelineGraph] Edge:', {
        id: edge.id,
        source: edge.source,
        sourceHandle: edge.sourceHandle,
        target: edge.target,
        targetHandle: edge.targetHandle,
        hasExecutionData: !!executionData,
        executionData: executionData,
      });

      return {
        ...edge,
        type: 'execution', // Use custom edge component
        data: {
          value: executionData?.value,
          type: executionData?.type,
          sourceHandle: edge.sourceHandle, // Pass for debugging
        },
      };
    });

    // Apply dagre auto-layout
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(newNodes, edgesWithData);

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [pipelineState, visualState, moduleTemplates, failedModuleIds, executionValues]);

  return (
    <div className="w-full h-full bg-gray-900">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
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
        <Background variant="dots" gap={20} size={1} />
      </ReactFlow>
    </div>
  );
}
