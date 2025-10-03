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

  // Track pending connection (click-to-connect)
  const [pendingConnection, setPendingConnection] = useState<{
    sourceHandleId: string;
    sourceNodeId: string;
    handleType: 'source' | 'target';
    nodeType: string; // The type of the starting node for preview color
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

  // Helper: Calculate intersection of allowed types
  const getTypeIntersection = useCallback((types1: string[], types2: string[]): string[] => {
    return types1.filter(type => types2.includes(type));
  }, []);

  // Helper: Calculate effective allowed types for a pin based on connections
  const getEffectiveAllowedTypes = useCallback((
    moduleId: string,
    pinId: string,
    baseAllowedTypes: string[]
  ): string[] => {
    const module = nodes.find((n) => n.id === moduleId);
    if (!module?.data?.moduleInstance) return baseAllowedTypes;

    const moduleInstance = module.data.moduleInstance as ModuleInstance;
    const allPins = [...moduleInstance.inputs, ...moduleInstance.outputs];
    const currentPin = allPins.find((p) => p.node_id === pinId);

    // Collect all edges that affect this pin's type restrictions
    const relevantEdges: typeof edges = [];

    // 1. Direct connections to this pin
    edges.forEach((edge) => {
      if ((edge.source === moduleId && edge.sourceHandle === pinId) ||
          (edge.target === moduleId && edge.targetHandle === pinId)) {
        relevantEdges.push(edge);
      }
    });

    // 2. If this pin has a typevar, include connections to all pins with same typevar
    if (currentPin?.type_var) {
      const typeVarPins = allPins.filter((p) => p.type_var === currentPin.type_var);

      typeVarPins.forEach((pin) => {
        edges.forEach((edge) => {
          if ((edge.source === moduleId && edge.sourceHandle === pin.node_id) ||
              (edge.target === moduleId && edge.targetHandle === pin.node_id)) {
            // Avoid duplicates
            if (!relevantEdges.some((e) => e.id === edge.id)) {
              relevantEdges.push(edge);
            }
          }
        });
      });
    }

    if (relevantEdges.length === 0) {
      return baseAllowedTypes; // No restrictions
    }

    // Calculate intersection of all connected pins' allowed types
    let effectiveTypes = baseAllowedTypes;

    relevantEdges.forEach((edge) => {
      const isSource = edge.source === moduleId;
      const otherModuleId = isSource ? edge.target : edge.source;
      const otherPinId = isSource ? edge.targetHandle : edge.sourceHandle;

      const otherModule = nodes.find((n) => n.id === otherModuleId);
      if (!otherModule?.data?.moduleInstance) return;

      const otherModuleInstance = otherModule.data.moduleInstance as ModuleInstance;
      const otherPins = [...otherModuleInstance.inputs, ...otherModuleInstance.outputs];
      const otherPin = otherPins.find((p: NodePin) => p.node_id === otherPinId);

      if (otherPin) {
        // Intersect with the connected pin's allowed types
        effectiveTypes = getTypeIntersection(effectiveTypes, otherPin.allowed_types || []);
      }
    });

    return effectiveTypes;
  }, [edges, nodes, getTypeIntersection]);

  // Handle click on a handle to start or complete a connection
  const handleHandleClick = useCallback((nodeId: string, handleId: string, handleType: 'source' | 'target') => {
    if (viewOnly) return;

    if (!pendingConnection) {
      // Start a new connection - find the node's type for preview color
      const node = nodes.find(n => n.id === nodeId);
      if (!node) return;

      const moduleInstance = node.data.moduleInstance as ModuleInstance;
      const pin = handleType === 'source'
        ? moduleInstance.outputs.find(p => p.node_id === handleId)
        : moduleInstance.inputs.find(p => p.node_id === handleId);

      setPendingConnection({
        sourceHandleId: handleId,
        sourceNodeId: nodeId,
        handleType,
        nodeType: pin?.type || 'str',
      });
    } else {
      // Complete the connection
      const { sourceHandleId, sourceNodeId, handleType: sourceHandleType } = pendingConnection;

      // Validate connection: source must be output, target must be input (or vice versa)
      if (sourceHandleType === handleType) {
        // Both are the same type (both inputs or both outputs) - invalid connection
        // Cancel the pending connection and start a new one from the clicked handle
        const node = nodes.find(n => n.id === nodeId);
        if (!node) return;

        const moduleInstance = node.data.moduleInstance as ModuleInstance;
        const pin = handleType === 'source'
          ? moduleInstance.outputs.find(p => p.node_id === handleId)
          : moduleInstance.inputs.find(p => p.node_id === handleId);

        setPendingConnection({
          sourceHandleId: handleId,
          sourceNodeId: nodeId,
          handleType,
          nodeType: pin?.type || 'str',
        });
        return;
      }

      // Get both nodes and their pins
      const startingNode = nodes.find(n => n.id === sourceNodeId);
      const endingNode = nodes.find(n => n.id === nodeId);

      if (!startingNode || !endingNode) return;

      const startingModuleInstance = startingNode.data.moduleInstance as ModuleInstance;
      const endingModuleInstance = endingNode.data.moduleInstance as ModuleInstance;

      const startingPin = sourceHandleType === 'source'
        ? startingModuleInstance.outputs.find(p => p.node_id === sourceHandleId)
        : startingModuleInstance.inputs.find(p => p.node_id === sourceHandleId);

      const endingPin = handleType === 'source'
        ? endingModuleInstance.outputs.find(p => p.node_id === handleId)
        : endingModuleInstance.inputs.find(p => p.node_id === handleId);

      if (!startingPin || !endingPin) return;

      // Rule 1: Validate type intersection
      const startingAllowedTypes = startingPin.allowed_types || ['str'];
      const endingAllowedTypes = endingPin.allowed_types || ['str'];
      const typeIntersection = getTypeIntersection(startingAllowedTypes, endingAllowedTypes);

      if (typeIntersection.length === 0) {
        // No shared types - reject connection
        console.warn('Cannot connect: No shared types between nodes');
        setPendingConnection(null);
        setMousePosition(null);
        return;
      }

      // Rule 2: Determine which type to use
      let targetType: string;
      const startingTypeInIntersection = typeIntersection.includes(startingPin.type);
      const endingTypeInIntersection = typeIntersection.includes(endingPin.type);

      if (startingTypeInIntersection) {
        // Rule 2a: Starting node's type is in intersection
        targetType = startingPin.type;
      } else if (endingTypeInIntersection) {
        // Rule 2b: Ending node's type is in intersection
        targetType = endingPin.type;
      } else {
        // Rule 2c: Neither type in intersection, use first shared type
        targetType = typeIntersection[0];
      }

      // Update both nodes to the target type AND cascade through typevars
      setNodes((nds) =>
        nds.map((node) => {
          if (node.id === sourceNodeId) {
            const moduleInstance = node.data.moduleInstance as ModuleInstance;
            let updatedInputs = [...moduleInstance.inputs];
            let updatedOutputs = [...moduleInstance.outputs];

            // Update the starting pin's type
            updatedInputs = updatedInputs.map((input) =>
              input.node_id === sourceHandleId ? { ...input, type: targetType } : input
            );
            updatedOutputs = updatedOutputs.map((output) =>
              output.node_id === sourceHandleId ? { ...output, type: targetType } : output
            );

            // Check if the updated pin has a typevar - if so, cascade to all pins with same typevar
            const updatedPin = [...updatedInputs, ...updatedOutputs].find(p => p.node_id === sourceHandleId);
            if (updatedPin?.type_var) {
              const typeVar = updatedPin.type_var;
              updatedInputs = updatedInputs.map((input) =>
                input.type_var === typeVar ? { ...input, type: targetType } : input
              );
              updatedOutputs = updatedOutputs.map((output) =>
                output.type_var === typeVar ? { ...output, type: targetType } : output
              );
            }

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
          } else if (node.id === nodeId) {
            const moduleInstance = node.data.moduleInstance as ModuleInstance;
            let updatedInputs = [...moduleInstance.inputs];
            let updatedOutputs = [...moduleInstance.outputs];

            // Update the ending pin's type
            updatedInputs = updatedInputs.map((input) =>
              input.node_id === handleId ? { ...input, type: targetType } : input
            );
            updatedOutputs = updatedOutputs.map((output) =>
              output.node_id === handleId ? { ...output, type: targetType } : output
            );

            // Check if the updated pin has a typevar - if so, cascade to all pins with same typevar
            const updatedPin = [...updatedInputs, ...updatedOutputs].find(p => p.node_id === handleId);
            if (updatedPin?.type_var) {
              const typeVar = updatedPin.type_var;
              updatedInputs = updatedInputs.map((input) =>
                input.type_var === typeVar ? { ...input, type: targetType } : input
              );
              updatedOutputs = updatedOutputs.map((output) =>
                output.type_var === typeVar ? { ...output, type: targetType } : output
              );
            }

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

      // Create the connection
      const connection: Connection = sourceHandleType === 'source'
        ? { source: sourceNodeId, sourceHandle: sourceHandleId, target: nodeId, targetHandle: handleId }
        : { source: nodeId, sourceHandle: handleId, target: sourceNodeId, targetHandle: sourceHandleId };

      // Use the target type for edge color
      const edgeColor = TYPE_COLORS[targetType] || "#6B7280";
      setEdges((eds) => addEdge({ ...connection, style: { stroke: edgeColor, strokeWidth: 2 } }, eds));

      // Clear pending connection
      setPendingConnection(null);
      setMousePosition(null);
    }
  }, [viewOnly, pendingConnection, nodes, getTypeIntersection]);

  // Handle click on the pane (background) to cancel pending connection
  const handlePaneClick = useCallback(() => {
    if (pendingConnection) {
      setPendingConnection(null);
      setMousePosition(null);
    }
  }, [pendingConnection]);

  // Track mouse movement for preview line
  useEffect(() => {
    if (!pendingConnection) {
      setMousePosition(null);
      return;
    }

    const handleMouseMove = (event: MouseEvent) => {
      setMousePosition({ x: event.clientX, y: event.clientY });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [pendingConnection]);

  // Handle Escape key to cancel pending connection
  useEffect(() => {
    if (!pendingConnection) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setPendingConnection(null);
        setMousePosition(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [pendingConnection]);

  // Handle module deletion
  const handleDeleteModule = useCallback((moduleId: string) => {
    setNodes((nds) => nds.filter((node) => node.id !== moduleId));
    setEdges((eds) => eds.filter((edge) => edge.source !== moduleId && edge.target !== moduleId));
  }, []);

  // Handle node updates (type changes, name changes)
  const handleUpdateNode = useCallback((moduleId: string, nodeId: string, updates: Partial<NodePin>) => {
    // If this is a type change, we need to propagate it to connected nodes
    if (updates.type) {
      const newType = updates.type;

      // Find all edges connected to this node
      const connectedEdges = edges.filter((edge) => {
        return (edge.source === moduleId && edge.sourceHandle === nodeId) ||
               (edge.target === moduleId && edge.targetHandle === nodeId);
      });

      // Update the node
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

      // Update connected nodes to match the new type
      if (connectedEdges.length > 0) {
        setNodes((nds) => {
          let updatedNodes = [...nds];
          const nodesToUpdate = new Map<string, { moduleId: string; pinId: string; newType: string }>();

          // First pass: identify all nodes that need to be updated
          for (const edge of connectedEdges) {
            const isSource = edge.source === moduleId && edge.sourceHandle === nodeId;
            const connectedModuleId = isSource ? edge.target : edge.source;
            const connectedPinId = isSource ? edge.targetHandle : edge.sourceHandle;

            nodesToUpdate.set(`${connectedModuleId}:${connectedPinId}`, {
              moduleId: connectedModuleId,
              pinId: connectedPinId,
              newType,
            });
          }

          // Second pass: update nodes and cascade through typevars
          updatedNodes = updatedNodes.map((node) => {
            // Check if any pin in this node needs updating
            const moduleInstance = node.data.moduleInstance as ModuleInstance;
            let hasChanges = false;
            let updatedInputs = [...moduleInstance.inputs];
            let updatedOutputs = [...moduleInstance.outputs];

            // Update directly connected pins
            for (const [key, update] of nodesToUpdate.entries()) {
              if (node.id === update.moduleId) {
                const changedPin = [...updatedInputs, ...updatedOutputs].find(p => p.node_id === update.pinId);

                updatedInputs = updatedInputs.map((input) =>
                  input.node_id === update.pinId ? { ...input, type: newType } : input
                );

                updatedOutputs = updatedOutputs.map((output) =>
                  output.node_id === update.pinId ? { ...output, type: newType } : output
                );

                hasChanges = true;

                // If the changed pin has a typevar, update all pins with the same typevar in this module
                if (changedPin?.type_var) {
                  const typeVar = changedPin.type_var;

                  updatedInputs = updatedInputs.map((input) =>
                    input.type_var === typeVar ? { ...input, type: newType } : input
                  );

                  updatedOutputs = updatedOutputs.map((output) =>
                    output.type_var === typeVar ? { ...output, type: newType } : output
                  );
                }
              }
            }

            if (hasChanges) {
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
          });

          return updatedNodes;
        });

        // Update edge colors to match the new type
        // Need to update edges connected to the original node AND edges connected to typevar siblings
        setEdges((eds) => {
          const edgesToUpdate = new Set<string>();

          // Add directly connected edges
          connectedEdges.forEach((ce) => edgesToUpdate.add(ce.id));

          // Find the original node to check for typevar
          const originalNode = nodes.find(n => n.id === moduleId);
          if (originalNode?.data?.moduleInstance) {
            const moduleInstance = originalNode.data.moduleInstance as ModuleInstance;
            const allPins = [...moduleInstance.inputs, ...moduleInstance.outputs];
            const changedPin = allPins.find(p => p.node_id === nodeId);

            if (changedPin?.type_var) {
              // Find all pins with the same typevar in this module
              const typeVarPins = allPins.filter(p => p.type_var === changedPin.type_var);

              // Find edges connected to these pins
              eds.forEach((edge) => {
                typeVarPins.forEach((pin) => {
                  if ((edge.source === moduleId && edge.sourceHandle === pin.node_id) ||
                      (edge.target === moduleId && edge.targetHandle === pin.node_id)) {
                    edgesToUpdate.add(edge.id);
                  }
                });
              });
            }
          }

          return eds.map((edge) => {
            if (edgesToUpdate.has(edge.id)) {
              const edgeColor = TYPE_COLORS[newType] || "#6B7280";
              return {
                ...edge,
                style: { ...edge.style, stroke: edgeColor, strokeWidth: 2 },
              };
            }
            return edge;
          });
        });
      }
    } else {
      // Not a type change, just update normally
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
    }
  }, [edges, nodes]);

  // Handle adding a node to a group
  const handleAddNode = useCallback((moduleId: string, direction: "input" | "output", groupLabel: string) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === moduleId) {
          const moduleInstance = node.data.moduleInstance as ModuleInstance;
          const nodeArray = direction === "input" ? moduleInstance.inputs : moduleInstance.outputs;

          // Find nodes in this group to copy type_var and allowed_types
          const groupNodes = nodeArray.filter((n) => n.label === groupLabel);
          const nextIndex = groupNodes.length;

          // Copy type_var and allowed_types from existing nodes in the group
          const existingNode = groupNodes[0];
          const typeVar = existingNode?.type_var;
          const allowedTypes = existingNode?.allowed_types || ["str"];

          // If there's a typevar, find the current type being used by other nodes with same typevar
          let nodeType: string;
          if (typeVar) {
            // Look for any node (input or output) with the same typevar to get current type
            const allNodes = [...moduleInstance.inputs, ...moduleInstance.outputs];
            const sameTypeVarNode = allNodes.find(n => n.type_var === typeVar);
            nodeType = sameTypeVarNode?.type || allowedTypes[0];
          } else {
            nodeType = allowedTypes[0];
          }

          // Create new node
          const newNode: NodePin = {
            node_id: `${direction}-${Date.now()}-${Math.random()}`,
            direction: direction === "input" ? "in" : "out",
            type: nodeType,
            name: "",
            label: groupLabel,
            position_index: nextIndex,
            is_static: false,
            group_key: groupLabel.toLowerCase().replace(/\s+/g, "_"),
            type_var: typeVar,
            allowed_types: allowedTypes,
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
      const typeParams = template.meta?.io_shape?.type_params || {};
      const ALL_TYPES = ["str", "int", "float", "bool", "datetime"];

      // Process static nodes
      if (ioShape?.static?.slots) {
        ioShape.static.slots.forEach((nodeSpec: any) => {
          const typeVar = nodeSpec.typing?.type_var;

          // Get allowed types: if typeVar exists, look it up in type_params, otherwise use allowed_types
          let allowedTypes: string[];
          if (typeVar && typeParams[typeVar]) {
            const typeParamTypes = typeParams[typeVar];
            // Empty array means all types allowed
            allowedTypes = typeParamTypes.length === 0 ? ALL_TYPES : typeParamTypes;
          } else {
            const directTypes = nodeSpec.typing?.allowed_types || ["str"];
            // Empty array means all types allowed
            allowedTypes = directTypes.length === 0 ? ALL_TYPES : directTypes;
          }

          const defaultType = allowedTypes[0];

          nodes.push({
            node_id: `${instanceId}-${direction}-static-${positionIndex}`,
            direction,
            type: defaultType,
            name: "",
            label: nodeSpec.label,
            position_index: positionIndex++,
            is_static: true,
            type_var: typeVar,
            allowed_types: allowedTypes,
          });
        });
      }

      // Process dynamic node groups
      if (ioShape?.dynamic?.groups) {
        ioShape.dynamic.groups.forEach((group: any, groupIndex: number) => {
          const typeVar = group.item?.typing?.type_var;

          // Get allowed types: if typeVar exists, look it up in type_params, otherwise use allowed_types
          let allowedTypes: string[];
          if (typeVar && typeParams[typeVar]) {
            const typeParamTypes = typeParams[typeVar];
            // Empty array means all types allowed
            allowedTypes = typeParamTypes.length === 0 ? ALL_TYPES : typeParamTypes;
          } else {
            const directTypes = group.item?.typing?.allowed_types || ["str"];
            // Empty array means all types allowed
            allowedTypes = directTypes.length === 0 ? ALL_TYPES : directTypes;
          }

          const defaultType = allowedTypes[0];
          const groupKey = `dynamic-group-${groupIndex}`;

          // Create min_count instances
          for (let i = 0; i < group.min_count; i++) {
            nodes.push({
              node_id: `${instanceId}-${direction}-dynamic-${groupIndex}-${i}`,
              direction,
              type: defaultType,
              name: "",
              label: group.item.label,
              position_index: positionIndex++,
              is_static: false,
              group_key: groupKey,
              type_var: typeVar,
              allowed_types: allowedTypes,
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
      onHandleClick: handleHandleClick,
      pendingConnection,
      getEffectiveAllowedTypes,
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
        nodeTypes={nodeTypes}
        nodesDraggable={!viewOnly && !isTextFocused}
        nodesConnectable={false}
        elementsSelectable={!viewOnly}
        onPaneClick={handlePaneClick}
        panOnDrag={!isTextFocused}
        defaultEdgeOptions={{ style: { strokeWidth: 2 } }}
      >
        <Controls />
        <Background variant="dots" gap={20} size={1} />

        {/* Connection preview line */}
        {pendingConnection && mousePosition && (
          <ConnectionPreviewLine
            pendingConnection={pendingConnection}
            mousePosition={mousePosition}
            nodes={nodes}
          />
        )}

        {/* Instructions banner when creating connection */}
        {pendingConnection && (
          <div
            style={{
              position: 'absolute',
              top: 10,
              left: '50%',
              transform: 'translateX(-50%)',
              backgroundColor: '#3B82F6',
              color: 'white',
              padding: '8px 16px',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: 500,
              zIndex: 1000,
              boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
            }}
          >
            Click another handle to connect, or press Escape to cancel
          </div>
        )}
      </ReactFlow>
    </div>
  );
}

// Connection preview line component
interface ConnectionPreviewLineProps {
  pendingConnection: {
    sourceHandleId: string;
    sourceNodeId: string;
    handleType: 'source' | 'target';
    nodeType: string;
  };
  mousePosition: { x: number; y: number };
  nodes: Node[];
}

function ConnectionPreviewLine({
  pendingConnection,
  mousePosition,
  nodes,
}: ConnectionPreviewLineProps) {
  const { sourceHandleId, nodeType, handleType } = pendingConnection;

  // Find the handle element to get its position
  const handleElement = document.querySelector(`[data-handleid="${sourceHandleId}"]`) as HTMLElement;
  if (!handleElement) return null;

  const rect = handleElement.getBoundingClientRect();
  const startX = rect.left + rect.width / 2;
  const startY = rect.top + rect.height / 2;

  // Use the starting node's type for the preview color
  const edgeColor = TYPE_COLORS[nodeType] || "#6B7280";

  // Calculate bezier curve control points
  const dx = mousePosition.x - startX;
  const controlPointDistance = Math.abs(dx) * 0.5;
  const controlX1 = startX + (handleType === 'source' ? controlPointDistance : -controlPointDistance);
  const controlY1 = startY;
  const controlX2 = mousePosition.x + (handleType === 'source' ? -controlPointDistance : controlPointDistance);
  const controlY2 = mousePosition.y;

  const path = `M ${startX} ${startY} C ${controlX1} ${controlY1}, ${controlX2} ${controlY2}, ${mousePosition.x} ${mousePosition.y}`;

  return (
    <svg
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: 999,
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
