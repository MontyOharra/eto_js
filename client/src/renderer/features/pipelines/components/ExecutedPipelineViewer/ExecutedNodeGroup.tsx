/**
 * ExecutedNodeGroup
 * Displays a group of input or output pins with a label header
 */

import { ExecutedModuleRow } from "./ExecutedModuleRow";

interface NodeData {
  nodeId: string;
  name: string;
  type: string;
  value: string;
}

interface ExecutedNodeGroupProps {
  groupLabel: string;
  nodes: NodeData[];
  direction: "input" | "output";
}

export function ExecutedNodeGroup({
  groupLabel,
  nodes,
  direction,
}: ExecutedNodeGroupProps) {
  return (
    <div className="mb-3 last:mb-0">
      {/* Group Label */}
      <div className="flex items-center mb-2">
        <div className="flex-1 border-t border-gray-600"></div>
        <span className="px-2 text-xs text-gray-400 uppercase font-semibold">
          {groupLabel}
        </span>
        <div className="flex-1 border-t border-gray-600"></div>
      </div>

      {/* Node Rows */}
      <div className="space-y-1">
        {nodes.map((node) => (
          <ExecutedModuleRow
            key={node.nodeId}
            nodeId={node.nodeId}
            name={node.name}
            type={node.type}
            value={node.value}
            direction={direction}
          />
        ))}
      </div>
    </div>
  );
}
