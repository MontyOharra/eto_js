/**
 * NodeGroupSection Component
 * Displays a group of input or output pins with add/remove functionality
 */

import {
  NodePin,
  ModuleTemplate,
} from "../../../../../shared/types/moduleTypes";
import { NodeRow } from "./NodeRow";

export interface NodeGroupSectionProps {
  groupIndex: number;
  groupLabel: string;
  nodes: NodePin[];
  direction: "input" | "output";
  moduleId: string;
  template: ModuleTemplate;
  onTypeChange: (nodeId: string, newType: string) => void;
  onNameChange: (nodeId: string, newName: string) => void;
  onAddNode?: (
    moduleId: string,
    direction: "input" | "output",
    groupIndex: number
  ) => void;
  onRemoveNode?: (moduleId: string, nodeId: string) => void;
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
  executionMode?: boolean;
  executionValues?: Map<string, { value: any; type: string; name: string }>;
}

export function NodeGroupSection({
  groupIndex,
  groupLabel,
  nodes,
  direction,
  moduleId,
  template,
  onTypeChange,
  onNameChange,
  onAddNode,
  onRemoveNode,
  getConnectedOutputName,
  highlightedTypeVar,
  onTypeVarFocus,
  onTextFocus,
  onTextBlur,
  onHandleClick,
  pendingConnection,
  getEffectiveAllowedTypes,
  executionMode = false,
  executionValues,
}: NodeGroupSectionProps) {
  // Get the NodeGroup from template
  const ioShape =
    direction === "input"
      ? template.meta?.io_shape?.inputs
      : template.meta?.io_shape?.outputs;

  const nodeGroup = ioShape?.nodes[groupIndex];

  const minCount = nodeGroup?.min_count || 1;
  const maxCount = nodeGroup?.max_count;

  const canAdd = maxCount == null || nodes.length < maxCount;
  const canRemove = nodes.length > minCount;

  return (
    <div className="mb-3 last:mb-0">
      {/* Group Label */}
      <div className="flex items-center mb-2">
        <div className="flex-1 border-t border-gray-600"></div>
        <span className="px-2 text-sm text-gray-400 uppercase font-semibold">
          {groupLabel}
        </span>
        <div className="flex-1 border-t border-gray-600"></div>
      </div>

      {/* Node Rows */}
      <div className="space-y-1">
        {nodes.map((node) => (
          <NodeRow
            key={node.node_id}
            node={node}
            direction={direction}
            moduleId={moduleId}
            canRemove={canRemove}
            onTypeChange={onTypeChange}
            onNameChange={onNameChange}
            onRemove={
              onRemoveNode
                ? () => onRemoveNode(moduleId, node.node_id)
                : undefined
            }
            getConnectedOutputName={getConnectedOutputName}
            highlightedTypeVar={highlightedTypeVar}
            onTypeVarFocus={onTypeVarFocus}
            onTextFocus={onTextFocus}
            onTextBlur={onTextBlur}
            onHandleClick={onHandleClick}
            pendingConnection={pendingConnection}
            getEffectiveAllowedTypes={getEffectiveAllowedTypes}
            executionMode={executionMode}
            executionValue={executionValues?.get(node.node_id)}
          />
        ))}

        {/* Add Node Button */}
        {canAdd && onAddNode && !executionMode && (
          <div className="relative flex items-center gap-2 py-1.5 group">
            <button
              onClick={() => onAddNode(moduleId, direction, groupIndex)}
              className="absolute flex items-center justify-center w-5 h-5 rounded-full border-2 border-gray-900 bg-gray-500 group-hover:bg-gray-400 transition-colors"
              style={{
                [direction === "input" ? "left" : "right"]: -23,
                top: "50%",
                transform: "translateY(-50%)",
              }}
            >
              <svg
                className="w-2.5 h-2.5 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={3}
                  d="M12 4v16m8-8H4"
                />
              </svg>
            </button>
            <div
              className="flex-1 text-xs text-gray-300 font-medium px-2 py-1.5 border-2 border-dashed border-gray-500 bg-gray-800 rounded cursor-pointer group-hover:border-gray-400 group-hover:bg-gray-700 group-hover:text-white transition-colors text-center"
              onClick={() => onAddNode(moduleId, direction, groupIndex)}
            >
              Add {direction === "input" ? "Input" : "Output"}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
