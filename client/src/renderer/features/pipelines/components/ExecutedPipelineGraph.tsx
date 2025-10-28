/**
 * ExecutedPipelineGraph Component
 * Read-only pipeline visualization with execution data overlay
 * Purpose-built for viewing pipeline execution results (not for editing)
 */

import { useState, useEffect, useMemo, useImperativeHandle, forwardRef } from 'react';
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

export interface ExecutedPipelineGraphRef {
  fitView: () => void;
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

  const nodeWidth = 220;  // Further reduced for execution mode (no delete buttons, no type indicators)
  const nodeHeight = 180;

  // Increased spacing: nodesep=200 for vertical separation, ranksep=450 for horizontal module spacing
  dagreGraph.setGraph({ rankdir: direction, ranksep: 450, nodesep: 200 });

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

export const ExecutedPipelineGraph = forwardRef<ExecutedPipelineGraphRef, ExecutedPipelineGraphProps>((props, ref) => {
  return (
    <ReactFlowProvider>
      <ExecutedPipelineGraphInner {...props} ref={ref} />
    </ReactFlowProvider>
  );
});

const ExecutedPipelineGraphInner = forwardRef<ExecutedPipelineGraphRef, ExecutedPipelineGraphProps>(({
  moduleTemplates,
  pipelineState,
  visualState,
  failedModuleIds,
  executionValues = new Map(),
}, ref) => {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [hoveredModuleId, setHoveredModuleId] = useState<string | null>(null);
  const { fitView } = useReactFlow();

  // Expose fitView to parent component
  useImperativeHandle(ref, () => ({
    fitView: () => {
      fitView({ padding: 0.2, maxZoom: 1 });
    },
  }), [fitView]);

  // Hover callbacks for highlighting connected edges
  const handleModuleMouseEnter = (moduleId: string) => {
    setHoveredModuleId(moduleId);
  };

  const handleModuleMouseLeave = () => {
    setHoveredModuleId(null);
  };

  // Convert pipeline state to React Flow nodes and edges
  useEffect(() => {
    console.log('[ExecutedPipelineGraph] Building nodes and edges from pipeline state');

    const newNodes: Node[] = [];
    const templateMap = new Map(moduleTemplates.map((t) => [t.id, t]));

    // Build a lookup map for connections: input_pin_id -> output_pin_id
    const connectionMap = new Map<string, string>();
    pipelineState.connections.forEach((conn) => {
      connectionMap.set(conn.to_node_id, conn.from_node_id);
    });

    // Build a lookup map for pin names: node_id -> pin
    const allPins = new Map<string, any>();
    pipelineState.entry_points.forEach((ep) => {
      allPins.set(ep.node_id, { name: ep.name, type: 'entry_point' });
    });
    pipelineState.modules.forEach((mod) => {
      mod.inputs.forEach((pin) => allPins.set(pin.node_id, pin));
      mod.outputs.forEach((pin) => allPins.set(pin.node_id, pin));
    });

    // Function to get connected output name for an input pin
    const getConnectedOutputName = (moduleId: string, inputPinId: string): string | undefined => {
      const outputPinId = connectionMap.get(inputPinId);
      if (outputPinId) {
        const outputPin = allPins.get(outputPinId);
        return outputPin?.name;
      }
      return undefined;
    };

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
            color: '#000000',  // Black color for entry points
            meta: { io_shape: { inputs: { nodes: [] }, outputs: { nodes: [] }, type_params: {} } },
            config_schema: {},
          },
          executionMode: true,  // Execution view mode
          failedModuleIds,
          executionValues,  // Pass execution data for value display
          getConnectedOutputName,  // Function to lookup connected output names
          onModuleMouseEnter: handleModuleMouseEnter,
          onModuleMouseLeave: handleModuleMouseLeave,
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
        console.error(`[ExecutedPipelineGraph] Template not found for module: ${moduleInstance.module_ref}`);
        console.error(`[ExecutedPipelineGraph] Looking for template ID: "${templateId}"`);
        console.error(`[ExecutedPipelineGraph] Available template IDs:`, Array.from(templateMap.keys()));
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
          getConnectedOutputName,  // Function to lookup connected output names
          onModuleMouseEnter: handleModuleMouseEnter,
          onModuleMouseLeave: handleModuleMouseLeave,
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

    // Add execution data to edges (without offsets yet - we need layout positions first)
    const edgesWithData = baseEdges.map((edge) => {
      const executionData = executionValues.get(edge.sourceHandle || '');

      return {
        ...edge,
        type: 'execution',
        data: {
          value: executionData?.value,
          type: executionData?.type,
          sourceHandle: edge.sourceHandle,
          offset: 0, // Will be calculated after layout
        },
      };
    });

    // Apply dagre auto-layout
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(newNodes, edgesWithData);

    // NOW calculate offsets based on actual layouted positions
    const nodePositions = new Map<string, { x: number; y: number }>();
    layoutedNodes.forEach((node) => {
      nodePositions.set(node.id, node.position);
    });

    // Group edges by their X column positions (vertical alignment)
    const edgesByColumn = new Map<string, typeof layoutedEdges>();
    layoutedEdges.forEach((edge) => {
      const sourcePos = nodePositions.get(edge.source);
      const targetPos = nodePositions.get(edge.target);

      if (sourcePos && targetPos) {
        // Round X positions to nearest 100px to group edges in the same vertical column
        const sourceCol = Math.round(sourcePos.x / 100) * 100;
        const targetCol = Math.round(targetPos.x / 100) * 100;
        const columnKey = `${sourceCol}-${targetCol}`;

        if (!edgesByColumn.has(columnKey)) {
          edgesByColumn.set(columnKey, []);
        }
        edgesByColumn.get(columnKey)!.push(edge);
      }
    });

    // Apply offsets to edges that share the same vertical column
    const edgesWithOffsets = layoutedEdges.map((edge) => {
      const sourcePos = nodePositions.get(edge.source);
      const targetPos = nodePositions.get(edge.target);

      let offset = 0;
      if (sourcePos && targetPos) {
        const sourceCol = Math.round(sourcePos.x / 100) * 100;
        const targetCol = Math.round(targetPos.x / 100) * 100;
        const columnKey = `${sourceCol}-${targetCol}`;
        const parallelEdges = edgesByColumn.get(columnKey) || [];
        const edgeIndex = parallelEdges.indexOf(edge);
        const totalEdges = parallelEdges.length;

        // Spread parallel edges horizontally (12px spacing between each)
        if (totalEdges > 1) {
          const spacing = 12;
          const totalWidth = (totalEdges - 1) * spacing;
          offset = (edgeIndex * spacing) - (totalWidth / 2);
        }
      }

      return {
        ...edge,
        data: {
          ...edge.data,
          offset,
        },
      };
    });

    setNodes(layoutedNodes);
    setEdges(edgesWithOffsets);
  }, [pipelineState, visualState, moduleTemplates, failedModuleIds, executionValues]);

  // Update edge data when hoveredModuleId changes (without recalculating layout)
  useEffect(() => {
    setEdges((currentEdges) =>
      currentEdges.map((edge) => ({
        ...edge,
        data: {
          ...edge.data,
          hoveredModuleId,
        },
      }))
    );
  }, [hoveredModuleId]);

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
        <Background variant="dots" />
      </ReactFlow>
    </div>
  );
});
