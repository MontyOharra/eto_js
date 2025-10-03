import { useState, useCallback, useRef, useEffect } from "react";
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  NodeChange,
  EdgeChange,
  Connection,
  ConnectionLineType,
  useReactFlow,
  ReactFlowProvider,
  ViewportPortal,
  useViewport,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { ModuleTemplate, ModuleInstance, NodePin } from "../../types/moduleTypes";
import { PipelineState, VisualState } from "../../types/pipelineTypes";
import { ModuleNodeNew } from "./pipeline-graph/ModuleNodeNew";

// Type to color mapping (same as ModuleNodeNew)
const TYPE_COLORS: Record<string, string> = {
  str: "#3B82F6", // blue-500
  int: "#EF4444", // red-500
  float: "#F59E0B", // orange-500
  bool: "#10B981", // green-500
  datetime: "#8B5CF6", // purple-500
};

interface PipelineGraphProps {
  // Mode control
  viewOnly: boolean;

  // Module templates (for creating/reconstructing modules)
  moduleTemplates: ModuleTemplate[];

  // Initial state (optional - for View page)
  initialPipelineState?: PipelineState;
  initialVisualState?: VisualState;

  // Create mode only
  selectedModuleId?: string | null;
  onModulePlaced?: () => void;
}

// Custom node types
const nodeTypes = {
  module: ModuleNodeNew,
};

// Helper function to create example module instances
function createExampleModuleInstance(
  id: string,
  templateId: string,
  inputs: NodePin[],
  outputs: NodePin[]
): ModuleInstance {
  return {
    module_instance_id: id,
    module_ref: `${templateId}:1.0.0`,
    module_kind: "transform",
    config: {},
    inputs,
    outputs,
  };
}

export function PipelineGraph(props: PipelineGraphProps) {
  return (
    <ReactFlowProvider>
      <PipelineGraphInner {...props} />
    </ReactFlowProvider>
  );
}

