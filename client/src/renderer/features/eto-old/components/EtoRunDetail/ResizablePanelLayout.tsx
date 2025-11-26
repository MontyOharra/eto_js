/**
 * ResizablePanelLayout
 * Two-panel layout with resizable divider
 * Manages resize state and width calculation
 */

import { useState, useEffect } from "react";
import { ResizableDivider } from "./ResizableDivider";

interface ResizablePanelLayoutProps {
  leftPanel: React.ReactNode;
  rightPanel: React.ReactNode;
  defaultSplitPercentage?: number;
  onDragStateChange?: (isDragging: boolean) => void;
}

export function ResizablePanelLayout({
  leftPanel,
  rightPanel,
  defaultSplitPercentage = 60,
  onDragStateChange,
}: ResizablePanelLayoutProps) {
  const [leftWidth, setLeftWidth] = useState(defaultSplitPercentage);
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseDown = () => {
    setIsDragging(true);
    onDragStateChange?.(true);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging) return;

    const container = document.querySelector(".resizable-panel-container");
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const percentage = (offsetX / rect.width) * 100;

    // Constrain between 20% and 80%
    const constrainedPercentage = Math.min(Math.max(percentage, 20), 80);
    setLeftWidth(constrainedPercentage);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    onDragStateChange?.(false);
  };

  // Attach/detach global mouse event listeners
  useEffect(() => {
    if (isDragging) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };
    }
  }, [isDragging]);

  return (
    <div className="flex h-full resizable-panel-container">
      {/* Left Panel */}
      <div style={{ width: `${leftWidth}%`, height: '100%' }}>{leftPanel}</div>

      {/* Resizable Divider */}
      <ResizableDivider onMouseDown={handleMouseDown} isDragging={isDragging} />

      {/* Right Panel */}
      <div style={{ width: `${100 - leftWidth}%`, height: '100%' }}>{rightPanel}</div>
    </div>
  );
}
