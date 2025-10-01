import { useState, useRef, useEffect } from 'react';

interface ViewportState {
  zoom: number;
  panOffset: { x: number; y: number };
}

interface ModulePosition {
  x: number;
  y: number;
}

interface UseViewportOptions {
  minZoom?: number;
  maxZoom?: number;
  initialZoom?: number;
  initialPanOffset?: { x: number; y: number };
}

export const useViewport = (options: UseViewportOptions = {}) => {
  const {
    minZoom = 0.25,
    maxZoom = 3,
    initialZoom = 1,
    initialPanOffset = { x: 0, y: 0 }
  } = options;

  // Viewport state
  const [zoom, setZoom] = useState(initialZoom);
  const [panOffset, setPanOffset] = useState(initialPanOffset);

  // Canvas dragging state
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [dragStartOffset, setDragStartOffset] = useState({ x: 0, y: 0 });

  // Canvas reference
  const canvasRef = useRef<HTMLDivElement>(null);

  // Zoom controls
  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev * 1.2, maxZoom));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev * 0.8, minZoom));
  };

  const handleResetZoom = (modulePositions?: Record<string, ModulePosition>) => {
    // If there are modules, fit them all in view
    if (modulePositions && Object.keys(modulePositions).length > 0 && canvasRef.current) {
      const positions = Object.values(modulePositions);

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
      const zoomToFitWidth = canvasWidth / boundingWidth;
      const zoomToFitHeight = canvasHeight / boundingHeight;
      const newZoom = Math.min(Math.min(zoomToFitWidth, zoomToFitHeight), maxZoom);

      // Calculate pan offset to center the bounding box
      const newPanX = canvasWidth / 2 - centerX * newZoom;
      const newPanY = canvasHeight / 2 - centerY * newZoom;

      setZoom(Math.max(newZoom, minZoom));
      setPanOffset({ x: newPanX, y: newPanY });
    } else {
      // No modules, just reset to defaults
      setZoom(initialZoom);
      setPanOffset(initialPanOffset);
    }
  };

  // Canvas mouse event handlers
  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) { // Left click only
      setIsDragging(true);
      setDragStart({ x: e.clientX, y: e.clientY });
      setDragStartOffset({ ...panOffset });
    }
  };

  const handleCanvasMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      const deltaX = e.clientX - dragStart.x;
      const deltaY = e.clientY - dragStart.y;
      setPanOffset({
        x: dragStartOffset.x + deltaX,
        y: dragStartOffset.y + deltaY
      });
    }
  };

  const handleCanvasMouseUp = () => {
    setIsDragging(false);
  };

  const handleCanvasMouseLeave = () => {
    setIsDragging(false);
  };

  // Wheel handler for zooming
  useEffect(() => {
    const handleWheel = (e: WheelEvent) => {
      if (!canvasRef.current) return;

      // Check if mouse is over the canvas
      const rect = canvasRef.current.getBoundingClientRect();
      const isOverCanvas =
        e.clientX >= rect.left &&
        e.clientX <= rect.right &&
        e.clientY >= rect.top &&
        e.clientY <= rect.bottom;

      if (!isOverCanvas) return;

      e.preventDefault();

      // Calculate mouse position relative to canvas
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      // Calculate mouse position in canvas coordinates (before zoom)
      const canvasMouseX = (mouseX - panOffset.x) / zoom;
      const canvasMouseY = (mouseY - panOffset.y) / zoom;

      // Calculate new zoom
      const zoomDelta = e.deltaY > 0 ? 0.9 : 1.1;
      const newZoom = Math.min(Math.max(zoom * zoomDelta, minZoom), maxZoom);

      // Calculate new pan offset to keep mouse position stable
      const newPanX = mouseX - canvasMouseX * newZoom;
      const newPanY = mouseY - canvasMouseY * newZoom;

      setZoom(newZoom);
      setPanOffset({ x: newPanX, y: newPanY });
    };

    const canvas = canvasRef.current;
    if (canvas) {
      canvas.addEventListener('wheel', handleWheel, { passive: false });
      return () => {
        canvas.removeEventListener('wheel', handleWheel);
      };
    }
  }, [zoom, panOffset, minZoom, maxZoom]);

  // Grid utilities
  const getGridSize = (zoomLevel: number) => {
    if (zoomLevel < 0.5) return 80;
    if (zoomLevel < 1) return 40;
    if (zoomLevel < 2) return 20;
    return 10;
  };

  const getGridOpacity = (zoomLevel: number) => {
    if (zoomLevel < 0.5) return 0.1;
    if (zoomLevel < 1) return 0.15;
    if (zoomLevel < 2) return 0.2;
    return 0.25;
  };

  // Convert screen coordinates to canvas coordinates
  const screenToCanvas = (screenX: number, screenY: number) => {
    if (!canvasRef.current) return { x: 0, y: 0 };

    const rect = canvasRef.current.getBoundingClientRect();
    const canvasX = (screenX - rect.left - panOffset.x) / zoom;
    const canvasY = (screenY - rect.top - panOffset.y) / zoom;

    return { x: canvasX, y: canvasY };
  };

  // Convert canvas coordinates to screen coordinates
  const canvasToScreen = (canvasX: number, canvasY: number) => {
    if (!canvasRef.current) return { x: 0, y: 0 };

    const rect = canvasRef.current.getBoundingClientRect();
    const screenX = canvasX * zoom + panOffset.x + rect.left;
    const screenY = canvasY * zoom + panOffset.y + rect.top;

    return { x: screenX, y: screenY };
  };

  return {
    // State
    zoom,
    panOffset,
    isDragging,
    canvasRef,

    // Actions
    handleZoomIn,
    handleZoomOut,
    handleResetZoom,
    handleCanvasMouseDown,
    handleCanvasMouseMove,
    handleCanvasMouseUp,
    handleCanvasMouseLeave,

    // Utilities
    getGridSize,
    getGridOpacity,
    screenToCanvas,
    canvasToScreen,

    // Direct setters for advanced use cases
    setZoom,
    setPanOffset
  };
};