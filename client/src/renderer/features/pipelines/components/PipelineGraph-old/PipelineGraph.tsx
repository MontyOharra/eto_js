/**
 * PipelineGraph Component
 * Visual pipeline builder using React Flow
 * Refactored to use extracted hooks and utilities
 */

import {
  useState,
  useCallback,
  useImperativeHandle,
  forwardRef,
  useEffect,
  useMemo,
  useRef,
} from "react";
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  NodeChange,
  EdgeChange,
  useReactFlow,
  ReactFlowProvider,
  useViewport,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { ModuleTemplate } from "../../../../modules/types";
import {
  PipelineState,
  VisualState,
  EntryPoint,
} from "../../types";
import { Module } from "./Module";
import { TYPE_COLORS } from "../../utils/moduleUtils";

// Hooks
import {
  useConnectionManager,
  useNodeUpdates,
  useModuleOperations,
  usePipelineInitialization,
} from "../../hooks";

// Utilities
import {
  serializeToPipelineState,
  serializeToVisualState,
} from "../../utils/serialization";
import { getEffectiveAllowedTypes } from "../../utils/typeSystem";

export interface PipelineGraphProps {
  viewOnly: boolean;
  moduleTemplates: ModuleTemplate[];
  initialPipelineState?: PipelineState;
  initialVisualState?: VisualState;
  selectedModuleId?: string | null;
  onModulePlaced?: () => void;
  onChange?: (state: PipelineState) => void; // Called when pipeline state changes (modules, connections)
  onVisualChange?: (state: VisualState) => void; // Called when visual state changes (node positions)
  entryPoints?: EntryPoint[];
  failedModuleIds?: string[]; // For execution visualization - highlight failed modules
}

export interface PipelineGraphRef {
  getPipelineState: () => PipelineState;
  getVisualState: () => VisualState;
}

const nodeTypes = {
  module: Module,
};

export const PipelineGraph = forwardRef<PipelineGraphRef, PipelineGraphProps>(
  (props, ref) => {
    return (
      <ReactFlowProvider>
        <PipelineGraphInner {...props} ref={ref} />
      </ReactFlowProvider>
    );
  }
);