function PipelineGraphInner({
  viewOnly,
  moduleTemplates,
  selectedModuleId,
  onModulePlaced,
}: PipelineGraphProps) {
  const { screenToFlowPosition, flowToScreenPosition } = useReactFlow();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [isTextFocused, setIsTextFocused] = useState(false);
  let nodeIdCounter = useRef(0);

  // Track connection preview
  const [connectionPreview, setConnectionPreview] = useState<{
    handleId: string;
    nodeId: string;
    handleType: 'source' | 'target';
    x: number;
    y: number;
  } | null>(null);
  const [mousePosition, setMousePosition] = useState<{ x: number; y: number } | null>(null);

  // Convert edges to simple connection format for ModuleNode
  const connections = edges.map((edge) => ({
    from_node_id: edge.sourceHandle || "",
    to_node_id: edge.targetHandle || "",
  }));

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      if (!viewOnly) {
        setNodes((nds) => applyNodeChanges(changes, nds));
      }
    },
    [viewOnly]
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      if (!viewOnly) {
        setEdges((eds) => applyEdgeChanges(changes, eds));
      }
    },
    [viewOnly]
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      if (!viewOnly) {
        // Find the source node to get the color
        const sourceNode = nodes.find((n) => n.id === connection.source);
        if (sourceNode) {
          const moduleInstance = sourceNode.data.moduleInstance as ModuleInstance;
          const sourcePin = moduleInstance.outputs.find((p) => p.node_id === connection.sourceHandle);
          const edgeColor = sourcePin ? TYPE_COLORS[sourcePin.type] || "#6B7280" : "#6B7280";

          setEdges((eds) => addEdge({ ...connection, style: { stroke: edgeColor } }, eds));
        } else {
          setEdges((eds) => addEdge(connection, eds));
        }
      }
    },
    [viewOnly, nodes]
  );

  // Track connection start for preview
  const onConnectStart = useCallback((_event: any, params: { nodeId: string | null; handleId: string | null; handleType: 'source' | 'target' | null }) => {
    console.log('🔵 onConnectStart fired:', params);

    if (viewOnly || !params.nodeId || !params.handleId || !params.handleType) {
      console.log('⚠️ Skipping preview - viewOnly or missing params');
      return;
    }

    // Find the handle element to get its position
    const handleElement = document.querySelector(`[data-handleid="${params.handleId}"]`) as HTMLElement;
    console.log('🔍 Handle element found:', !!handleElement, params.handleId);

    if (handleElement) {
      const rect = handleElement.getBoundingClientRect();
      const handleScreenX = rect.left + rect.width / 2;
      const handleScreenY = rect.top + rect.height / 2;

      console.log('✅ Setting connection preview:', { handleScreenX, handleScreenY });

      setConnectionPreview({
        handleId: params.handleId,
        nodeId: params.nodeId,
        handleType: params.handleType,
        x: handleScreenX,
        y: handleScreenY,
      });
    } else {
      console.log('❌ Handle element not found!');
    }
  }, [viewOnly]);

  // Clear connection preview when done
  const onConnectEnd = useCallback(() => {
    setConnectionPreview(null);
    setMousePosition(null);
  }, []);

  // Track mouse movement for preview line
  useEffect(() => {
    if (!connectionPreview) {
      setMousePosition(null);
      return;
    }

    console.log('👂 Starting mouse tracking for connection preview');

    const handleMouseMove = (event: MouseEvent) => {
      setMousePosition({ x: event.clientX, y: event.clientY });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => {
      console.log('🛑 Stopping mouse tracking');
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [connectionPreview]);

  // Debug: Log when preview state changes
  useEffect(() => {
    console.log('🔄 Connection preview state:', connectionPreview);
    console.log('🔄 Mouse position:', mousePosition);
  }, [connectionPreview, mousePosition]);

  // Handle module deletion
  const handleDeleteModule = useCallback((moduleId: string) => {
    setNodes((nds) => nds.filter((node) => node.id !== moduleId));
    setEdges((eds) => eds.filter((edge) => edge.source !== moduleId && edge.target !== moduleId));
  }, []);

  // Handle node updates (type changes, name changes)
  const handleUpdateNode = useCallback((moduleId: string, nodeId: string, updates: Partial<NodePin>) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === moduleId) {
          const moduleInstance = node.data.moduleInstance as ModuleInstance;

          // Update inputs
          const updatedInputs = moduleInstance.inputs.map((input) =>
            input.node_id === nodeId ? { ...input, ...updates } : input
          );

          // Update outputs
          const updatedOutputs = moduleInstance.outputs.map((output) =>
            output.node_id === nodeId ? { ...output, ...updates } : output
          );

          return {
            ...node,
            data: {
              ...node.data,
              moduleInstance: {
                ...moduleInstance,
                inputs: updatedInputs,
                outputs: updatedOutputs,
              },
            },
          };
        }
        return node;
      })
    );
  }, []);

  // Handle adding a node to a group
  const handleAddNode = useCallback((moduleId: string, direction: "input" | "output", groupLabel: string) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === moduleId) {
          const moduleInstance = node.data.moduleInstance as ModuleInstance;
          const nodeArray = direction === "input" ? moduleInstance.inputs : moduleInstance.outputs;

          // Find nodes in this group
          const groupNodes = nodeArray.filter((n) => n.label === groupLabel);
          const nextIndex = groupNodes.length;

          // Create new node
          const newNode: NodePin = {
            node_id: `${direction}-${Date.now()}-${Math.random()}`,
            direction: direction === "input" ? "in" : "out",
            type: "str",
            name: "",
            label: groupLabel,
            position_index: nextIndex,
            is_static: false,
            group_key: groupLabel.toLowerCase().replace(/\s+/g, "_"),
          };

          return {
            ...node,
            data: {
              ...node.data,
              moduleInstance: {
                ...moduleInstance,
                inputs: direction === "input" ? [...moduleInstance.inputs, newNode] : moduleInstance.inputs,
                outputs: direction === "output" ? [...moduleInstance.outputs, newNode] : moduleInstance.outputs,
              },
            },
          };
        }
        return node;
      })
    );
  }, []);

  // Handle removing a node
  const handleRemoveNode = useCallback((moduleId: string, nodeId: string) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === moduleId) {
          const moduleInstance = node.data.moduleInstance as ModuleInstance;

          return {
            ...node,
            data: {
              ...node.data,
              moduleInstance: {
                ...moduleInstance,
                inputs: moduleInstance.inputs.filter((input) => input.node_id !== nodeId),
                outputs: moduleInstance.outputs.filter((output) => output.node_id !== nodeId),
              },
            },
          };
        }
        return node;
      })
    );

    // Remove any edges connected to this node
    setEdges((eds) => eds.filter((edge) => edge.sourceHandle !== nodeId && edge.targetHandle !== nodeId));
  }, []);

  // Create module instance from template
  const createModuleInstance = useCallback((template: ModuleTemplate): ModuleInstance => {
    const instanceId = `module-${Date.now()}-${nodeIdCounter.current++}`;

    const createNodes = (ioShape: any, direction: "in" | "out"): NodePin[] => {
      const nodes: NodePin[] = [];
      let positionIndex = 0;

      // Process static nodes
      if (ioShape?.static?.slots) {
        ioShape.static.slots.forEach((nodeSpec: any) => {
          const typeVar = nodeSpec.typing?.type_var;
          const allowedTypes = nodeSpec.typing?.allowed_types || ["str"];
          const defaultType = typeVar ? "str" : allowedTypes[0];

          nodes.push({
            node_id: `${instanceId}-${direction}-static-${positionIndex}`,
            direction,
            type: defaultType,
            name: direction === "out" ? nodeSpec.label : "",
            label: nodeSpec.label,
            position_index: positionIndex++,
            is_static: true,
            type_var: typeVar,
          });
        });
      }

      // Process dynamic node groups
      if (ioShape?.dynamic?.groups) {
        ioShape.dynamic.groups.forEach((group: any, groupIndex: number) => {
          const typeVar = group.item?.typing?.type_var;
          const allowedTypes = group.item?.typing?.allowed_types || ["str"];
          const defaultType = typeVar ? "str" : allowedTypes[0];
          const groupKey = `dynamic-group-${groupIndex}`;

          // Create min_count instances
          for (let i = 0; i < group.min_count; i++) {
            nodes.push({
              node_id: `${instanceId}-${direction}-dynamic-${groupIndex}-${i}`,
              direction,
              type: defaultType,
              name: direction === "out" ? `${group.item.label} ${i + 1}` : "",
              label: group.item.label,
              position_index: positionIndex++,
              is_static: false,
              group_key: groupKey,
              type_var: typeVar,
            });
          }
        });
      }

      return nodes;
    };

    const inputs = createNodes(template.meta?.io_shape?.inputs, "in");
    const outputs = createNodes(template.meta?.io_shape?.outputs, "out");

    return {
      module_instance_id: instanceId,
      module_ref: `${template.id}:${template.version}`,
      module_kind: template.kind,
      config: {},
      inputs,
      outputs,
    };
  }, []);

  // Handle drag over
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  // Handle drop
  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const data = event.dataTransfer.getData("application/reactflow");
      if (!data) return;

      const { moduleId } = JSON.parse(data);
      const template = moduleTemplates.find((t) => t.id === moduleId);
      if (!template) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const moduleInstance = createModuleInstance(template);
      const newNode: Node = {
        id: moduleInstance.module_instance_id,
        type: "module",
        position,
        data: {
          moduleInstance,
          template,
        },
      };

      setNodes((nds) => nds.concat(newNode));
      onModulePlaced?.();
    },
    [screenToFlowPosition, moduleTemplates, createModuleInstance, onModulePlaced]
  );

  // Update nodes to include callbacks and connections
  const nodesWithCallbacks = nodes.map((node) => ({
    ...node,
    data: {
      ...node.data,
      onDeleteModule: handleDeleteModule,
      onUpdateNode: handleUpdateNode,
      onAddNode: handleAddNode,
      onRemoveNode: handleRemoveNode,
      connections,
      onTextFocus: () => setIsTextFocused(true),
      onTextBlur: () => setIsTextFocused(false),
    },
    draggable: !isTextFocused,
  }));

  return (
    <div
      className="w-full h-full bg-gray-900"
      style={{ width: "100%", height: "100%" }}
      onDrop={viewOnly ? undefined : onDrop}
      onDragOver={viewOnly ? undefined : onDragOver}
    >
      <ReactFlow
        nodes={nodesWithCallbacks}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onConnectStart={onConnectStart}
        onConnectEnd={onConnectEnd}
        nodeTypes={nodeTypes}
        nodesDraggable={!viewOnly}
        nodesConnectable={!viewOnly}
        elementsSelectable={!viewOnly}
        connectOnClick={!viewOnly}
        connectionLineStyle={{
          strokeDasharray: "5,5",
        }}
        connectionMode="loose"
        defaultEdgeOptions={{ style: { strokeWidth: 2 } }}
      >
        <Controls />
        <Background variant="dots" gap={20} size={1} />

        {/* Connection preview line */}
        {connectionPreview && mousePosition && (() => {
          console.log('🎨 Rendering ConnectionPreviewLine:', {
            start: { x: connectionPreview.x, y: connectionPreview.y },
            end: { x: mousePosition.x, y: mousePosition.y }
          });
          return (
            <ConnectionPreviewLine
              startX={connectionPreview.x}
              startY={connectionPreview.y}
              endX={mousePosition.x}
              endY={mousePosition.y}
              handleType={connectionPreview.handleType}
              nodes={nodes}
              nodeId={connectionPreview.nodeId}
              handleId={connectionPreview.handleId}
            />
          );
        })()}
      </ReactFlow>
    </div>
  );
}

