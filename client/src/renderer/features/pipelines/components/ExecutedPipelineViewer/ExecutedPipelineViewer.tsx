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
  useViewport,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "dagre";
import { ExecutedModule } from "./ExecutedModule";
import { ExecutedEntryPoint } from "./ExecutedEntryPoint";
import { ExecutionEdge } from "./ExecutionEdge";
import { useModules } from "../../../modules";
import type { PipelineState } from "../../types";
import type { ExecutionStepResult } from "../../api/types";

interface ExecutedPipelineViewerProps {
  pipelineId: number | null;
  pipelineState?: PipelineState;
  executionSteps?: ExecutionStepResult[];
  entryValues?: Record<string, { name: string; value: any; type: string }>;
}

const nodeTypes = {
  executedModule: ExecutedModule,
  executedEntryPoint: ExecutedEntryPoint,
};

const edgeTypes = {
  executionEdge: ExecutionEdge,
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
  entryValues,
}: ExecutedPipelineViewerProps) {
  // Get current zoom level to adjust background density
  const { zoom } = useViewport();

  // Calculate gap based on zoom - larger gap when zoomed out
  // This prevents visual clutter at low zoom levels
  const backgroundGap = useMemo(() => {
    if (zoom < 0.5) return 40;
    if (zoom < 0.75) return 30;
    if (zoom < 1.5) return 20;
    return 15;
  }, [zoom]);

  // Fetch modules using TanStack Query
  const { data: modules = [], isLoading: modulesLoading } = useModules();

  // Convert pipeline state modules and entry points to React Flow nodes
  const rawNodes: Node[] = useMemo(() => {
    if (!pipelineState || !modules.length) {
      return [];
    }

    const nodes: Node[] = [];

    // Create entry point nodes
    pipelineState.entry_points.forEach((entryPoint) => {
      nodes.push({
        id: entryPoint.entry_point_id, // Use entry_point_id (E{xx} format)
        type: "executedEntryPoint",
        position: { x: 0, y: 0 }, // Will be positioned by dagre
        data: {
          name: entryPoint.name,
          nodeId: entryPoint.outputs[0]?.node_id || '', // Get node_id from first output
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

      // Determine execution status based on execution step
      let status: "executed" | "failed" | "not_executed";
      let error: string | null = null;

      if (!executionStep) {
        // No execution step means this module never ran (stopped before reaching it)
        status = "not_executed";
      } else if (executionStep.error) {
        // Has execution step with error - module failed
        status = "failed";
        error = executionStep.error;
      } else {
        // Has execution step without error - module executed successfully
        status = "executed";
      }

      // Build inputs/outputs from pipeline state structure with execution values
      // This ensures all handles are rendered even if execution data is missing
      const inputs: Record<string, { name: string; value: string; type: string; group_index: number; label: string }> = {};
      const outputs: Record<string, { name: string; value: string; type: string; group_index: number; label: string }> = {};

      // Populate inputs from pipeline state, overlay with execution data if available
      moduleInstance.inputs.forEach((input) => {
        const executionData = executionStep?.inputs?.[input.node_id];
        // Get group label from template's io_shape
        const groupLabel = template?.meta?.io_shape?.inputs?.nodes?.[input.group_index]?.label || input.label || "Group";

        inputs[input.node_id] = {
          name: executionData?.name || input.name,
          value: executionData?.value || "",
          type: executionData?.type || input.type,
          group_index: input.group_index,
          label: groupLabel,
        };
      });

      // Populate outputs from pipeline state, overlay with execution data if available
      moduleInstance.outputs.forEach((output) => {
        const executionData = executionStep?.outputs?.[output.node_id];
        // Get group label from template's io_shape
        const groupLabel = template?.meta?.io_shape?.outputs?.nodes?.[output.group_index]?.label || output.label || "Group";

        outputs[output.node_id] = {
          name: executionData?.name || output.name,
          value: executionData?.value || "",
          type: executionData?.type || output.type,
          group_index: output.group_index,
          label: groupLabel,
        };
      });

      nodes.push({
        id: moduleInstance.module_instance_id,
        type: "executedModule",
        position: { x: 0, y: 0 }, // Will be positioned by dagre
        data: {
          moduleId: moduleInstance.module_instance_id,
          moduleName,
          moduleColor,
          inputs,
          outputs,
          status,
          error,
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

    // Map entry points - use entry_point_id as the node ID
    pipelineState.entry_points.forEach((ep) => {
      // Map the output node_id to the entry_point_id
      if (ep.outputs[0]) {
        nodeIdToModuleId.set(ep.outputs[0].node_id, ep.entry_point_id);
      }
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

      // Get output data from source module or entry point
      let outputData = null;
      // Check if source is an entry point (E{xx} format)
      const isEntryPoint = pipelineState.entry_points.some(
        ep => ep.entry_point_id === sourceModuleId
      );

      if (isEntryPoint) {
        // Source is an entry point - use entryValues
        outputData = entryValues?.[connection.from_node_id] || null;
        console.log('Entry point edge:', connection.from_node_id, outputData);
      } else if (sourceModuleId) {
        // Source is a module - use execution steps
        const sourceExecution = executionSteps?.find(
          (step) => step.module_instance_id === sourceModuleId
        );
        // Get the specific output for this connection
        outputData = sourceExecution?.outputs?.[connection.from_node_id] || null;
      }

      return {
        id: `edge-${index}`,
        source: sourceModuleId || '',
        target: targetModuleId || '',
        sourceHandle: connection.from_node_id,
        targetHandle: connection.to_node_id,
        type: 'executionEdge',
        data: {
          output: outputData,
        },
      };
    });

    // Filter out edges with missing source or target
    return edges.filter(edge => edge.source && edge.target);
  }, [pipelineState, executionSteps, entryValues]);

  // Apply dagre layout to position nodes and calculate edge offsets
  const { nodes, edges } = useMemo(() => {
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(rawNodes, rawEdges);

    // Build node position map
    const nodePositions = new Map<string, { x: number; y: number }>();
    layoutedNodes.forEach((node) => {
      nodePositions.set(node.id, node.position);
    });

    // Group edges by their source-target column positions
    const edgesByColumn = new Map<string, typeof layoutedEdges>();
    layoutedEdges.forEach((edge) => {
      const sourcePos = nodePositions.get(edge.source);
      const targetPos = nodePositions.get(edge.target);

      if (sourcePos && targetPos) {
        // Round X positions to nearest 100px to group edges in same vertical column
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
          offset = edgeIndex * spacing - totalWidth / 2;
        }
      }

      return {
        ...edge,
        data: {
          ...edge.data, // Preserve existing data (output)
          offset,
        },
      };
    });

    return { nodes: layoutedNodes, edges: edgesWithOffsets };
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
        <Background
          variant={BackgroundVariant.Dots}
          gap={backgroundGap}
          size={2}
          color="#6B7280"
        />
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
