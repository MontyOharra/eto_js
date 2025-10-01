import React, { useState, useRef, useEffect } from 'react';
import {
  ModuleTemplate,
  ModuleInstance,
  PipelineState,
  VisualState,
  PipelineData,
  Connection
} from '../../../types/pipelineTypes';
import { removeNodeFromModule, updateNodeType } from '../../../utils/moduleFactory';
import { createModuleInstance, addNodeToGroup, TypeVariableManager } from '../../../utils/moduleFactoryNew';
import { ModuleComponent } from './ModuleComponent';
import { ConnectionLayer } from './ConnectionLayer';
import { ConnectionInfoOverlay } from './ConnectionInfoOverlay';
import { EntryPointComponent } from './EntryPointComponent';

interface TransformationGraphProps {
  // Available module templates from API
  moduleTemplates: ModuleTemplate[];

  // Currently selected module from sidebar
  selectedModule: ModuleTemplate | null;
  onModuleSelect: (module: ModuleTemplate | null) => void;

  // Initial state for loading existing pipelines
  initialPipeline?: PipelineState;
  initialVisual?: VisualState;

  // Callbacks for state changes (optional)
  onPipelineChange?: (pipeline: PipelineState) => void;
  onVisualChange?: (visual: VisualState) => void;
}

export const TransformationGraph: React.FC<TransformationGraphProps> = ({
  moduleTemplates,
  selectedModule,
  onModuleSelect,
  initialPipeline,
  initialVisual,
  onPipelineChange,
  onVisualChange
}) => {
  // Canvas ref for mouse position calculations
  const canvasRef = useRef<HTMLDivElement>(null);

  // Viewport state
  const [zoom, setZoom] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });

  // Canvas dragging state
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [dragStartOffset, setDragStartOffset] = useState({ x: 0, y: 0 });

  // Module dragging state
  const [isDraggingModule, setIsDraggingModule] = useState(false);
  const [draggedModuleId, setDraggedModuleId] = useState<string | null>(null);
  const [moduleDragOffset, setModuleDragOffset] = useState({ x: 0, y: 0 });
  const [temporaryPosition, setTemporaryPosition] = useState<{ x: number; y: number } | null>(null);

  // Selection state
  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);

  // Connection state
  const [startingConnection, setStartingConnection] = useState<{
    moduleId: string;
    nodeId: string;
    nodeType: 'input' | 'output';
    editingConnections?: Connection[]; // Connections being edited/redirected
  } | null>(null);
  const [currentMousePosition, setCurrentMousePosition] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [selectedConnectionId, setSelectedConnectionId] = useState<string | null>(null);

  // Pipeline state (matches backend expectations)
  const [pipelineState, setPipelineState] = useState<PipelineState>(
    initialPipeline || {
      entry_points: [],
      modules: [],
      connections: []
    }
  );

  // Visual state (UI positioning only)
  const [visualState, setVisualState] = useState<VisualState>(
    initialVisual || {
      modules: {}
    }
  );

  // Map of module templates by ID for quick lookup
  const moduleTemplatesMap = moduleTemplates.reduce((acc, mod) => {
    acc[mod.id] = mod;
    return acc;
  }, {} as Record<string, ModuleTemplate>);

  // Helper function to get the name of the output connected to an input
  const getConnectedOutputName = (inputNodeId: string): string => {
    // Find connection where this input is the target
    const connection = pipelineState.connections.find(conn => conn.to_node_id === inputNodeId);
    if (!connection) return 'Not Connected';

    // Find the output node
    const outputNodeId = connection.from_node_id;

    // Check if it's an entry point
    const entryPoint = pipelineState.entry_points.find(ep => ep.node_id === outputNodeId);
    if (entryPoint) return entryPoint.name;

    // Otherwise, find the module and output
    for (const module of pipelineState.modules) {
      const outputNode = module.outputs.find(n => n.node_id === outputNodeId);
      if (outputNode) return outputNode.name;
    }

    return 'Not Connected';
  };

  // Notify parent of state changes
  useEffect(() => {
    if (onPipelineChange) {
      onPipelineChange(pipelineState);
    }
  }, [pipelineState]);

  useEffect(() => {
    if (onVisualChange) {
      onVisualChange(visualState);
    }
  }, [visualState]);

  // Track mouse movement for connection preview
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (startingConnection && canvasRef.current) {
        const canvasRect = canvasRef.current.getBoundingClientRect();
        const mouseX = (e.clientX - canvasRect.left - panOffset.x) / zoom;
        const mouseY = (e.clientY - canvasRect.top - panOffset.y) / zoom;
        setCurrentMousePosition({ x: mouseX, y: mouseY });
      }
    };

    if (startingConnection) {
      document.addEventListener('mousemove', handleMouseMove);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
      };
    }
  }, [startingConnection, panOffset, zoom]);

  // Keyboard shortcuts for deleting selected connection
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedConnectionId) {
        e.preventDefault();
        handleConnectionDelete(selectedConnectionId);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedConnectionId]);

  // Zoom controls
  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev * 1.2, 3)); // Max zoom 3x
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev * 0.8, 0.25)); // Min zoom 0.25x
  };

  const handleResetZoom = () => {
    // If there are modules, fit them all in view
    if (pipelineState.modules.length > 0 && canvasRef.current) {
      const positions = Object.values(visualState.modules);
      if (positions.length > 0) {
        // Calculate bounding box of all modules
        const xs = positions.map(p => p.x);
        const ys = positions.map(p => p.y);

        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);

        // Add padding around the bounding box (accounting for module size)
        const padding = 150; // Padding in canvas coordinates
        const boundingWidth = maxX - minX + padding * 2;
        const boundingHeight = maxY - minY + padding * 2;

        // Calculate center of bounding box
        const centerX = (minX + maxX) / 2;
        const centerY = (minY + maxY) / 2;

        // Get canvas dimensions
        const rect = canvasRef.current.getBoundingClientRect();
        const canvasWidth = rect.width;
        const canvasHeight = rect.height;

        // Calculate zoom to fit bounding box
        let newZoom = 1;
        if (boundingWidth > 0 && boundingHeight > 0) {
          const zoomX = canvasWidth / boundingWidth;
          const zoomY = canvasHeight / boundingHeight;
          newZoom = Math.min(zoomX, zoomY, 2); // Take smaller zoom, cap at 2x
          newZoom = Math.max(0.1, newZoom); // Minimum zoom of 0.1x
        }

        // Calculate pan to center the modules
        const newPanX = canvasWidth / 2 - centerX * newZoom;
        const newPanY = canvasHeight / 2 - centerY * newZoom;

        setZoom(newZoom);
        setPanOffset({ x: newPanX, y: newPanY });
      } else {
        // No module positions, just reset to defaults
        setZoom(1);
        setPanOffset({ x: 0, y: 0 });
      }
    } else {
      // No modules, just reset to defaults
      setZoom(1);
      setPanOffset({ x: 0, y: 0 });
    }
  };

  // Canvas mouse handlers
  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Only left mouse button

    // Don't start canvas drag if we're already dragging a module
    if (isDraggingModule) return;

    // Blur any active textarea when clicking canvas
    const activeElement = document.activeElement as HTMLElement;
    if (activeElement && activeElement.tagName === 'TEXTAREA') {
      activeElement.blur();
    }

    // Cancel any active connection when clicking empty canvas
    if (startingConnection) {
      setStartingConnection(null);
      return;
    }

    // Deselect module and connection if clicking on canvas background
    if (e.target === e.currentTarget) {
      setSelectedModuleId(null);
      setSelectedConnectionId(null);
    }

    // Start canvas dragging
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
    setDragStartOffset({ ...panOffset });

    e.preventDefault();
  };

  const handleCanvasMouseMove = (e: React.MouseEvent) => {
    // Mouse movement is handled by global listeners
  };

  const handleCanvasMouseUp = () => {
    if (!isDraggingModule) {
      setIsDragging(false);
    }
  };

  const handleCanvasMouseLeave = () => {
    if (!isDraggingModule) {
      setIsDragging(false);
    }
  };

  // Module handlers
  const handleModuleSelect = (moduleId: string) => {
    setSelectedModuleId(moduleId);
  };

  const handleAddNode = (moduleId: string, nodeType: 'input' | 'output', groupId?: string) => {
    const module = pipelineState.modules.find(m => m.module_instance_id === moduleId);

    // Don't allow adding nodes to entry points
    if (module?.module_ref === 'entry_point:1.0.0') return;

    const template = module ? moduleTemplatesMap[module.module_ref.split(':')[0]] : null;

    if (!module || !template) return;

    // If groupId is provided, use the new factory system with group support
    if (groupId) {
      // Create a temporary TypeVariableManager for this operation
      const typeVarManager = new TypeVariableManager();

      const newNode = addNodeToGroup(
        module,
        nodeType,
        groupId,
        template,
        typeVarManager
      );

      if (newNode) {
        setPipelineState(prev => ({
          ...prev,
          modules: prev.modules.map(m => m.module_instance_id === moduleId ? module : m)
        }));
      }
    } else {
      // Fallback to old system for backward compatibility
      const ioSide = nodeType === 'input' ? template.meta.io_shape.inputs : template.meta.io_shape.outputs;
      const newNode = addNodeToModule(module, nodeType, ioSide);

      if (newNode) {
        setPipelineState(prev => ({
          ...prev,
          modules: prev.modules.map(m => m.module_instance_id === moduleId ? module : m)
        }));
      }
    }
  };

  const handleRemoveNode = (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => {
    const module = pipelineState.modules.find(m => m.module_instance_id === moduleId);

    // Don't allow removing nodes from entry points
    if (module?.module_ref === 'entry_point:1.0.0') return;

    const template = module ? moduleTemplatesMap[module.module_ref.split(':')[0]] : null;

    if (!module || !template) return;

    const ioSide = nodeType === 'input' ? template.meta.io_shape.inputs : template.meta.io_shape.outputs;
    const removedNodeId = removeNodeFromModule(module, nodeType, nodeIndex, ioSide);

    if (removedNodeId) {
      // Update pipeline state
      setPipelineState(prev => ({
        ...prev,
        modules: prev.modules.map(m => m.module_instance_id === moduleId ? module : m),
        // Remove connections to/from the removed node
        connections: prev.connections.filter(conn =>
          conn.from_node_id !== removedNodeId && conn.to_node_id !== removedNodeId
        )
      }));
    }
  };

  const handleNodeTypeChange = (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newType: string) => {
    setPipelineState(prev => ({
      ...prev,
      modules: prev.modules.map(module => {
        if (module.module_instance_id === moduleId) {
          const nodes = nodeType === 'input' ? module.inputs : module.outputs;
          if (nodeIndex >= 0 && nodeIndex < nodes.length) {
            nodes[nodeIndex].type = newType;
          }
        }
        return module;
      })
    }));
  };

  const handleNodeNameChange = (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newName: string) => {
    setPipelineState(prev => ({
      ...prev,
      modules: prev.modules.map(module => {
        if (module.module_instance_id === moduleId) {
          const nodes = nodeType === 'input' ? module.inputs : module.outputs;
          if (nodeIndex >= 0 && nodeIndex < nodes.length) {
            nodes[nodeIndex].name = newName;
          }
        }
        return module;
      })
    }));
  };

  const handleNodeClick = (moduleId: string, nodeId: string, nodeType: 'input' | 'output') => {
    if (!startingConnection) {
      // Check if this node has existing connections
      const existingConnections = pipelineState.connections.filter(conn => {
        if (nodeType === 'output') {
          // Output nodes can only have one connection (one-to-one)
          return conn.from_node_id === nodeId;
        } else {
          // Input nodes can only have one connection
          return conn.to_node_id === nodeId;
        }
      });

      if (existingConnections.length > 0) {
        // Enter connection editing mode
        console.log(`Editing connection(s) from ${moduleId}[${nodeType}:${nodeId}]`);

        // Don't select connections when editing - they'll be temporarily removed

        // For visual feedback, start from the OPPOSITE node (the anchored one)
        // But store that we clicked this node for the completion logic
        const firstConn = existingConnections[0];
        const oppositeNodeId = nodeType === 'output' ? firstConn.to_node_id : firstConn.from_node_id;
        const oppositeNodeType = nodeType === 'output' ? 'input' : 'output';

        // Find the module containing the opposite node
        let oppositeModuleId = '';
        for (const module of pipelineState.modules) {
          if (oppositeNodeType === 'input') {
            if (module.inputs.some(n => n.node_id === oppositeNodeId)) {
              oppositeModuleId = module.module_instance_id;
              break;
            }
          } else {
            if (module.outputs.some(n => n.node_id === oppositeNodeId)) {
              oppositeModuleId = module.module_instance_id;
              break;
            }
          }
        }

        // Start from opposite (anchored) node, store clicked node info
        setStartingConnection({
          moduleId: oppositeModuleId,
          nodeId: oppositeNodeId,
          nodeType: oppositeNodeType,
          editingConnections: existingConnections,
          clickedNodeId: nodeId, // Store which node was clicked to move
          clickedNodeType: nodeType // Store type of clicked node
        } as any);

        // Remove the existing connections temporarily
        setPipelineState(prev => ({
          ...prev,
          connections: prev.connections.filter(conn =>
            !existingConnections.includes(conn)
          )
        }));
      } else {
        // Start new connection normally
        console.log(`Starting connection from ${moduleId}[${nodeType}:${nodeId}]`);
        setStartingConnection({ moduleId, nodeId, nodeType });
      }

      // Initialize mouse position to the starting node position (will be updated by mouse move)
      const nodeElement = document.querySelector(`[data-node-id="${nodeId}"]`);
      if (nodeElement && canvasRef.current) {
        const rect = nodeElement.getBoundingClientRect();
        const canvasRect = canvasRef.current.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2 - canvasRect.left;
        const centerY = rect.top + rect.height / 2 - canvasRect.top;
        setCurrentMousePosition({
          x: (centerX - panOffset.x) / zoom,
          y: (centerY - panOffset.y) / zoom
        });
      }
    } else {
      // Try to complete connection
      const start = startingConnection;

      // Can only connect output to input or input to output
      if (start.nodeType !== nodeType) {
        // Determine which is output and which is input
        let fromNodeId = start.nodeType === 'output' ? start.nodeId : nodeId;
        let toNodeId = start.nodeType === 'input' ? start.nodeId : nodeId;

        // If we're editing existing connections
        if (start.editingConnections) {
          // The clicked node is being moved to the target node
          // The anchored node stays where it was (start.nodeId)

          // The visual starts from the anchored node (start.nodeId)
          // The clicked node type tells us what was clicked to be moved
          if ((start as any).clickedNodeType === 'output') {
            // User clicked an output, wanting to connect it to a different input
            // The anchored node is the input (start.nodeId is the input)
            // The new target (nodeId) becomes the new output
            fromNodeId = nodeId; // Target node is the new output
            toNodeId = start.nodeId; // Anchored input
          } else {
            // User clicked an input, wanting to connect it to a different output
            // The anchored node is the output (start.nodeId is the output)
            // The new target (nodeId) becomes the new input
            fromNodeId = start.nodeId; // Anchored output
            toNodeId = nodeId; // Target node is the new input
          }
        }

        // For both editing and new connections, remove existing connections and add the new one
        setPipelineState(prev => ({
          ...prev,
          connections: [
            ...prev.connections.filter(conn =>
              conn.to_node_id !== toNodeId && conn.from_node_id !== fromNodeId
            ),
            { from_node_id: fromNodeId, to_node_id: toNodeId }
          ]
        }));

        console.log(`Connection created/updated: ${fromNodeId} -> ${toNodeId}`);

        // Reset starting connection
        setStartingConnection(null);
        setCurrentMousePosition({ x: 0, y: 0 });
      } else {
        // Can't connect same type nodes
        console.log('Cannot connect', nodeType, 'to', nodeType);
        setStartingConnection(null);
        setCurrentMousePosition({ x: 0, y: 0 });
      }
    }
  };

  const handleConfigChange = (moduleId: string, config: Record<string, any>) => {
    setPipelineState(prev => ({
      ...prev,
      modules: prev.modules.map(module =>
        module.module_instance_id === moduleId
          ? { ...module, config }
          : module
      )
    }));
  };

  // Connection helper functions
  const getNodeType = (nodeId: string): string => {
    // Find the module and node to get its type
    for (const module of pipelineState.modules) {
      const inputNode = module.inputs.find(n => n.node_id === nodeId);
      if (inputNode) return inputNode.type;

      const outputNode = module.outputs.find(n => n.node_id === nodeId);
      if (outputNode) return outputNode.type;
    }
    return 'string'; // Default type
  };

  const getTypeColor = (type: string): string => {
    switch (type) {
      case 'string': return '#3B82F6'; // Blue
      case 'number': return '#EF4444'; // Red
      case 'boolean': return '#10B981'; // Green
      case 'datetime': return '#F59E0B'; // Amber
      default: return '#6B7280'; // Gray for undefined
    }
  };

  const handleConnectionClick = (connectionId: string) => {
    setSelectedConnectionId(connectionId);
    setSelectedModuleId(null); // Deselect module when selecting connection
  };

  const handleConnectionDelete = (connectionId: string) => {
    // Parse the connection ID (format: "fromNodeId-toNodeId")
    const [fromNodeId, toNodeId] = connectionId.split('-');

    setPipelineState(prev => ({
      ...prev,
      connections: prev.connections.filter(conn =>
        !(conn.from_node_id === fromNodeId && conn.to_node_id === toNodeId)
      )
    }));

    setSelectedConnectionId(null);
  };

  const handleModuleMouseDown = (moduleId: string) => (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Only left mouse button

    e.preventDefault(); // Prevent text selection
    e.stopPropagation();

    // Get current module position
    const currentPosition = visualState.modules[moduleId];
    if (!currentPosition || !canvasRef.current) return;

    const canvasRect = canvasRef.current.getBoundingClientRect();

    // Calculate mouse position in canvas coordinates
    const mouseX = (e.clientX - canvasRect.left - panOffset.x) / zoom;
    const mouseY = (e.clientY - canvasRect.top - panOffset.y) / zoom;

    // Calculate offset from mouse to module center
    const offsetX = mouseX - currentPosition.x;
    const offsetY = mouseY - currentPosition.y;

    setIsDraggingModule(true);
    setDraggedModuleId(moduleId);
    setModuleDragOffset({ x: offsetX, y: offsetY });
    setTemporaryPosition(currentPosition); // Start with current position
  };

  const handleModuleDelete = (moduleId: string) => {
    // Remove from pipeline state
    setPipelineState(prev => ({
      ...prev,
      modules: prev.modules.filter(m => m.module_instance_id !== moduleId),
      // Also remove any connections to/from this module's nodes
      connections: prev.connections.filter(conn => {
        const moduleToDelete = prev.modules.find(m => m.module_instance_id === moduleId);
        if (!moduleToDelete) return true;

        const nodeIds = [
          ...moduleToDelete.inputs.map(n => n.node_id),
          ...moduleToDelete.outputs.map(n => n.node_id)
        ];

        return !nodeIds.includes(conn.from_node_id) && !nodeIds.includes(conn.to_node_id);
      })
    }));

    // Remove from visual state
    setVisualState(prev => {
      const newModules = { ...prev.modules };
      delete newModules[moduleId];
      return { ...prev, modules: newModules };
    });

    // Clear selection if deleted module was selected
    if (selectedModuleId === moduleId) {
      setSelectedModuleId(null);
    }
  };

  // Handle module drop
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    try {
      const dragData = JSON.parse(e.dataTransfer.getData('application/json'));

      if (dragData.type === 'module') {
        const moduleTemplate = moduleTemplatesMap[dragData.moduleId];
        if (!moduleTemplate) {
          console.error('Module template not found:', dragData.moduleId);
          return;
        }

        // Calculate drop position in canvas coordinates
        const rect = canvasRef.current?.getBoundingClientRect();
        if (!rect) return;

        const dropX = (e.clientX - rect.left - panOffset.x) / zoom;
        const dropY = (e.clientY - rect.top - panOffset.y) / zoom;

        // Create new module instance using new factory
        const { moduleInstance, typeVarManager } = createModuleInstance(moduleTemplate, { x: dropX, y: dropY });

        // Update pipeline state
        setPipelineState(prev => ({
          ...prev,
          modules: [...prev.modules, moduleInstance]
        }));

        // Update visual state
        setVisualState(prev => ({
          ...prev,
          modules: {
            ...prev.modules,
            [moduleInstance.module_instance_id]: { x: dropX, y: dropY }
          }
        }));

        // Select the newly placed module
        setSelectedModuleId(moduleInstance.module_instance_id);

        console.log('Module placed:', moduleInstance.module_instance_id, 'at', dropX, dropY);
      }
    } catch (error) {
      console.error('Failed to handle drop:', error);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  };

  // Global mouse event handlers for dragging
  useEffect(() => {
    const handleGlobalMouseMove = (e: MouseEvent) => {
      if (isDraggingModule && draggedModuleId && canvasRef.current) {
        e.preventDefault();
        e.stopPropagation();

        const canvasRect = canvasRef.current.getBoundingClientRect();

        // Calculate new position
        const mouseX = (e.clientX - canvasRect.left - panOffset.x) / zoom;
        const mouseY = (e.clientY - canvasRect.top - panOffset.y) / zoom;

        const newX = mouseX - moduleDragOffset.x;
        const newY = mouseY - moduleDragOffset.y;

        // Update temporary position for visual feedback
        setTemporaryPosition({ x: newX, y: newY });
      } else if (isDragging) {
        // Handle canvas panning
        const deltaX = e.clientX - dragStart.x;
        const deltaY = e.clientY - dragStart.y;

        setPanOffset({
          x: dragStartOffset.x + deltaX,
          y: dragStartOffset.y + deltaY
        });
      }
    };

    const handleGlobalMouseUp = (e: MouseEvent) => {
      if (isDraggingModule && draggedModuleId && temporaryPosition) {
        e.preventDefault();
        e.stopPropagation();

        // Check if it's an entry point or a module
        const isEntryPoint = pipelineState.entry_points.some(ep => ep.node_id === draggedModuleId);

        // Update visual state with final position
        if (isEntryPoint) {
          setVisualState(prev => ({
            ...prev,
            entryPoints: {
              ...prev.entryPoints,
              [draggedModuleId]: temporaryPosition
            }
          }));
        } else {
          setVisualState(prev => ({
            ...prev,
            modules: {
              ...prev.modules,
              [draggedModuleId]: temporaryPosition
            }
          }));
        }

        // Reset dragging state
        setIsDraggingModule(false);
        setDraggedModuleId(null);
        setTemporaryPosition(null);
      }

      // Always stop canvas dragging
      if (isDragging) {
        setIsDragging(false);
      }
    };

    // Use capture phase to ensure we get events first
    document.addEventListener('mousemove', handleGlobalMouseMove, true);
    document.addEventListener('mouseup', handleGlobalMouseUp, true);

    return () => {
      document.removeEventListener('mousemove', handleGlobalMouseMove, true);
      document.removeEventListener('mouseup', handleGlobalMouseUp, true);
    };
  }, [isDraggingModule, draggedModuleId, moduleDragOffset, temporaryPosition, panOffset, zoom, isDragging, dragStart, dragStartOffset]);

  // Remove all keyboard shortcuts - typing should only affect input fields
  // (Removed keyboard event listeners to prevent interference with typing)

  // Wheel event handler for zoom
  useEffect(() => {
    const handleWheel = (e: WheelEvent) => {
      if (!canvasRef.current || !canvasRef.current.contains(e.target as Node)) return;

      e.preventDefault();

      const rect = canvasRef.current.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      // Calculate new zoom
      const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
      const newZoom = Math.max(0.25, Math.min(3, zoom * zoomFactor));

      // Adjust pan to keep mouse position stable
      const zoomRatio = newZoom / zoom;
      const newPanX = mouseX - (mouseX - panOffset.x) * zoomRatio;
      const newPanY = mouseY - (mouseY - panOffset.y) * zoomRatio;

      setZoom(newZoom);
      setPanOffset({ x: newPanX, y: newPanY });
    };

    window.addEventListener('wheel', handleWheel, { passive: false });
    return () => window.removeEventListener('wheel', handleWheel);
  }, [zoom, panOffset]);

  // Calculate adaptive grid size based on zoom level
  const getGridSize = (zoomLevel: number) => {
    if (zoomLevel <= 0.25) {
      return 100; // Large grid for very zoomed out
    } else if (zoomLevel <= 0.5) {
      return 50; // Medium grid for moderately zoomed out
    } else {
      return 20; // Fine grid for normal/zoomed in
    }
  };

  // Calculate grid opacity based on zoom level
  const getGridOpacity = (zoomLevel: number) => {
    if (zoomLevel <= 0.25) {
      return 0.2; // Less visible when very zoomed out
    } else if (zoomLevel <= 0.5) {
      return 0.25; // Slightly more visible
    } else {
      return 0.3; // Normal visibility
    }
  };

  return (
    <div className="flex-1 relative overflow-hidden bg-gray-900">
      {/* Canvas */}
      <div
        ref={canvasRef}
        className="absolute inset-0 transformation-graph-canvas"
        onMouseDown={handleCanvasMouseDown}
        onMouseMove={handleCanvasMouseMove}
        onMouseUp={handleCanvasMouseUp}
        onMouseLeave={handleCanvasMouseLeave}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        style={{
          cursor: isDraggingModule ? 'grabbing' : (isDragging ? 'grabbing' : 'grab'),
          backgroundImage: `
            linear-gradient(rgba(75, 85, 99, ${getGridOpacity(zoom)}) 1px, transparent 1px),
            linear-gradient(90deg, rgba(75, 85, 99, ${getGridOpacity(zoom)}) 1px, transparent 1px)
          `,
          backgroundSize: `${getGridSize(zoom) * zoom}px ${getGridSize(zoom) * zoom}px`,
          backgroundPosition: `${panOffset.x}px ${panOffset.y}px`
        }}
      >
        {/* Transform container for zoom and pan */}
        <div
          className="absolute inset-0 origin-top-left"
          style={{
            transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoom})`,
            pointerEvents: 'auto'
          }}
        >
          {/* Modules and Entry Points will be rendered here */}
          <div className="absolute inset-0" style={{ zIndex: 1 }}>
            {/* Entry Points */}
            {pipelineState.entry_points.map((entryPoint, index) => {
              // Use temporary position if this entry point is being dragged, otherwise use visual state
              const position = (isDraggingModule && draggedModuleId === entryPoint.node_id && temporaryPosition)
                ? temporaryPosition
                : (visualState.entryPoints?.[entryPoint.node_id] || { x: 100, y: 100 + index * 100 });

              // Higher z-index for dragged entry point
              const zIndex = (isDraggingModule && draggedModuleId === entryPoint.node_id) ? 1000 : index;

              return (
                <div
                  key={entryPoint.node_id}
                  style={{
                    position: 'absolute',
                    zIndex: zIndex
                  }}
                >
                  <EntryPointComponent
                    entryPoint={entryPoint}
                    position={position}
                    isSelected={selectedModuleId === entryPoint.node_id}
                    onSelect={(nodeId) => setSelectedModuleId(nodeId)}
                    onMouseDown={(e) => {
                      const nodeId = entryPoint.node_id;
                      setSelectedModuleId(nodeId);
                      setIsDraggingModule(true);
                      setDraggedModuleId(nodeId);

                      // Calculate offset from mouse to module position
                      // Module is already centered horizontally due to transform
                      const moduleX = position.x * zoom + panOffset.x;
                      const moduleY = position.y * zoom + panOffset.y;

                      const canvasRect = canvasRef.current?.getBoundingClientRect();
                      if (canvasRect) {
                        const mouseX = e.clientX - canvasRect.left;
                        const mouseY = e.clientY - canvasRect.top;

                        setModuleDragOffset({
                          x: (mouseX - moduleX) / zoom,
                          y: (mouseY - moduleY) / zoom
                        });
                      }

                      setTemporaryPosition(position);
                    }}
                    onDelete={(nodeId) => {
                      // Remove entry point and its connections
                      setPipelineState(prev => ({
                        ...prev,
                        entry_points: prev.entry_points.filter(ep => ep.node_id !== nodeId),
                        connections: prev.connections.filter(conn =>
                          conn.from_node_id !== nodeId && conn.to_node_id !== nodeId
                        )
                      }));

                      // Remove visual position
                      setVisualState(prev => {
                        const newEntryPoints = { ...prev.entryPoints };
                        delete newEntryPoints[nodeId];
                        return { ...prev, entryPoints: newEntryPoints };
                      });
                    }}
                    onNameChange={(nodeId, name) => {
                      setPipelineState(prev => ({
                        ...prev,
                        entry_points: prev.entry_points.map(ep =>
                          ep.node_id === nodeId ? { ...ep, name } : ep
                        )
                      }));
                    }}
                    onNodeClick={(nodeId) => {
                      handleNodeClick(`entry-${nodeId}`, nodeId, 'output');
                    }}
                  />
                </div>
              );
            })}

            {/* Regular Modules */}
            {pipelineState.modules.map((module, index) => {
              // Use temporary position if this module is being dragged, otherwise use visual state
              const position = (isDraggingModule && draggedModuleId === module.module_instance_id && temporaryPosition)
                ? temporaryPosition
                : (visualState.modules[module.module_instance_id] || { x: 0, y: 0 });

              // Check if this is an entry point module
              let template;
              if (module.module_ref === 'entry_point:1.0.0') {
                // Create a special template for entry point modules
                template = {
                  module_ref: 'entry_point:1.0.0',
                  id: 'entry_point',
                  version: '1.0.0',
                  title: 'Entry Point',
                  description: 'Pipeline entry point',
                  kind: 'transform',
                  meta: {
                    inputs: { allow: false, min_count: 0, max_count: 0, type: [] },
                    outputs: { allow: false, min_count: 1, max_count: 1, type: ['string'] }
                  },
                  config_schema: {},
                  category: 'Entry',
                  color: '#FFFFFF' // White color for entry points
                };
              } else {
                template = moduleTemplatesMap[module.module_ref.split(':')[0]];

                if (!template) {
                  console.warn('Template not found for module:', module.module_ref);
                  return null;
                }
              }

              // Higher z-index for dragged module
              const zIndex = (isDraggingModule && draggedModuleId === module.module_instance_id) ? 1000 : index;

              return (
                <div
                  key={module.module_instance_id}
                  style={{
                    position: 'absolute',
                    zIndex: zIndex
                  }}
                >
                  <ModuleComponent
                    module={module}
                    template={template}
                    position={position}
                    isSelected={selectedModuleId === module.module_instance_id}
                    getConnectedOutputName={getConnectedOutputName}
                    onSelect={handleModuleSelect}
                    onMouseDown={handleModuleMouseDown(module.module_instance_id)}
                    onDelete={handleModuleDelete}
                    onAddNode={handleAddNode}
                    onRemoveNode={handleRemoveNode}
                    onNodeTypeChange={handleNodeTypeChange}
                    onNodeNameChange={handleNodeNameChange}
                    onNodeClick={handleNodeClick}
                    onConfigChange={handleConfigChange}
                  />
                </div>
              );
            })}
          </div>

          {/* Connection Layer - Behind modules for proper click priority */}
          <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 0 }}>
            <ConnectionLayer
              connections={pipelineState.connections}
              selectedConnectionId={selectedConnectionId}
              startingConnection={startingConnection}
              currentMousePosition={currentMousePosition}
              modulePositions={(() => {
                // Use temporary position for dragged module
                if (isDraggingModule && draggedModuleId && temporaryPosition) {
                  return {
                    ...visualState.modules,
                    [draggedModuleId]: temporaryPosition
                  };
                }
                return visualState.modules;
              })()}
              modules={pipelineState.modules}
              zoom={zoom}
              panOffset={panOffset}
              getNodeType={getNodeType}
              getTypeColor={getTypeColor}
              onConnectionClick={handleConnectionClick}
              onConnectionDelete={handleConnectionDelete}
            />
          </div>
        </div>
      </div>

      {/* Top Controls Bar */}
      <div className="absolute top-4 right-4 z-20 flex gap-4">
        {/* Save Pipeline Button */}
        <button
          onClick={() => {
            // Prepare the pipeline data for saving
            const pipelineData = {
              schema_version: '1.0.0',
              name: 'Untitled Pipeline',
              description: 'Pipeline created in visual editor',
              pipeline_json: pipelineState,
              visual_json: visualState
            };

            console.log('=== SAVING PIPELINE ===');
            console.log(JSON.stringify(pipelineData, null, 2));
            console.log('======================');

            // TODO: Call API to save pipeline
            alert('Pipeline save functionality coming soon!\nCheck console for pipeline data.');
          }}
          className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg shadow-lg border border-gray-700 font-medium"
        >
          Save Pipeline
        </button>

        {/* Zoom Controls */}
        <div className="flex flex-col bg-gray-800 rounded-lg shadow-lg border border-gray-700">
        <button
          onClick={handleZoomIn}
          className="w-10 h-10 flex items-center justify-center text-white hover:bg-gray-700 transition-colors rounded-t-lg border-b border-gray-700"
          title="Zoom In"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
        </button>

        <div className="w-10 h-8 flex items-center justify-center text-xs text-gray-400 border-b border-gray-700">
          {Math.round(zoom * 100)}%
        </div>

        <button
          onClick={handleZoomOut}
          className="w-10 h-10 flex items-center justify-center text-white hover:bg-gray-700 transition-colors border-b border-gray-700"
          title="Zoom Out"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 12H6" />
          </svg>
        </button>

        <button
          onClick={handleResetZoom}
          className="w-10 h-10 flex items-center justify-center text-white hover:bg-gray-700 transition-colors rounded-b-lg"
          title="Fit All to View"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </button>
        </div>
      </div>

      {/* Debug Info and Controls */}
      <div className="absolute bottom-4 left-4 bg-gray-800 rounded p-2 text-xs text-gray-400">
        <div>Zoom: {(zoom * 100).toFixed(0)}%</div>
        <div>Pan: ({panOffset.x.toFixed(0)}, {panOffset.y.toFixed(0)})</div>
        <div>Modules: {pipelineState.modules.length}</div>
        <div>Connections: {pipelineState.connections.length}</div>
        <div>Entry Points: {pipelineState.entry_points.length}</div>
        <button
          onClick={() => {
            console.log('=== PIPELINE STATE ===');
            console.log(JSON.stringify(pipelineState, null, 2));
            console.log('=== VISUAL STATE ===');
            console.log(JSON.stringify(visualState, null, 2));
            console.log('=====================');
          }}
          className="mt-2 px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs"
        >
          Print State to Console
        </button>
        <button
          onClick={() => {
            // Create a new entry point
            const nodeId = `N${Date.now()}`;
            const newEntryPoint = {
              node_id: nodeId,
              name: `Entry ${pipelineState.entry_points.length + 1}`,
              type: 'str' // Default to string type
            };

            setPipelineState(prev => ({
              ...prev,
              entry_points: [...prev.entry_points, newEntryPoint]
            }));

            // Add visual position for the entry point (center of viewport)
            if (canvasRef.current) {
              const rect = canvasRef.current.getBoundingClientRect();
              const centerX = (rect.width / 2 - panOffset.x) / zoom;
              const centerY = (rect.height / 2 - panOffset.y) / zoom;

              setVisualState(prev => ({
                ...prev,
                entryPoints: {
                  ...prev.entryPoints,
                  [nodeId]: { x: centerX, y: centerY }
                }
              }));
            }
          }}
          className="mt-1 px-2 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-xs w-full"
        >
          Add Entry Point (Old)
        </button>
        <button
          onClick={() => {
            // Create a new entry point as a module
            const timestamp = Date.now();
            const moduleId = `E${timestamp}`;
            const outputNodeId = `N${timestamp}_out`;

            // Create a special module that acts as an entry point
            const entryPointModule = {
              module_instance_id: moduleId,
              module_ref: 'entry_point:1.0.0', // Special module ref for entry points
              module_kind: 'transform' as const,
              config: {},
              inputs: [], // No inputs for entry points
              outputs: [{
                node_id: outputNodeId,
                direction: 'out' as const,
                type: 'string',
                name: `Entry ${pipelineState.modules.filter(m => m.module_ref === 'entry_point:1.0.0').length + 1}`,
                position_index: 0
              }]
            };

            setPipelineState(prev => ({
              ...prev,
              modules: [...prev.modules, entryPointModule]
            }));

            // Add visual position for the module (center of viewport)
            if (canvasRef.current) {
              const rect = canvasRef.current.getBoundingClientRect();
              const centerX = (rect.width / 2 - panOffset.x) / zoom;
              const centerY = (rect.height / 2 - panOffset.y) / zoom;

              setVisualState(prev => ({
                ...prev,
                modules: {
                  ...prev.modules,
                  [moduleId]: { x: centerX, y: centerY }
                }
              }));
            }

            console.log('Added entry point module:', moduleId);
          }}
          className="mt-1 px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs w-full"
        >
          Add Entry Point (Module)
        </button>
      </div>

      {/* Connection Info Overlay */}
      <ConnectionInfoOverlay
        selectedConnectionId={selectedConnectionId}
        connections={pipelineState.connections}
        modules={pipelineState.modules}
        moduleTemplates={moduleTemplates}
        onDelete={() => {
          if (selectedConnectionId) {
            handleConnectionDelete(selectedConnectionId);
          }
        }}
        onClose={() => setSelectedConnectionId(null)}
      />
    </div>
  );
};