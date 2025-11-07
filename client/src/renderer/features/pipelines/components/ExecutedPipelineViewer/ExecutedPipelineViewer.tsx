/**
 * ExecutedPipelineViewer
 * Read-only pipeline visualization with execution data overlay
 */

import { useMemo } from "react";
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  Background,
  ReactFlowProvider,
  BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "dagre";
import { ExecutedModule } from "./ExecutedModule";
import { ExecutedEntryPoint } from "./ExecutedEntryPoint";
import { useModules } from "../../../modules";
import type { PipelineState } from "../../types";
import type { ExecutionStepResult } from "../../api/types";

interface ExecutedPipelineViewerProps {
  pipelineId: number | null;
  pipelineState?: PipelineState;
  executionSteps?: ExecutionStepResult[];
}

const nodeTypes = {
  executedModule: ExecutedModule,
  executedEntryPoint: ExecutedEntryPoint,
};

// Use dagre to calculate node positions (left-to-right layout)
const getLayoutedElements = (
  nodes: Node[],
  edges: Edge[],
  direction = "LR"
) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const nodeWidth = 220;
  const nodeHeight = 180;

  // Configure layout: LR (left-to-right), ranksep for horizontal spacing, nodesep for vertical
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


function ExecutedPipelineViewerInner({
  pipelineState,
  executionSteps,
}: ExecutedPipelineViewerProps) {
  // Fetch modules using TanStack Query
  const { data: modules = [], isLoading: modulesLoading } = useModules();

  // Log execution steps on render
  console.log('Execution Steps:', executionSteps?.map((step, index) => ({
    index,
    module_instance_id: step.module_instance_id,
    step_number: step.step_number,
    inputs: step.inputs,
    outputs: step.outputs,
    error: step.error,
  })));

  // Log pipeline state structure
  console.log('Pipeline State Modules:', pipelineState?.modules.map(m => ({
    module_instance_id: m.module_instance_id,
    outputs: m.outputs.map(o => ({ node_id: o.node_id, name: o.name })),
    inputs: m.inputs.map(i => ({ node_id: i.node_id, name: i.name }))
  })));

  console.log('Pipeline Connections:', pipelineState?.connections);

  // Convert pipeline state modules and entry points to React Flow nodes
  const rawNodes: Node[] = useMemo(() => {
    if (!pipelineState || !modules.length) {
      return [];
    }

    const nodes: Node[] = [];

    // Create entry point nodes
    pipelineState.entry_points.forEach((entryPoint) => {
      nodes.push({
        id: `entry-${entryPoint.node_id}`, // Prefix with 'entry-' to match old implementation
        type: "executedEntryPoint",
        position: { x: 0, y: 0 }, // Will be positioned by dagre
        data: {
          name: entryPoint.name,
          nodeId: entryPoint.node_id,
        },
      });
    });

    // Create a map of module_ref to module template for quick lookup
    const moduleTemplateMap = new Map(
      modules.map((template) => [`${template.id}:${template.version}`, template])
    );

    // Create module nodes
    pipelineState.modules.forEach((moduleInstance) => {
      // Get module template from the loaded modules
      const template = moduleTemplateMap.get(moduleInstance.module_ref);

      // Fallback values if template not found
      const moduleName = template?.title || moduleInstance.module_ref.split(":")[0];
      const moduleColor = template?.color || "#6B7280";

      // Get execution data for this module
      const executionStep = executionSteps?.find((step) => step.module_instance_id === moduleInstance.module_instance_id);

      // Build inputs/outputs from pipeline state structure with execution values
      // This ensures all handles are rendered even if execution data is missing
      const inputs: Record<string, { name: string; value: string; type: string }> = {};
      const outputs: Record<string, { name: string; value: string; type: string }> = {};

      // Populate inputs from pipeline state, overlay with execution data if available
      moduleInstance.inputs.forEach((input) => {
        const executionData = executionStep?.inputs?.[input.node_id];
        inputs[input.node_id] = {
          name: executionData?.name || input.name,
          value: executionData?.value || "",
          type: executionData?.type || input.type,
        };
      });

      // Populate outputs from pipeline state, overlay with execution data if available
      moduleInstance.outputs.forEach((output) => {
        const executionData = executionStep?.outputs?.[output.node_id];
        outputs[output.node_id] = {
          name: executionData?.name || output.name,
          value: executionData?.value || "",
          type: executionData?.type || output.type,
        };
      });

      nodes.push({
        id: moduleInstance.module_instance_id,
        type: "executedModule",
        position: { x: 0, y: 0 }, // Will be positioned by dagre
        data: {
          moduleName,
          moduleColor,
          inputs,
          outputs,
          status: "executed" as const, // Default to executed for now
        },
      });
    });

    return nodes;
  }, [pipelineState, modules, executionSteps]);

  // Convert pipeline state connections to React Flow edges
  const rawEdges: Edge[] = useMemo(() => {
    if (!pipelineState) {
      return [];
    }

    // Build a lookup map: node_id -> module_instance_id (or entry point node_id)
    const nodeIdToModuleId = new Map<string, string>();
    pipelineState.modules.forEach((module) => {
      module.inputs.forEach((input) => {
        nodeIdToModuleId.set(input.node_id, module.module_instance_id);
      });
      module.outputs.forEach((output) => {
        nodeIdToModuleId.set(output.node_id, module.module_instance_id);
      });
    });

    // Map entry points - use 'entry-' prefixed ID as the node ID
    pipelineState.entry_points.forEach((ep) => {
      nodeIdToModuleId.set(ep.node_id, `entry-${ep.node_id}`);
    });

    // Convert connections to edges
    const edges = pipelineState.connections.map((connection, index) => {
      const sourceModuleId = nodeIdToModuleId.get(connection.from_node_id);
      const targetModuleId = nodeIdToModuleId.get(connection.to_node_id);

      // Debug: Log missing handles
      if (!sourceModuleId) {
        console.warn(`Missing source node for handle: ${connection.from_node_id}`);
      }
      if (!targetModuleId) {
        console.warn(`Missing target node for handle: ${connection.to_node_id}`);
      }

      return {
        id: `edge-${index}`,
        source: sourceModuleId || '',
        target: targetModuleId || '',
        sourceHandle: connection.from_node_id,
        targetHandle: connection.to_node_id,
        type: 'straight',
        style: { stroke: '#6B7280', strokeWidth: 2 },
      };
    });

    // Filter out edges with missing source or target
    return edges.filter(edge => edge.source && edge.target);
  }, [pipelineState]);

  // Apply dagre layout to position nodes
  const { nodes, edges } = useMemo(() => {
    return getLayoutedElements(rawNodes, rawEdges);
  }, [rawNodes, rawEdges]);

  // Show loading state while modules are loading
  if (modulesLoading) {
    return (
      <div className="w-full h-full bg-gray-900 flex items-center justify-center">
        <div className="text-gray-400">Loading modules...</div>
      </div>
    );
  }

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
        <Background variant={BackgroundVariant.Dots} />
      </ReactFlow>
    </div>
  );
}

export function ExecutedPipelineViewer(props: ExecutedPipelineViewerProps) {
  return (
    <ReactFlowProvider>
      <ExecutedPipelineViewerInner {...props} />
    </ReactFlowProvider>
  );
}
