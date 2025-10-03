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

  // Helper function to get connected output name for an input pin
  const getConnectedOutputName = useCallback((moduleId: string, inputPinId: string): string | undefined => {
    // Find edge where this input is the target
    const edge = edges.find((e) => e.target === moduleId && e.targetHandle === inputPinId);
    if (!edge) return undefined;

    // Find the source module and pin
    const sourceModule = nodes.find((n) => n.id === edge.source);
    if (!sourceModule?.data?.moduleInstance) return undefined;

    const sourceModuleInstance = sourceModule.data.moduleInstance as ModuleInstance;
    const sourcePin = sourceModuleInstance.outputs.find((p) => p.node_id === edge.sourceHandle);

    return sourcePin ? sourcePin.name : undefined;
  }, [edges, nodes]);

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

  // Helper: Calculate effective allowed types for a pin based on entire connection graph
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
    if (!currentPin) return baseAllowedTypes;

    // Use BFS to traverse the entire connected graph and collect all type restrictions
    const visited = new Set<string>();
    const queue: Array<{ moduleId: string; pinId: string }> = [];
    let effectiveTypes = baseAllowedTypes;

    // Start with current pin
    queue.push({ moduleId, pinId });

    // If current pin has typevar, add all typevar siblings to start
    if (currentPin.type_var) {
      const typeVarPins = allPins.filter((p) => p.type_var === currentPin.type_var);
      typeVarPins.forEach((pin) => {
        queue.push({ moduleId, pinId: pin.node_id });
      });
    }

    while (queue.length > 0) {
      const current = queue.shift()!;
      const key = `${current.moduleId}:${current.pinId}`;

      if (visited.has(key)) continue;
      visited.add(key);

      // Get the module and pin
      const mod = nodes.find((n) => n.id === current.moduleId);
      if (!mod?.data?.moduleInstance) continue;

      const modInstance = mod.data.moduleInstance as ModuleInstance;
      const modPins = [...modInstance.inputs, ...modInstance.outputs];
      const pin = modPins.find((p) => p.node_id === current.pinId);
      if (!pin) continue;

      // Intersect with this pin's allowed types
      effectiveTypes = getTypeIntersection(effectiveTypes, pin.allowed_types || []);

      // If this pin has a typevar, add all typevar siblings
      if (pin.type_var) {
        const typeVarPins = modPins.filter((p) => p.type_var === pin.type_var);
        typeVarPins.forEach((p) => {
          queue.push({ moduleId: current.moduleId, pinId: p.node_id });
        });
      }

      // Find all connected pins via edges
      edges.forEach((edge) => {
        if (edge.source === current.moduleId && edge.sourceHandle === current.pinId) {
          queue.push({ moduleId: edge.target!, pinId: edge.targetHandle! });
        } else if (edge.target === current.moduleId && edge.targetHandle === current.pinId) {
          queue.push({ moduleId: edge.source!, pinId: edge.sourceHandle! });
        }
      });
    }

    return effectiveTypes;
  }, [edges, nodes, getTypeIntersection]);

  // Handle click on a handle to start or complete a connection
  const handleHandleClick = useCallback((nodeId: string, handleId: string, handleType: 'source' | 'target') => {
    if (viewOnly) return;

    if (!pendingConnection) {
      // Check if this handle already has a connection
      const existingEdge = edges.find((edge) => {
        return (edge.source === nodeId && edge.sourceHandle === handleId) ||
               (edge.target === nodeId && edge.targetHandle === handleId);
      });

      if (existingEdge) {
        // Handle already connected - pick up the connection from the OTHER end
        // Keep the clicked handle as the destination
        const isSource = existingEdge.source === nodeId && existingEdge.sourceHandle === handleId;
        const otherNodeId = isSource ? existingEdge.target : existingEdge.source;
        const otherHandleId = isSource ? existingEdge.targetHandle : existingEdge.sourceHandle;
        const otherHandleType: 'source' | 'target' = isSource ? 'target' : 'source';

        // Remove the existing edge
        setEdges((eds) => eds.filter((e) => e.id !== existingEdge.id));

        // Find the other node's pin for the type
        const otherNode = nodes.find(n => n.id === otherNodeId);
        if (!otherNode) return;

        const otherModuleInstance = otherNode.data.moduleInstance as ModuleInstance;
        const otherPin = otherHandleType === 'source'
          ? otherModuleInstance.outputs.find(p => p.node_id === otherHandleId)
          : otherModuleInstance.inputs.find(p => p.node_id === otherHandleId);

        // Start pending connection from the OTHER end
        setPendingConnection({
          sourceHandleId: otherHandleId!,
          sourceNodeId: otherNodeId!,
          handleType: otherHandleType,
          nodeType: otherPin?.type || 'str',
        });
      } else {
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
      }
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

      // Check if target handle already has a connection - if so, remove it
      const existingTargetEdge = edges.find((edge) => {
        return (edge.source === nodeId && edge.sourceHandle === handleId) ||
               (edge.target === nodeId && edge.targetHandle === handleId);
      });

      if (existingTargetEdge) {
        setEdges((eds) => eds.filter((e) => e.id !== existingTargetEdge.id));
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

      // Update connected nodes to match the new type using queue-based cascading
      if (connectedEdges.length > 0) {
        setNodes((nds) => {
          let updatedNodes = [...nds];

          // Queue of pins to process: { moduleId, pinId, newType }
          const queue: Array<{ moduleId: string; pinId: string; newType: string }> = [];
          const processed = new Set<string>(); // Track processed pins to avoid infinite loops

          // Initialize queue with directly connected pins
          for (const edge of connectedEdges) {
            const isSource = edge.source === moduleId && edge.sourceHandle === nodeId;
            const connectedModuleId = isSource ? edge.target : edge.source;
            const connectedPinId = isSource ? edge.targetHandle : edge.sourceHandle;

            queue.push({
              moduleId: connectedModuleId,
              pinId: connectedPinId,
              newType,
            });
          }

          // Process queue until empty
          while (queue.length > 0) {
            const update = queue.shift()!;
            const key = `${update.moduleId}:${update.pinId}`;

            // Skip if already processed
            if (processed.has(key)) continue;
            processed.add(key);

            // Find the module in the current updatedNodes
            const moduleNode = updatedNodes.find(n => n.id === update.moduleId);
            if (!moduleNode?.data?.moduleInstance) continue;

            const moduleInstance = moduleNode.data.moduleInstance as ModuleInstance;
            let updatedInputs = [...moduleInstance.inputs];
            let updatedOutputs = [...moduleInstance.outputs];

            // Find the pin being updated
            const allPins = [...updatedInputs, ...updatedOutputs];
            const targetPin = allPins.find(p => p.node_id === update.pinId);

            if (!targetPin) {
              continue;
            }

            if (targetPin.type === update.newType) {
              // Still need to check for edges to propagate further, even if this pin is already correct
              edges.forEach((edge) => {
                if (edge.source === update.moduleId && edge.sourceHandle === update.pinId) {
                  queue.push({
                    moduleId: edge.target!,
                    pinId: edge.targetHandle!,
                    newType: update.newType,
                  });
                } else if (edge.target === update.moduleId && edge.targetHandle === update.pinId) {
                  queue.push({
                    moduleId: edge.source!,
                    pinId: edge.sourceHandle!,
                    newType: update.newType,
                  });
                }
              });
              continue;
            }

            // Update the target pin
            updatedInputs = updatedInputs.map((input) =>
              input.node_id === update.pinId ? { ...input, type: update.newType } : input
            );
            updatedOutputs = updatedOutputs.map((output) =>
              output.node_id === update.pinId ? { ...output, type: update.newType } : output
            );

            // If the pin has a typevar, cascade to all typevar siblings
            if (targetPin.type_var) {
              const typeVar = targetPin.type_var;

              // Update typevar siblings and add to queue
              updatedInputs = updatedInputs.map((input) => {
                if (input.type_var === typeVar && input.type !== update.newType) {
                  queue.push({
                    moduleId: update.moduleId,
                    pinId: input.node_id,
                    newType: update.newType,
                  });
                  return { ...input, type: update.newType };
                }
                return input;
              });

              updatedOutputs = updatedOutputs.map((output) => {
                if (output.type_var === typeVar && output.type !== update.newType) {
                  queue.push({
                    moduleId: update.moduleId,
                    pinId: output.node_id,
                    newType: update.newType,
                  });
                  return { ...output, type: update.newType };
                }
                return output;
              });
            }

            // Find all edges connected to the updated pin and add them to queue
            edges.forEach((edge) => {
              if (edge.source === update.moduleId && edge.sourceHandle === update.pinId) {
                queue.push({
                  moduleId: edge.target!,
                  pinId: edge.targetHandle!,
                  newType: update.newType,
                });
              } else if (edge.target === update.moduleId && edge.targetHandle === update.pinId) {
                queue.push({
                  moduleId: edge.source!,
                  pinId: edge.sourceHandle!,
                  newType: update.newType,
                });
              }
            });

            // Update the module in updatedNodes
            updatedNodes = updatedNodes.map((node) => {
              if (node.id === update.moduleId) {
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
          }

          return updatedNodes;
        });

        // Update edge colors for all edges in the graph
        // Use setTimeout to ensure this runs after the node state has updated
        setTimeout(() => {
          setEdges((eds) => {
            // We need to access the updated nodes from the state
            let latestNodes: typeof nodes = [];
            setNodes((currentNodes) => {
              latestNodes = currentNodes;
              return currentNodes;
            });

            return eds.map((edge) => {
              const sourceNode = latestNodes.find(n => n.id === edge.source);
              const targetNode = latestNodes.find(n => n.id === edge.target);

              if (sourceNode?.data?.moduleInstance && targetNode?.data?.moduleInstance) {
                const sourceModule = sourceNode.data.moduleInstance as ModuleInstance;
                const targetModule = targetNode.data.moduleInstance as ModuleInstance;

                const sourcePin = [...sourceModule.inputs, ...sourceModule.outputs].find(
                  p => p.node_id === edge.sourceHandle
                );
                const targetPin = [...targetModule.inputs, ...targetModule.outputs].find(
                  p => p.node_id === edge.targetHandle
                );

                // If both pins exist and have the same type, update edge color to match
                if (sourcePin && targetPin && sourcePin.type === targetPin.type) {
                  const edgeColor = TYPE_COLORS[sourcePin.type] || "#6B7280";
                  if (edge.style?.stroke !== edgeColor) {
                    return {
                      ...edge,
                      style: { ...edge.style, stroke: edgeColor, strokeWidth: 2 },
                    };
                  }
                }
              }

              return edge;
            });
          });
        }, 0);
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

  // Handle config changes
  const handleConfigChange = useCallback((moduleId: string, configKey: string, value: any) => {
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
                config: {
                  ...moduleInstance.config,
                  [configKey]: value,
                },
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
      onConfigChange: handleConfigChange,
      onTextFocus: () => setIsTextFocused(true),
      onTextBlur: () => setIsTextFocused(false),
      onHandleClick: handleHandleClick,
      pendingConnection,
      getEffectiveAllowedTypes,
      getConnectedOutputName,
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
        minZoom={0.1}
        maxZoom={4}
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
  const viewport = useViewport(); // Get current viewport for zoom/pan

  // Find the handle element to get its position (recalculates on viewport change)
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
      key={`${viewport.x}-${viewport.y}-${viewport.zoom}`} // Force re-render on viewport change
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