// Connection preview line component
interface ConnectionPreviewLineProps {
  startX: number;
  startY: number;
  endX: number;
  endY: number;
  handleType: 'source' | 'target';
  nodes: Node[];
  nodeId: string;
  handleId: string;
}

function ConnectionPreviewLine({
  startX,
  startY,
  endX,
  endY,
  handleType,
  nodes,
  nodeId,
  handleId,
}: ConnectionPreviewLineProps) {
  // Get the color from the source node's output type
  const sourceNode = nodes.find((n) => n.id === nodeId);
  let edgeColor = "#6B7280"; // default gray

  if (sourceNode) {
    const moduleInstance = sourceNode.data.moduleInstance as ModuleInstance;
    if (handleType === 'source') {
      // Starting from output, find the output node
      const outputPin = moduleInstance.outputs.find((p) => p.node_id === handleId);
      edgeColor = outputPin ? TYPE_COLORS[outputPin.type] || "#6B7280" : "#6B7280";
    } else {
      // Starting from input, find the input node
      const inputPin = moduleInstance.inputs.find((p) => p.node_id === handleId);
      edgeColor = inputPin ? TYPE_COLORS[inputPin.type] || "#6B7280" : "#6B7280";
    }
  }

  // Calculate bezier curve control points
  const dx = endX - startX;
  const controlPointDistance = Math.abs(dx) * 0.5;
  const controlX1 = startX + (handleType === 'source' ? controlPointDistance : -controlPointDistance);
  const controlY1 = startY;
  const controlX2 = endX + (handleType === 'source' ? -controlPointDistance : controlPointDistance);
  const controlY2 = endY;

  const path = `M ${startX} ${startY} C ${controlX1} ${controlY1}, ${controlX2} ${controlY2}, ${endX} ${endY}`;

  console.log('🖌️ ConnectionPreviewLine rendering:', {
    path,
    color: edgeColor,
    start: { x: startX, y: startY },
    end: { x: endX, y: endY }
  });

  return (
    <svg
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 1000,
      }}
    >
      <path
        d={path}
        stroke={edgeColor}
        strokeWidth="2"
        strokeDasharray="5,5"
        fill="none"
      />
    </svg>
  );
}
