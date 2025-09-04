/**
 * Connection utility functions for the transformation pipeline
 */

/**
 * Generate bezier path for connection - direction aware
 */
export const generateBezierPath = (
  start: { x: number; y: number }, 
  end: { x: number; y: number }, 
  startType?: 'input' | 'output'
): string => {
  const controlPointOffset = Math.abs(end.x - start.x) * 0.5;
  
  let cp1x, cp2x;
  
  if (startType === 'input') {
    // Starting from input node (left side) - curve should go left then right
    cp1x = start.x - controlPointOffset;
    cp2x = end.x + controlPointOffset;
  } else {
    // Starting from output node (right side) or standard connection - curve should go right then left
    cp1x = start.x + controlPointOffset;
    cp2x = end.x - controlPointOffset;
  }
  
  return `M ${start.x},${start.y} C ${cp1x},${start.y} ${cp2x},${end.y} ${end.x},${end.y}`;
};

/**
 * Get node position from DOM element or cached position
 */
export const getNodePosition = (
  moduleId: string, 
  nodeType: 'input' | 'output', 
  nodeIndex: number,
  canvasRef: React.RefObject<HTMLDivElement>,
  panOffset: { x: number; y: number },
  zoom: number,
  nodePositions: Record<string, { x: number; y: number }>
): { x: number; y: number } => {
  // Try to find the actual DOM element for this node
  const nodeSelector = `[data-node-id="${moduleId}-${nodeType}-${nodeIndex}"]`;
  const nodeElement = document.querySelector(nodeSelector);
  
  if (nodeElement && canvasRef.current) {
    const nodeRect = nodeElement.getBoundingClientRect();
    const canvasRect = canvasRef.current.getBoundingClientRect();
    
    // Calculate center of the node element
    const centerX = nodeRect.left + nodeRect.width / 2;
    const centerY = nodeRect.top + nodeRect.height / 2;
    
    // Convert from screen coordinates to canvas coordinates
    const canvasX = (centerX - canvasRect.left - panOffset.x) / zoom;
    const canvasY = (centerY - canvasRect.top - panOffset.y) / zoom;
    
    return { x: canvasX, y: canvasY };
  }
  
  // Fallback to cached position if DOM element not found
  const nodeKey = `${moduleId}-${nodeType}-${nodeIndex}`;
  const cachedPosition = nodePositions[nodeKey];
  
  if (cachedPosition && canvasRef.current) {
    const canvasRect = canvasRef.current.getBoundingClientRect();
    const canvasX = (cachedPosition.x - canvasRect.left - panOffset.x) / zoom;
    const canvasY = (cachedPosition.y - canvasRect.top - panOffset.y) / zoom;
    return { x: canvasX, y: canvasY };
  }
  
  // Final fallback to origin
  return { x: 0, y: 0 };
};