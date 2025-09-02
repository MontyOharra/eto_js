import { createFileRoute } from "@tanstack/react-router";
import { useState, useRef, useEffect } from "react";
import { ModuleSelectionPane } from "../../components/ModuleSelectionPane";
import { GraphModuleComponent } from "../../components/GraphModuleComponent";
import { testBaseModules, BaseModuleTemplate } from "../../data/testModules";

export const Route = createFileRoute("/transformation_pipeline/graph")({
  component: TransformationPipelineGraph,
});

interface PlacedModule {
  id: string;
  template: BaseModuleTemplate;
  position: { x: number; y: number };
  config: any;
}

function TransformationPipelineGraph() {
  const [zoom, setZoom] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [dragStartOffset, setDragStartOffset] = useState({ x: 0, y: 0 });
  const canvasRef = useRef<HTMLDivElement>(null);

  // Module selection and placement state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [selectedModuleTemplate, setSelectedModuleTemplate] = useState<BaseModuleTemplate | null>(null);
  const [placedModules, setPlacedModules] = useState<PlacedModule[]>([]);
  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);
  
  // Placement state
  const [isPlacingModule, setIsPlacingModule] = useState(false);
  const [placementStartPos, setPlacementStartPos] = useState({ x: 0, y: 0 });

  // Module dragging state
  const [isDraggingModule, setIsDraggingModule] = useState(false);
  const [draggedModuleId, setDraggedModuleId] = useState<string | null>(null);
  const [moduleDragOffset, setModuleDragOffset] = useState({ x: 0, y: 0 });

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

  // Zoom utility functions
  const zoomIn = () => {
    setZoom(prev => Math.min(prev * 1.2, 3)); // Max zoom 3x
  };

  const zoomOut = () => {
    setZoom(prev => Math.max(prev / 1.2, 0.1)); // Min zoom 0.1x
  };

  const resetZoom = () => {
    setZoom(1);
    setPanOffset({ x: 0, y: 0 });
  };

  // Handle scroll wheel zoom
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    
    // Disable zooming when dragging a module
    if (isDraggingModule) return;
    
    if (!canvasRef.current) return;
    
    const canvasRect = canvasRef.current.getBoundingClientRect();
    const mouseX = e.clientX - canvasRect.left;
    const mouseY = e.clientY - canvasRect.top;
    
    // Zoom factor
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.max(0.1, Math.min(3, zoom * zoomFactor));
    
    if (newZoom !== zoom) {
      // Calculate pan offset to zoom towards mouse position
      const zoomRatio = newZoom / zoom;
      const newPanX = mouseX - (mouseX - panOffset.x) * zoomRatio;
      const newPanY = mouseY - (mouseY - panOffset.y) * zoomRatio;
      
      setZoom(newZoom);
      setPanOffset({ x: newPanX, y: newPanY });
    }
  };

  // Handle mouse down for canvas - either place module or start canvas drag
  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    console.log('🖱️ Canvas mouse down', { button: e.button, selectedModuleTemplate: !!selectedModuleTemplate, selectedModuleId });
    
    if (e.button !== 0) return; // Only left mouse button
    
    // If module is selected, start placement
    if (selectedModuleTemplate) {
      handleModulePlacementStart(e);
      return;
    }
    
    // Deselect any selected module when clicking empty canvas
    setSelectedModuleId(null);
    
    // Only start canvas dragging if no module is currently selected
    // This prevents canvas movement when interacting with module configurations
    if (selectedModuleId === null) {
      console.log('🎯 Starting canvas drag');
      setIsDragging(true);
      setDragStart({ x: e.clientX, y: e.clientY });
      setDragStartOffset({ ...panOffset });
    }
    
    // Prevent text selection during drag
    e.preventDefault();
  };

  // Handle module placement start
  const handleModulePlacementStart = (e: React.MouseEvent) => {
    if (!selectedModuleTemplate || !canvasRef.current) return;
    
    const canvasRect = canvasRef.current.getBoundingClientRect();
    const clickX = (e.clientX - canvasRect.left - panOffset.x) / zoom;
    const clickY = (e.clientY - canvasRect.top - panOffset.y) / zoom;
    
    setIsPlacingModule(true);
    setPlacementStartPos({ x: clickX, y: clickY });
    
    // Create and place module immediately on click
    const newModule: PlacedModule = {
      id: `${selectedModuleTemplate.id}_${Date.now()}`,
      template: selectedModuleTemplate,
      position: { x: clickX, y: clickY },
      config: {}
    };
    
    setPlacedModules(prev => [...prev, newModule]);
    
    e.preventDefault();
  };

  // Handle mouse move for module placement only (canvas dragging is now global)
  const handleCanvasMouseMove = (e: React.MouseEvent) => {
    // If placing module and dragging, update the most recent module position
    if (isPlacingModule && selectedModuleTemplate && canvasRef.current) {
      const canvasRect = canvasRef.current.getBoundingClientRect();
      const mouseX = (e.clientX - canvasRect.left - panOffset.x) / zoom;
      const mouseY = (e.clientY - canvasRect.top - panOffset.y) / zoom;
      
      // Update the position of the most recently placed module
      setPlacedModules(prev => {
        if (prev.length === 0) return prev;
        const updatedModules = [...prev];
        updatedModules[updatedModules.length - 1] = {
          ...updatedModules[updatedModules.length - 1],
          position: { x: mouseX, y: mouseY }
        };
        return updatedModules;
      });
    }
  };

  // Handle mouse up - only for module placement, not for dragging (global handlers manage dragging)
  const handleCanvasMouseUp = () => {
    console.log('🖱️ Canvas mouse up');
    // Only handle module placement cleanup, NOT dragging
    if (isPlacingModule) {
      console.log('🛑 Stopping module placement (mouse up)');
      setSelectedModuleTemplate(null);
      setIsPlacingModule(false);
    }
    
    // DO NOT stop dragging here - let global handlers manage that
  };

  // Handle mouse leave - only for module placement, not for dragging (global handlers manage dragging)
  const handleCanvasMouseLeave = () => {
    console.log('🚪 Canvas mouse leave');
    // Only handle module placement cleanup, NOT dragging
    if (isPlacingModule) {
      console.log('🛑 Stopping module placement (mouse leave)');
      setSelectedModuleTemplate(null);
      setIsPlacingModule(false);
    }
    
    // DO NOT stop dragging here - let global handlers manage that
  };

  // Module selection handlers
  const handleModuleTemplateSelect = (template: BaseModuleTemplate | null) => {
    setSelectedModuleTemplate(template);
  };

  const toggleSidebar = () => {
    setIsSidebarCollapsed(prev => !prev);
  };

  // Global mouse handlers for module dragging and canvas dragging
  useEffect(() => {
    const handleGlobalMouseMove = (e: MouseEvent) => {
      // Log when we're in a dragging state
      if (isDragging) {
        console.log('📍 Global mouse move - canvas dragging', { 
          x: e.clientX, 
          y: e.clientY,
          target: e.target?.constructor?.name || 'unknown'
        });
      }
      if (isDraggingModule) {
        console.log('📍 Global mouse move - module dragging');
      }

      // Prevent any other event handlers from interfering
      if (isDragging || isDraggingModule) {
        e.preventDefault();
        e.stopPropagation();
      }

      // Handle module dragging
      if (isDraggingModule && draggedModuleId && canvasRef.current) {
        const canvasRect = canvasRef.current.getBoundingClientRect();
        
        // Calculate new position
        const mouseX = (e.clientX - canvasRect.left - panOffset.x) / zoom;
        const mouseY = (e.clientY - canvasRect.top - panOffset.y) / zoom;
        
        let newX = mouseX - moduleDragOffset.x;
        let newY = mouseY - moduleDragOffset.y;
        
        // Apply bounds checking - keep modules within reasonable canvas area
        const moduleWidth = 160; // Half of max module width for centering
        const moduleHeight = 50; // Approximate half module height
        const padding = 20; // Minimum distance from edges
        
        // Calculate canvas bounds in world coordinates
        const canvasWidth = canvasRect.width / zoom;
        const canvasHeight = canvasRect.height / zoom;
        const leftBound = (-panOffset.x / zoom) + moduleWidth + padding;
        const rightBound = (-panOffset.x / zoom) + canvasWidth - moduleWidth - padding;
        const topBound = (-panOffset.y / zoom) + moduleHeight + padding;
        const bottomBound = (-panOffset.y / zoom) + canvasHeight - moduleHeight - padding;
        
        // Constrain position within bounds
        newX = Math.max(leftBound, Math.min(rightBound, newX));
        newY = Math.max(topBound, Math.min(bottomBound, newY));
        
        setPlacedModules(prev => 
          prev.map(module => 
            module.id === draggedModuleId 
              ? { ...module, position: { x: newX, y: newY } }
              : module
          )
        );
        return;
      }

      // Handle canvas dragging
      if (isDragging) {
        const deltaX = e.clientX - dragStart.x;
        const deltaY = e.clientY - dragStart.y;
        
        setPanOffset({
          x: dragStartOffset.x + deltaX,
          y: dragStartOffset.y + deltaY,
        });
      }
    };

    const handleGlobalMouseUp = (e: MouseEvent) => {
      console.log('🛑 Global mouse up', { 
        isDragging, 
        isDraggingModule, 
        target: e.target?.constructor?.name || 'unknown'
      });
      
      if (isDragging || isDraggingModule) {
        e.preventDefault();
        e.stopPropagation();
      }
      
      if (isDraggingModule) {
        console.log('🛑 Stopping module drag');
        setIsDraggingModule(false);
        setDraggedModuleId(null);
      }
      if (isDragging) {
        console.log('🛑 Stopping canvas drag');
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
  }, [isDraggingModule, draggedModuleId, moduleDragOffset, isDragging, dragStart, dragStartOffset, panOffset, zoom]);

  // Handle module deletion
  const handleModuleDelete = (moduleId: string) => () => {
    setPlacedModules(prev => prev.filter(module => module.id !== moduleId));
    // Clear selection if deleted module was selected
    if (selectedModuleId === moduleId) {
      setSelectedModuleId(null);
    }
  };

  // Handle module click (selection)
  const handleModuleClick = (moduleId: string) => (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedModuleId(moduleId);
  };

  // Handle module mouse down (start dragging)
  const handleModuleMouseDown = (moduleId: string) => (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Only left mouse button
    
    e.preventDefault(); // Prevent text selection
    e.stopPropagation();
    
    const module = placedModules.find(m => m.id === moduleId);
    if (!module || !canvasRef.current) return;
    
    const canvasRect = canvasRef.current.getBoundingClientRect();
    
    // Calculate offset from mouse to module center
    const mouseX = (e.clientX - canvasRect.left - panOffset.x) / zoom;
    const mouseY = (e.clientY - canvasRect.top - panOffset.y) / zoom;
    
    const offsetX = mouseX - module.position.x;
    const offsetY = mouseY - module.position.y;
    
    setIsDraggingModule(true);
    setDraggedModuleId(moduleId);
    setModuleDragOffset({ x: offsetX, y: offsetY });
  };

  // Handle drag over canvas
  const handleCanvasDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  };

  // Handle drop on canvas
  const handleCanvasDrop = (e: React.DragEvent) => {
    e.preventDefault();
    
    if (!canvasRef.current) return;
    
    try {
      const moduleData = JSON.parse(e.dataTransfer.getData('application/json')) as BaseModuleTemplate;
      const canvasRect = canvasRef.current.getBoundingClientRect();
      
      // Calculate drop position relative to canvas, accounting for zoom and pan
      const dropX = (e.clientX - canvasRect.left - panOffset.x) / zoom;
      const dropY = (e.clientY - canvasRect.top - panOffset.y) / zoom;
      
      // Create new placed module
      const newModule: PlacedModule = {
        id: `${moduleData.id}_${Date.now()}`,
        template: moduleData,
        position: { x: dropX, y: dropY },
        config: {}
      };
      
      setPlacedModules(prev => [...prev, newModule]);
      
      // Clear selection after successful drop
      setSelectedModuleTemplate(null);
      
    } catch (error) {
      console.error('Failed to parse dropped module data:', error);
    }
  };

  return (
    <div className="relative w-full h-full overflow-hidden bg-gray-900 flex">
      {/* Module Selection Sidebar */}
      <div className={`relative z-50 ${isDragging ? 'pointer-events-none' : ''}`}>
        <ModuleSelectionPane
          modules={testBaseModules}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={toggleSidebar}
          onModuleSelect={handleModuleTemplateSelect}
          selectedModule={selectedModuleTemplate}
        />
      </div>

      {/* Main Graph Area */}
      <div className="flex-1 relative">
        {/* Zoom Controls - Top Right */}
        <div className="absolute top-4 right-4 z-20 flex flex-col bg-gray-800 rounded-lg shadow-lg border border-gray-700">
          <button
            onClick={isDraggingModule ? undefined : zoomIn}
            disabled={isDraggingModule}
            className={`w-10 h-10 flex items-center justify-center transition-colors rounded-t-lg border-b border-gray-700 ${
              isDraggingModule 
                ? 'text-gray-500 cursor-not-allowed' 
                : 'text-white hover:bg-gray-700'
            }`}
            title={isDraggingModule ? "Cannot zoom while dragging" : "Zoom In"}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </button>
          
          <div className="w-10 h-8 flex items-center justify-center text-xs text-gray-400 border-b border-gray-700">
            {Math.round(zoom * 100)}%
          </div>
          
          <button
            onClick={isDraggingModule ? undefined : zoomOut}
            disabled={isDraggingModule}
            className={`w-10 h-10 flex items-center justify-center transition-colors border-b border-gray-700 ${
              isDraggingModule 
                ? 'text-gray-500 cursor-not-allowed' 
                : 'text-white hover:bg-gray-700'
            }`}
            title={isDraggingModule ? "Cannot zoom while dragging" : "Zoom Out"}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 12H6" />
            </svg>
          </button>
          
          <button
            onClick={isDraggingModule ? undefined : resetZoom}
            disabled={isDraggingModule}
            className={`w-10 h-10 flex items-center justify-center transition-colors rounded-b-lg ${
              isDraggingModule 
                ? 'text-gray-500 cursor-not-allowed' 
                : 'text-white hover:bg-gray-700'
            }`}
            title={isDraggingModule ? "Cannot reset while dragging" : "Reset Zoom"}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>

        {/* Canvas Container */}
        <div
          ref={canvasRef}
          className={`w-full h-full select-none ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
          style={{
            userSelect: 'none',
            WebkitUserSelect: 'none',
            MozUserSelect: 'none',
            msUserSelect: 'none'
          }}
          onWheel={handleWheel}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          onMouseLeave={handleCanvasMouseLeave}
          onDragOver={handleCanvasDragOver}
          onDrop={handleCanvasDrop}
          style={{
            backgroundImage: `
              linear-gradient(rgba(75, 85, 99, ${getGridOpacity(zoom)}) 1px, transparent 1px),
              linear-gradient(90deg, rgba(75, 85, 99, ${getGridOpacity(zoom)}) 1px, transparent 1px)
            `,
            backgroundSize: `${getGridSize(zoom) * zoom}px ${getGridSize(zoom) * zoom}px`,
            backgroundPosition: `${panOffset.x}px ${panOffset.y}px`,
          }}
        >
          {/* Zoom and Pan Container */}
          <div
            className="relative w-full h-full origin-top-left"
            style={{
              transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoom})`,
            }}
          >
            {/* Placed Modules */}
            {placedModules.map((placedModule) => (
              <GraphModuleComponent
                key={placedModule.id}
                template={placedModule.template}
                position={placedModule.position}
                onMouseDown={handleModuleMouseDown(placedModule.id)}
                onDelete={handleModuleDelete(placedModule.id)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}