const PipelineGraphInner = forwardRef<PipelineGraphRef, PipelineGraphProps>(
  (
    {
      viewOnly,
      moduleTemplates,
      selectedModuleId,
      onModulePlaced,
      onChange,
      onVisualChange,
      initialPipelineState,
      initialVisualState,
      entryPoints = [],
      failedModuleIds = [],
    },
    ref
  ) => {
    const { screenToFlowPosition } = useReactFlow();

    console.log("[PipelineGraph] Render with props:", {
      entryPointsCount: entryPoints.length,
      entryPointIds: entryPoints.map((ep) => ep.node_id),
    });

    // State
    const [nodes, setNodes] = useState<Node[]>([]);
    const [edges, setEdges] = useState<Edge[]>([]);
    const [isTextFocused, setIsTextFocused] = useState(false);
    const [selectedEdge, setSelectedEdge] = useState<string | null>(null);
    const [hoveredModuleId, setHoveredModuleId] = useState<string | null>(null);

    // Click-to-connect state
    const [pendingConnection, setPendingConnection] = useState<{
      sourceHandleId: string;
      sourceNodeId: string;
      handleType: "source" | "target";
      nodeType: string;
    } | null>(null);
    const [mousePosition, setMousePosition] = useState<{
      x: number;
      y: number;
    } | null>(null);

    // Initialize pipeline from state or entry points
    const { isInitialized } = usePipelineInitialization({
      moduleTemplates,
      initialPipelineState,
      initialVisualState,
      entryPoints,
      setNodes,
      setEdges,
    });

    // Connection management
    const connectionManager = useConnectionManager({
      nodes,
      edges,
      setNodes,
      setEdges,
      viewOnly,
    });

    // Node updates
    const nodeUpdates = useNodeUpdates({
      nodes,
      edges,
      setNodes,
      setEdges,
      viewOnly,
    });

    // Module operations
    const moduleOps = useModuleOperations({
      nodes,
      setNodes,
      viewOnly,
    });

    // Memoize pipeline state (logical structure only, not visual positioning)
    const pipelineState = useMemo(() => {
      return serializeToPipelineState(nodes, edges);
    }, [nodes, edges]);

    // Track previous pipeline state to detect actual changes (not just visual moves)
    const prevPipelineStateRef = useRef<string | null>(null);

    // Expose ref API
    useImperativeHandle(
      ref,
      () => ({
        getPipelineState: () => pipelineState,
        getVisualState: () => serializeToVisualState(nodes),
      }),
      [nodes, edges, pipelineState]
    );

    // Notify parent of state changes (only when logical structure changes, not visual)
    useEffect(() => {
      if (!onChange) return;

      // GUARD: Don't fire onChange until initialization is complete
      // This prevents clearing parent state on mount before we've loaded initial data
      if (!isInitialized) {
        console.log("[PipelineGraph onChange] Skipping - not initialized yet");
        return;
      }

      // Serialize to JSON for deep comparison
      const currentStateJson = JSON.stringify(pipelineState);

      // Only call onChange if the pipeline structure actually changed
      if (prevPipelineStateRef.current !== currentStateJson) {
        console.log("[PipelineGraph onChange]", {
          nodeCount: nodes.length,
          edgeCount: edges.length,
          pipelineState,
          reason:
            prevPipelineStateRef.current === null
              ? "initial"
              : "structure changed",
        });

        prevPipelineStateRef.current = currentStateJson;
        onChange(pipelineState);
      }
    }, [pipelineState, onChange, nodes.length, edges.length, isInitialized]);

    // Track if we've captured initial visual state
    const hasCapturedInitialVisualState = useRef(false);

    // Capture visual state after initialization completes
    useEffect(() => {
      if (!onVisualChange) return;
      if (!isInitialized) return;
      if (hasCapturedInitialVisualState.current) return; // Only capture once after init

      // Capture initial visual state (entry point positions, any loaded module positions)
      const visualState = serializeToVisualState(nodes);
      if (Object.keys(visualState).length > 0) {
        console.log(
          "[PipelineGraph] Capturing initial visual state after initialization:",
          {
            nodeCount: nodes.length,
            visualState,
          }
        );
        hasCapturedInitialVisualState.current = true;
        onVisualChange(visualState);
      }
    }, [isInitialized, nodes, onVisualChange]); // Run when nodes change after initialization

    // React Flow node/edge change handlers
    const onNodesChange = useCallback(
      (changes: NodeChange[]) => {
        if (!viewOnly) {
          // Check if this is a drag end event (position change with dragging=false)
          const isDragEnd = changes.some(
            (change) =>
              change.type === "position" &&
              "dragging" in change &&
              change.dragging === false
          );

          setNodes((nds) => {
            const updatedNodes = applyNodeChanges(changes, nds);

            // Only update visual state on drag end
            if (isDragEnd && onVisualChange) {
              const visualState = serializeToVisualState(updatedNodes);
              onVisualChange(visualState);
            }

            return updatedNodes;
          });
        }
      },
      [viewOnly, onVisualChange]
    );

    const onEdgesChange = useCallback(
      (changes: EdgeChange[]) => {
        if (!viewOnly) {
          setEdges((eds) => applyEdgeChanges(changes, eds));
        }
      },
      [viewOnly]
    );

    // Click-to-connect: Handle click on a pin
    const handleHandleClick = useCallback(
      (nodeId: string, handleId: string, handleType: "source" | "target") => {
        if (viewOnly) return;

        if (!pendingConnection) {
          // Start connection - check if handle already has a connection
          const existingEdge = edges.find(
            (edge) =>
              (edge.source === nodeId && edge.sourceHandle === handleId) ||
              (edge.target === nodeId && edge.targetHandle === handleId)
          );

          if (existingEdge) {
            // Pick up existing connection from the other end
            const isSource =
              existingEdge.source === nodeId &&
              existingEdge.sourceHandle === handleId;
            const otherNodeId = isSource
              ? existingEdge.target
              : existingEdge.source;
            const otherHandleId = isSource
              ? existingEdge.targetHandle
              : existingEdge.sourceHandle;
            const otherHandleType: "source" | "target" = isSource
              ? "target"
              : "source";

            // Remove existing edge
            connectionManager.deleteConnection(existingEdge.id);

            // Start pending from other end
            const otherNode = nodes.find((n) => n.id === otherNodeId);
            const otherModule = otherNode?.data?.moduleInstance;
            const otherPin = otherModule
              ? findPin(otherModule, otherHandleId!)
              : null;

            setPendingConnection({
              sourceHandleId: otherHandleId!,
              sourceNodeId: otherNodeId!,
              handleType: otherHandleType,
              nodeType: otherPin?.type || "str",
            });
          } else {
            // Start new connection
            const node = nodes.find((n) => n.id === nodeId);
            const moduleInstance = node?.data?.moduleInstance;
            const pin = moduleInstance
              ? findPin(moduleInstance, handleId)
              : null;

            setPendingConnection({
              sourceHandleId: handleId,
              sourceNodeId: nodeId,
              handleType,
              nodeType: pin?.type || "str",
            });
          }
        } else {
          // Complete connection
          const {
            sourceHandleId,
            sourceNodeId,
            handleType: sourceHandleType,
          } = pendingConnection;

          // Validate: source must be output, target must be input
          if (sourceHandleType === handleType) {
            // Both same type - cancel and start new from clicked handle
            const node = nodes.find((n) => n.id === nodeId);
            const moduleInstance = node?.data?.moduleInstance;
            const pin = moduleInstance
              ? findPin(moduleInstance, handleId)
              : null;

            setPendingConnection({
              sourceHandleId: handleId,
              sourceNodeId: nodeId,
              handleType,
              nodeType: pin?.type || "str",
            });
            return;
          }

          // Determine source and target
          const isSourceOutput = sourceHandleType === "source";
          const sourceModuleId = isSourceOutput ? sourceNodeId : nodeId;
          const sourcePinId = isSourceOutput ? sourceHandleId : handleId;
          const targetModuleId = isSourceOutput ? nodeId : sourceNodeId;
          const targetPinId = isSourceOutput ? handleId : sourceHandleId;

          // Create connection (uses type propagation)
          const success = connectionManager.createConnection(
            sourceModuleId,
            sourcePinId,
            targetModuleId,
            targetPinId
          );

          if (success) {
            setPendingConnection(null);
            setMousePosition(null);
          } else {
            // Connection failed - keep pending
            console.warn("Connection creation failed");
          }
        }
      },
      [viewOnly, pendingConnection, nodes, edges, connectionManager]
    );

    // Module deletion
    const handleDeleteModule = useCallback(
      (moduleId: string) => {
        if (viewOnly) return;
        connectionManager.deleteConnectionsForModule(moduleId);
        moduleOps.deleteModule(moduleId);
      },
      [connectionManager, moduleOps, viewOnly]
    );

    // Node updates
    const handleUpdateNode = useCallback(
      (moduleId: string, nodeId: string, updates: Partial<any>) => {
        nodeUpdates.updateNode(moduleId, nodeId, updates);
      },
      [nodeUpdates]
    );

    // Add pin
    const handleAddNode = useCallback(
      (moduleId: string, direction: "input" | "output", groupIndex: number) => {
        const node = nodes.find((n) => n.id === moduleId);
        const template = node?.data?.template;
        if (template) {
          moduleOps.addPin(moduleId, template, direction, groupIndex);
        }
      },
      [nodes, moduleOps]
    );

    // Remove pin
    const handleRemoveNode = useCallback(
      (moduleId: string, nodeId: string) => {
        connectionManager.deleteConnectionsForPin(moduleId, nodeId);
        moduleOps.removePin(moduleId, nodeId);
      },
      [connectionManager, moduleOps]
    );

    // Config change
    const handleConfigChange = useCallback(
      (moduleId: string, configKey: string, value: any) => {
        moduleOps.updateConfig(moduleId, configKey, value);
      },
      [moduleOps]
    );

    // Get connected output name for input pin
    const getConnectedOutputName = useCallback(
      (moduleId: string, inputPinId: string): string | undefined => {
        const edge = edges.find(
          (e) => e.target === moduleId && e.targetHandle === inputPinId
        );
        if (!edge) return undefined;

        const sourceModule = nodes.find((n) => n.id === edge.source);
        const sourceModuleInstance = sourceModule?.data?.moduleInstance;
        const sourcePin = sourceModuleInstance
          ? findPin(sourceModuleInstance, edge.sourceHandle!)
          : null;

        return sourcePin?.name;
      },
      [nodes, edges]
    );

    // Get effective allowed types
    const getEffectiveAllowedTypesCallback = useCallback(
      (moduleId: string, pinId: string, baseAllowedTypes: string[]) => {
        return getEffectiveAllowedTypes(
          nodes,
          edges,
          moduleId,
          pinId,
          baseAllowedTypes
        );
      },
      [nodes, edges]
    );

    // Edge click
    const handleEdgeClick = useCallback(
      (_event: React.MouseEvent, edge: Edge) => {
        if (!viewOnly) {
          setSelectedEdge(edge.id);
        }
      },
      [viewOnly]
    );

    // Delete edge
    const handleDeleteEdge = useCallback(() => {
      if (selectedEdge) {
        connectionManager.deleteConnection(selectedEdge);
        setSelectedEdge(null);
      }
    }, [selectedEdge, connectionManager]);

    // Pane click (cancel pending connection or deselect edge)
    const handlePaneClick = useCallback(() => {
      setPendingConnection(null);
      setMousePosition(null);
      setSelectedEdge(null);
    }, []);

    // Module hover handlers for edge highlighting
    const handleModuleMouseEnter = useCallback((moduleId: string) => {
      setHoveredModuleId(moduleId);
    }, []);

    const handleModuleMouseLeave = useCallback(() => {
      setHoveredModuleId(null);
    }, []);

    // Track mouse for preview line
    const handleMouseMove = useCallback(
      (event: React.MouseEvent) => {
        if (pendingConnection) {
          setMousePosition({ x: event.clientX, y: event.clientY });
        }
      },
      [pendingConnection]
    );

    // Escape key - cancel pending connection
    const handleKeyDown = useCallback(
      (event: KeyboardEvent) => {
        if (event.key === "Escape" && pendingConnection) {
          setPendingConnection(null);
          setMousePosition(null);
        }
      },
      [pendingConnection]
    );

    // Attach escape key listener
    useEffect(() => {
      window.addEventListener("keydown", handleKeyDown);
      return () => window.removeEventListener("keydown", handleKeyDown);
    }, [handleKeyDown]);

    // Drag and drop
    const onDragOver = useCallback(
      (event: React.DragEvent) => {
        if (viewOnly) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
      },
      [viewOnly]
    );

    const onDrop = useCallback(
      (event: React.DragEvent) => {
        if (viewOnly) return;

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

        moduleOps.addModule(template, position);
        onModulePlaced?.();

        // Capture visual state after adding module
        // Need to wait for next tick to ensure state has updated
        setTimeout(() => {
          if (onVisualChange) {
            setNodes((currentNodes) => {
              const visualState = serializeToVisualState(currentNodes);
              console.log(
                "[PipelineGraph onDrop] Capturing visual state after module added:",
                {
                  nodeCount: currentNodes.length,
                  visualState,
                }
              );
              onVisualChange(visualState);
              return currentNodes;
            });
          }
        }, 0);
      },
      [
        viewOnly,
        screenToFlowPosition,
        moduleTemplates,
        moduleOps,
        onModulePlaced,
        onVisualChange,
      ]
    );

    // Prepare nodes with callbacks
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
        getEffectiveAllowedTypes: getEffectiveAllowedTypesCallback,
        getConnectedOutputName,
        failedModuleIds, // Pass failed module IDs for error highlighting
        onModuleMouseEnter: handleModuleMouseEnter, // For edge highlighting on hover
        onModuleMouseLeave: handleModuleMouseLeave,
      },
      draggable: !isTextFocused,
    }));

    // Prepare edges with selection and hover styling
    const edgesWithSelection = edges.map((edge) => {
      const edgeColor = edge.style?.stroke || "#6B7280";

      // Check if edge is selected
      if (edge.id === selectedEdge) {
        return {
          ...edge,
          style: {
            ...edge.style,
            strokeDasharray: "5,5",
            strokeWidth: 4,
            filter: `drop-shadow(0 0 8px ${edgeColor}) drop-shadow(0 0 16px ${edgeColor})`,
          },
        };
      }

      // Check if edge is connected to hovered module
      const isConnectedToHoveredModule =
        hoveredModuleId &&
        (edge.source === hoveredModuleId || edge.target === hoveredModuleId);

      if (isConnectedToHoveredModule) {
        return {
          ...edge,
          style: {
            ...edge.style,
            strokeWidth: 4,
            filter: `drop-shadow(0 0 8px ${edgeColor}) drop-shadow(0 0 16px ${edgeColor})`,
          },
        };
      }

      return edge;
    });

    return (
      <div
        className="w-full h-full bg-gray-900"
        onDrop={viewOnly ? undefined : onDrop}
        onDragOver={viewOnly ? undefined : onDragOver}
        onMouseMove={handleMouseMove}
      >
        <ReactFlow
          nodes={nodesWithCallbacks}
          edges={edgesWithSelection}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onEdgeClick={handleEdgeClick}
          nodeTypes={nodeTypes}
          nodesDraggable={!viewOnly && !isTextFocused}
          nodesConnectable={false}
          elementsSelectable={!viewOnly}
          onPaneClick={handlePaneClick}
          panOnDrag={!isTextFocused}
          defaultEdgeOptions={{
            type: "default",
            style: { strokeWidth: 2 },
          }}
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

          {/* Connection instructions */}
          {pendingConnection && (
            <div className="absolute top-10 left-1/2 transform -translate-x-1/2 bg-blue-500 text-white px-4 py-2 rounded-md shadow-lg z-[1000]">
              Click another handle to connect, or press Escape to cancel
            </div>
          )}

          {/* Edge deletion modal */}
          {selectedEdge && (
            <div className="absolute bottom-20 left-1/2 transform -translate-x-1/2 bg-gray-800 border border-gray-700 px-5 py-3 rounded-lg shadow-xl z-[1000] flex items-center gap-4">
              <span className="text-gray-300 text-sm">Connection selected</span>
              <button
                onClick={handleDeleteEdge}
                className="bg-red-500 hover:bg-red-600 text-white px-4 py-1.5 rounded-md text-sm font-medium transition-colors"
              >
                Delete Connection
              </button>
            </div>
          )}
        </ReactFlow>
      </div>
    );
  }
);

