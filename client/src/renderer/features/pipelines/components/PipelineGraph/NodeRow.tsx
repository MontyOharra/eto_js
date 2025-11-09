/**
 * NodeRow Component
 * Displays an individual input or output pin row
 */

import React, { useRef, useEffect, useState } from "react";
import { Handle, Position } from "@xyflow/react";
import { NodePin } from "../../types";
import { getTypeColor } from "../../utils/edgeUtils";
import { TypeIndicator } from "./TypeIndicator";

export interface NodeRowProps {
  node: NodePin;
  direction: "input" | "output";
  moduleId: string;
  canRemove: boolean;
  onTypeChange: (nodeId: string, newType: string) => void;
  onNameChange: (nodeId: string, newName: string) => void;
  onRemove?: () => void;
  getConnectedOutputName?: (inputNodeId: string) => string | undefined;
  highlightedTypeVar: string | null;
  onTypeVarFocus: (typeVar: string | null) => void;
  onTextFocus?: () => void;
  onTextBlur?: () => void;
  onHandleClick?: (
    nodeId: string,
    handleId: string,
    handleType: "source" | "target"
  ) => void;
  pendingConnection?: {
    sourceHandleId: string;
    sourceNodeId: string;
    handleType: "source" | "target";
  } | null;
  getEffectiveAllowedTypes?: (
    moduleId: string,
    pinId: string,
    baseAllowedTypes: string[]
  ) => string[];
}

export function NodeRow({
  node,
  direction,
  moduleId,
  canRemove,
  onTypeChange,
  onNameChange,
  onRemove,
  getConnectedOutputName,
  highlightedTypeVar,
  onTypeVarFocus,
  onTextFocus,
  onTextBlur,
  onHandleClick,
  getEffectiveAllowedTypes,
}: NodeRowProps) {
  const isHighlighted = node.type_var && node.type_var === highlightedTypeVar;
  const handleColor = getTypeColor(node.type);

  // Ref for output textarea to auto-resize
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Local state for text input - updates immediately for responsive typing
  const [localName, setLocalName] = useState(node.name);

  // Sync local state when node.name changes externally
  useEffect(() => {
    setLocalName(node.name);
  }, [node.name]);

  // Handle click
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onHandleClick) {
      const handleType = direction === "input" ? "target" : "source";
      onHandleClick(moduleId, node.node_id, handleType);
    }
  };

  // For input nodes, display connected output name or "Not Connected"
  const connectedOutputName =
    direction === "input" ? getConnectedOutputName?.(node.node_id) : undefined;
  const displayName =
    direction === "input"
      ? connectedOutputName !== undefined
        ? connectedOutputName
        : "Not Connected"
      : node.name || "";

  // Auto-resize textarea when value or layout changes
  useEffect(() => {
    if (textareaRef.current && direction === "output" && !node.readonly) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = textareaRef.current.scrollHeight + "px";
    }
  }, [node.name, canRemove, direction, node.readonly]);

  return (
    <div className="relative flex items-center gap-2 py-1.5">
      {/* Connection Handle - Centered on outer edge */}
      <Handle
        type={direction === "input" ? "target" : "source"}
        position={direction === "input" ? Position.Left : Position.Right}
        id={node.node_id}
        className="!w-5 !h-5 !border-3 !border-gray-900 !cursor-pointer"
        style={{
          [direction === "input" ? "left" : "right"]: -13,
          backgroundColor: handleColor,
        }}
        data-handleid={node.node_id}
        onClick={handleClick}
      />

      {/* Node Content - Mirrored layout based on direction */}
      {direction === "input" ? (
        // Input layout: [handle] name - delete - type
        <div className="flex items-start w-full gap-2">
          <div className="flex-1 min-w-0 nodrag">
            <div className="text-sm text-gray-300 px-1.5 py-0.5 w-full min-h-[24px] break-words">
              {displayName}
            </div>
          </div>
          {canRemove && onRemove && (
            <div className="flex-shrink-0 pt-0.5">
              <button
                onClick={onRemove}
                className="p-0.5 rounded transition-colors text-gray-500 hover:text-red-400 hover:bg-red-900 cursor-pointer"
                title="Remove node"
              >
                <svg
                  className="w-3 h-3"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          )}
          <div className="flex-shrink-0 w-12 flex items-start pt-0.5">
            <TypeIndicator
              node={node}
              onTypeChange={onTypeChange}
              onFocus={() => onTypeVarFocus(node.type_var || null)}
              onBlur={() => onTypeVarFocus(null)}
              isHighlighted={!!isHighlighted}
              effectiveAllowedTypes={getEffectiveAllowedTypes?.(
                moduleId,
                node.node_id,
                node.allowed_types || []
              )}
            />
          </div>
        </div>
      ) : (
        // Output layout: type - delete - name [handle]
        <div className="flex items-start w-full gap-2">
          <div className="flex-shrink-0 w-12 flex items-start pt-0.5">
            <TypeIndicator
              node={node}
              onTypeChange={onTypeChange}
              onFocus={() => onTypeVarFocus(node.type_var || null)}
              onBlur={() => onTypeVarFocus(null)}
              isHighlighted={!!isHighlighted}
              effectiveAllowedTypes={getEffectiveAllowedTypes?.(
                moduleId,
                node.node_id,
                node.allowed_types || []
              )}
            />
          </div>
          {canRemove && onRemove && (
            <div className="flex-shrink-0 pt-0.5">
              <button
                onClick={onRemove}
                className="p-0.5 rounded transition-colors text-gray-500 hover:text-red-400 hover:bg-red-900 cursor-pointer"
                title="Remove node"
              >
                <svg
                  className="w-3 h-3"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          )}
          <div className="flex-1 min-w-0 nodrag">
            {node.readonly ? (
              // Read-only label (used for entry points)
              <div className="text-sm text-gray-300 px-1.5 py-0.5 w-full min-h-[24px] break-words">
                {node.name}
              </div>
            ) : (
              // Editable textarea (used for regular modules)
              <textarea
                ref={textareaRef}
                value={localName}
                onChange={(e) => {
                  setLocalName(e.target.value);
                  // Auto-resize immediately
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = "auto";
                  target.style.height = target.scrollHeight + "px";
                }}
                onFocus={onTextFocus}
                // eslint-disable-next-line @typescript-eslint/no-unused-vars
                onBlur={(_event) => {
                  // Update pipeline state when done editing
                  onNameChange(node.node_id, localName);
                  onTextBlur?.();
                }}
                placeholder="Node name"
                className="w-full text-sm bg-gray-700 text-gray-200 px-1.5 py-0.5 rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none overflow-hidden min-h-[24px] break-words nodrag"
                rows={1}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
