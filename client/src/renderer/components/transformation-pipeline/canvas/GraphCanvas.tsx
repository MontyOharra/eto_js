import React, { useRef, useEffect, ReactNode } from 'react';

interface GraphCanvasProps {
  // Viewport state
  zoom: number;
  panOffset: { x: number; y: number };
  isDragging: boolean;
  
  // Event handlers
  onMouseDown: (e: React.MouseEvent) => void;
  onMouseMove: (e: React.MouseEvent) => void;
  onMouseUp: () => void;
  onMouseLeave: () => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
  
  // Canvas ref for external access
  canvasRef: React.RefObject<HTMLDivElement>;
  
  // Children (layers)
  children: ReactNode;
}

export const GraphCanvas: React.FC<GraphCanvasProps> = ({
  zoom,
  panOffset,
  isDragging,
  onMouseDown,
  onMouseMove,
  onMouseUp,
  onMouseLeave,
  onDragOver,
  onDrop,
  canvasRef,
  children
}) => {
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
    <div
      ref={canvasRef}
      className={`w-full h-full select-none touch-none overflow-hidden ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
      style={{
        userSelect: 'none',
        WebkitUserSelect: 'none',
        MozUserSelect: 'none',
        msUserSelect: 'none',
        WebkitTouchCallout: 'none',
        KhtmlUserSelect: 'none',
        backgroundImage: `
          linear-gradient(rgba(75, 85, 99, ${getGridOpacity(zoom)}) 1px, transparent 1px),
          linear-gradient(90deg, rgba(75, 85, 99, ${getGridOpacity(zoom)}) 1px, transparent 1px)
        `,
        backgroundSize: `${getGridSize(zoom) * zoom}px ${getGridSize(zoom) * zoom}px`,
        backgroundPosition: `${panOffset.x}px ${panOffset.y}px`,
      }}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onContextMenu={(e) => e.preventDefault()}
      onSelectStart={(e) => e.preventDefault()}
      onDragStart={(e) => e.preventDefault()}
    >
      {/* Zoom and Pan Container */}
      <div
        className="relative w-full h-full origin-top-left"
        style={{
          transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoom})`,
        }}
      >
        {children}
      </div>
    </div>
  );
};