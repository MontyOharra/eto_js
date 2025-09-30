import React, { useState, useRef, useEffect } from 'react';
import {
  ModuleTemplate,
  ModuleInstance,
  PipelineState,
  VisualState,
  PipelineData
} from '../../types/pipelineTypes';
import { createModuleInstance, addNodeToModule, removeNodeFromModule, updateNodeType } from '../../utils/moduleFactory';
import { ModuleComponentNew } from './ModuleComponentNew';

interface TransformationGraphNewProps {
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

export const TransformationGraphNew: React.FC<TransformationGraphNewProps> = ({
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

    // Deselect module if clicking on canvas background
    if (e.target === e.currentTarget) {
      setSelectedModuleId(null);
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

  const handleAddNode = (moduleId: string, nodeType: 'input' | 'output') => {
    const module = pipelineState.modules.find(m => m.module_instance_id === moduleId);
    const template = module ? moduleTemplatesMap[module.module_ref.split(':')[0]] : null;

    if (!module || !template) return;

    const meta = nodeType === 'input' ? template.meta.inputs : template.meta.outputs;
    const newNode = addNodeToModule(module, nodeType, meta);

    if (newNode) {
      setPipelineState(prev => ({
        ...prev,
        modules: prev.modules.map(m => m.module_instance_id === moduleId ? module : m)
      }));
    }
  };

  const handleRemoveNode = (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => {
    const module = pipelineState.modules.find(m => m.module_instance_id === moduleId);
    const template = module ? moduleTemplatesMap[module.module_ref.split(':')[0]] : null;

    if (!module || !template) return;

    const meta = nodeType === 'input' ? template.meta.inputs : template.meta.outputs;
    const removedNodeId = removeNodeFromModule(module, nodeType, nodeIndex, meta);

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
    // This will be used for connection creation later
    console.log('Node clicked:', moduleId, nodeId, nodeType);
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

        // Create new module instance
        const moduleInstance = createModuleInstance(moduleTemplate, { x: dropX, y: dropY });

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

        // Update visual state with final position
        setVisualState(prev => ({
          ...prev,
          modules: {
            ...prev.modules,
            [draggedModuleId]: temporaryPosition
          }
        }));

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

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Delete selected module
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedModuleId) {
        handleModuleDelete(selectedModuleId);
      }

      // Deselect on Escape
      if (e.key === 'Escape') {
        setSelectedModuleId(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedModuleId]);

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
        className="absolute inset-0"
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
          {/* Modules will be rendered here */}
          <div className="absolute inset-0">
            {pipelineState.modules.map(module => {
              // Use temporary position if this module is being dragged, otherwise use visual state
              const position = (isDraggingModule && draggedModuleId === module.module_instance_id && temporaryPosition)
                ? temporaryPosition
                : (visualState.modules[module.module_instance_id] || { x: 0, y: 0 });

              const template = moduleTemplatesMap[module.module_ref.split(':')[0]];

              if (!template) {
                console.warn('Template not found for module:', module.module_ref);
                return null;
              }

              return (
                <ModuleComponentNew
                  key={module.module_instance_id}
                  module={module}
                  template={template}
                  position={position}
                  isSelected={selectedModuleId === module.module_instance_id}
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
              );
            })}
          </div>
        </div>
      </div>

      {/* Zoom Controls - Top Right */}
      <div className="absolute top-4 right-4 z-20 flex flex-col bg-gray-800 rounded-lg shadow-lg border border-gray-700">
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

      {/* Debug Info (temporary) */}
      <div className="absolute bottom-4 left-4 bg-gray-800 rounded p-2 text-xs text-gray-400">
        <div>Zoom: {(zoom * 100).toFixed(0)}%</div>
        <div>Pan: ({panOffset.x.toFixed(0)}, {panOffset.y.toFixed(0)})</div>
        <div>Modules: {pipelineState.modules.length}</div>
        <div>Connections: {pipelineState.connections.length}</div>
      </div>
    </div>
  );
};