// Connection preview line component
interface ConnectionPreviewLineProps {
  pendingConnection: {
    sourceHandleId: string;
    sourceNodeId: string;
    handleType: "source" | "target";
    nodeType: string;
  };
  mousePosition: { x: number; y: number };
  nodes: Node[];
}

function ConnectionPreviewLine({
  pendingConnection,
  mousePosition,
}: ConnectionPreviewLineProps) {
  const { sourceHandleId, nodeType, handleType } = pendingConnection;
  const viewport = useViewport();

  // Find the handle element
  const handleElement = document.querySelector(
    `[data-handleid="${sourceHandleId}"]`
  ) as HTMLElement;
  if (!handleElement) return null;

  const rect = handleElement.getBoundingClientRect();
  const startX = rect.left + rect.width / 2;
  const startY = rect.top + rect.height / 2;

  // Get color from type (import at top of file)
  const edgeColor = TYPE_COLORS[nodeType] || "#6B7280";

  // Calculate bezier curve
  const dx = mousePosition.x - startX;
  const controlPointDistance = Math.abs(dx) * 0.5;
  const controlX1 =
    startX +
    (handleType === "source" ? controlPointDistance : -controlPointDistance);
  const controlY1 = startY;
  const controlX2 =
    mousePosition.x +
    (handleType === "source" ? -controlPointDistance : controlPointDistance);
  const controlY2 = mousePosition.y;

  const path = `M ${startX} ${startY} C ${controlX1} ${controlY1}, ${controlX2} ${controlY2}, ${mousePosition.x} ${mousePosition.y}`;

  return (
    <svg
      key={`${viewport.x}-${viewport.y}-${viewport.zoom}`}
      className="fixed top-0 left-0 w-screen h-screen pointer-events-none z-[999]"
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
