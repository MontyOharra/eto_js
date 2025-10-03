import { useState, useCallback } from "react";
import { Handle, Position } from "@xyflow/react";
import { ModuleTemplate, ModuleInstance, NodePin } from "../../../types/moduleTypes";

interface ModuleNodeNewProps {
  data: {
    moduleInstance: ModuleInstance;
    template: ModuleTemplate;
    onDeleteModule?: (moduleId: string) => void;
    onUpdateNode?: (moduleId: string, nodeId: string, updates: Partial<NodePin>) => void;
    onAddNode?: (moduleId: string, direction: "input" | "output", groupLabel: string) => void;
    onRemoveNode?: (moduleId: string, nodeId: string) => void;
    connections?: Array<{ from_node_id: string; to_node_id: string }>;
    onTextFocus?: () => void;
    onTextBlur?: () => void;
  };
}

// Type to color mapping
const TYPE_COLORS: Record<string, string> = {
  str: "#3B82F6", // blue-500
  int: "#EF4444", // red-500
  float: "#F59E0B", // orange-500
  bool: "#10B981", // green-500
  datetime: "#8B5CF6", // purple-500
};

// Calculate if text should be white or black based on background brightness
function getTextColor(hexColor: string): string {
  const hex = hexColor.replace("#", "");
  const r = parseInt(hex.substr(0, 2), 16);
  const g = parseInt(hex.substr(2, 2), 16);
  const b = parseInt(hex.substr(4, 2), 16);
  const brightness = (r * 299 + g * 587 + b * 114) / 1000;
  return brightness > 128 ? "#000000" : "#FFFFFF";
}

// Group nodes by their group_key (label)
function groupNodesByLabel(nodes: NodePin[]): Map<string, NodePin[]> {
  const groups = new Map<string, NodePin[]>();

  nodes.forEach((node) => {
    const label = node.label || "Ungrouped";
    if (!groups.has(label)) {
      groups.set(label, []);
    }
    groups.get(label)!.push(node);
  });

  return groups;
}

export function ModuleNodeNew({ data }: ModuleNodeNewProps) {
  const { moduleInstance, template, onDeleteModule, onUpdateNode, onAddNode, onRemoveNode, connections, onTextFocus, onTextBlur } = data;
  const [isConfigExpanded, setIsConfigExpanded] = useState(false);
  const [highlightedTypeVar, setHighlightedTypeVar] = useState<string | null>(null);

  // Group inputs and outputs
  const inputGroups = groupNodesByLabel(moduleInstance.inputs);
  const outputGroups = groupNodesByLabel(moduleInstance.outputs);

  // Get connected output name for an input node
  const getConnectedOutputName = useCallback((inputNodeId: string): string | undefined => {
    if (!connections) return undefined;
    const connection = connections.find((c) => c.to_node_id === inputNodeId);
    if (!connection) return undefined;

    // Find the output node
    const allOutputs = moduleInstance.outputs;
    const outputNode = allOutputs.find((n) => n.node_id === connection.from_node_id);
    return outputNode?.name;
  }, [connections, moduleInstance.outputs]);

  const handleTypeChange = (nodeId: string, newType: string) => {
    if (onUpdateNode) {
      onUpdateNode(moduleInstance.module_instance_id, nodeId, { type: newType });
    }
  };

  const handleNameChange = (nodeId: string, newName: string) => {
    if (onUpdateNode) {
      onUpdateNode(moduleInstance.module_instance_id, nodeId, { name: newName });
    }
  };

  const handleDelete = () => {
    if (onDeleteModule) {
      onDeleteModule(moduleInstance.module_instance_id);
    }
  };

  const headerColor = template.color || "#4B5563";
  const textColor = getTextColor(headerColor);

  return (
    <div className="bg-gray-800 rounded-lg border-2 border-gray-600 min-w-[340px]">
      {/* Header */}
      <div
        className="px-3 py-2 rounded-t-lg border-b border-gray-600 flex items-center justify-between"
        style={{ backgroundColor: headerColor }}
      >
        <div>
          <div className="font-medium text-sm" style={{ color: textColor }}>
            {template.title}
          </div>
          <div className="text-xs opacity-70" style={{ color: textColor }}>
            {moduleInstance.module_instance_id}
          </div>
        </div>
        <button
          onClick={handleDelete}
          className="p-1 rounded hover:bg-red-500 transition-colors"
          title="Delete module"
        >
          <svg
            className="w-4 h-4"
            style={{ color: textColor }}
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

      {/* Body with inputs and outputs side by side */}
      <div className="flex relative">
        {/* Inputs Section */}
        <div className="w-1/2 p-3 border-r border-gray-600">
          {Array.from(inputGroups.entries()).map(([groupLabel, nodes]) => (
            <NodeGroupSection
              key={groupLabel}
              groupLabel={groupLabel}
              nodes={nodes}
              direction="input"
              moduleId={moduleInstance.module_instance_id}
              template={template}
              onTypeChange={handleTypeChange}
              onNameChange={handleNameChange}
              onAddNode={onAddNode}
              onRemoveNode={onRemoveNode}
              getConnectedOutputName={getConnectedOutputName}
              highlightedTypeVar={highlightedTypeVar}
              onTypeVarFocus={setHighlightedTypeVar}
              onTextFocus={onTextFocus}
              onTextBlur={onTextBlur}
            />
          ))}
        </div>

        {/* Outputs Section */}
        <div className="w-1/2 p-3">
          {Array.from(outputGroups.entries()).map(([groupLabel, nodes]) => (
            <NodeGroupSection
              key={groupLabel}
              groupLabel={groupLabel}
              nodes={nodes}
              direction="output"
              moduleId={moduleInstance.module_instance_id}
              template={template}
              onTypeChange={handleTypeChange}
              onNameChange={handleNameChange}
              onAddNode={onAddNode}
              onRemoveNode={onRemoveNode}
              highlightedTypeVar={highlightedTypeVar}
              onTypeVarFocus={setHighlightedTypeVar}
              onTextFocus={onTextFocus}
              onTextBlur={onTextBlur}
            />
          ))}
        </div>
      </div>

      {/* Collapsible Configuration Section */}
      <div className="border-t border-gray-600">
        <button
          onClick={() => setIsConfigExpanded(!isConfigExpanded)}
          className="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-700 transition-colors"
        >
          <span className="text-[10px] text-gray-400 uppercase font-semibold">
            Configuration
          </span>
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform ${
              isConfigExpanded ? "rotate-180" : ""
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>

        {isConfigExpanded && (
          <div className="px-3 pb-3">
            <ConfigSection
              configSchema={template.config_schema}
              configValues={moduleInstance.config}
            />
          </div>
        )}
      </div>
    </div>
  );
}

// NodeGroup Section Component
interface NodeGroupSectionProps {
  groupLabel: string;
  nodes: NodePin[];
  direction: "input" | "output";
  moduleId: string;
  template: ModuleTemplate;
  onTypeChange: (nodeId: string, newType: string) => void;
  onNameChange: (nodeId: string, newName: string) => void;
  onAddNode?: (moduleId: string, direction: "input" | "output", groupLabel: string) => void;
  onRemoveNode?: (moduleId: string, nodeId: string) => void;
  getConnectedOutputName?: (inputNodeId: string) => string | undefined;
  highlightedTypeVar: string | null;
  onTypeVarFocus: (typeVar: string | null) => void;
  onTextFocus?: () => void;
  onTextBlur?: () => void;
}

function NodeGroupSection({
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
}: NodeGroupSectionProps) {
  // Determine if these are static or dynamic nodes and get constraints
  const isStatic = nodes.length > 0 ? nodes[0].is_static : true;
  const groupKey = nodes.length > 0 ? nodes[0].group_key : undefined;

  let minCount = 1;
  let maxCount: number | undefined = undefined;

  if (!isStatic && groupKey) {
    // Look up the dynamic group in the template
    const ioShape = direction === "input"
      ? template.meta?.io_shape?.inputs
      : template.meta?.io_shape?.outputs;

    if (ioShape?.dynamic?.groups) {
      // Find the group by matching the label
      const group = ioShape.dynamic.groups.find((g: any) => g.item.label === groupLabel);
      if (group) {
        minCount = group.min_count || 1;
        maxCount = group.max_count;
      }
    }
  } else {
    // Static nodes cannot be added or removed
    minCount = nodes.length;
    maxCount = nodes.length;
  }

  const canAdd = maxCount === undefined || nodes.length < maxCount;
  const canRemove = nodes.length > minCount;

  return (
    <div className="mb-3 last:mb-0">
      {/* Group Label */}
      <div className="flex items-center mb-2">
        <div className="flex-1 border-t border-gray-600"></div>
        <span className="px-2 text-[10px] text-gray-400 uppercase font-semibold">
          {groupLabel}
        </span>
        <div className="flex-1 border-t border-gray-600"></div>
      </div>

      {/* Node Rows */}
      <div className="space-y-2">
        {nodes.map((node) => (
          <NodeRow
            key={node.node_id}
            node={node}
            direction={direction}
            canRemove={canRemove}
            onTypeChange={onTypeChange}
            onNameChange={onNameChange}
            onRemove={onRemoveNode ? () => onRemoveNode(moduleId, node.node_id) : undefined}
            getConnectedOutputName={getConnectedOutputName}
            highlightedTypeVar={highlightedTypeVar}
            onTypeVarFocus={onTypeVarFocus}
            onTextFocus={onTextFocus}
            onTextBlur={onTextBlur}
          />
        ))}

        {/* Add Node Button */}
        {canAdd && onAddNode && (
          <div className="relative flex items-center gap-2 py-1.5 group">
            <button
              onClick={() => onAddNode(moduleId, direction, groupLabel)}
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
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M12 4v16m8-8H4" />
              </svg>
            </button>
            <div className="flex-1 text-xs text-gray-300 font-medium px-2 py-1.5 border-2 border-dashed border-gray-500 bg-gray-800 rounded cursor-pointer group-hover:border-gray-400 group-hover:bg-gray-700 group-hover:text-white transition-colors text-center" onClick={() => onAddNode(moduleId, direction, groupLabel)}>
              Add {direction === "input" ? "Input" : "Output"}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Individual Node Row Component
interface NodeRowProps {
  node: NodePin;
  direction: "input" | "output";
  canRemove: boolean;
  onTypeChange: (nodeId: string, newType: string) => void;
  onNameChange: (nodeId: string, newName: string) => void;
  onRemove?: () => void;
  getConnectedOutputName?: (inputNodeId: string) => string | undefined;
  highlightedTypeVar: string | null;
  onTypeVarFocus: (typeVar: string | null) => void;
  onTextFocus?: () => void;
  onTextBlur?: () => void;
}

function NodeRow({
  node,
  direction,
  canRemove,
  onTypeChange,
  onNameChange,
  onRemove,
  getConnectedOutputName,
  highlightedTypeVar,
  onTypeVarFocus,
  onTextFocus,
  onTextBlur,
}: NodeRowProps) {
  const isHighlighted = node.type_var && node.type_var === highlightedTypeVar;
  const handleColor = TYPE_COLORS[node.type] || "#6B7280";

  // For input nodes, display connected output name or "Not Connected"
  const displayName =
    direction === "input"
      ? getConnectedOutputName?.(node.node_id) ?? "Not Connected"
      : node.name || "";

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
      />

      {/* Node Content - Mirrored layout based on direction */}
      {direction === "input" ? (
        // Input layout: [handle] name - type - delete
        <>
          <div className="w-1/2 pl-2 pr-2 flex items-center">
            <div className="text-xs text-gray-300 px-2 py-1 bg-gray-700 rounded border border-gray-600 break-words w-full min-h-[28px] flex items-center">
              {displayName}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-1 min-h-[28px] pl-1">
            <div className="w-20 flex items-center">
              <TypeIndicator
                node={node}
                onTypeChange={onTypeChange}
                onFocus={() => onTypeVarFocus(node.type_var || null)}
                onBlur={() => onTypeVarFocus(null)}
                isHighlighted={isHighlighted}
              />
            </div>
            <button
              onClick={canRemove && onRemove ? onRemove : undefined}
              className={`p-1 rounded transition-colors flex-shrink-0 mr-1 ${
                canRemove && onRemove
                  ? "text-gray-500 hover:text-red-400 hover:bg-red-900 cursor-pointer"
                  : "text-transparent cursor-default"
              }`}
              title={canRemove ? "Remove node" : ""}
              disabled={!canRemove || !onRemove}
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </>
      ) : (
        // Output layout: delete - type - name [handle]
        <>
          <div className="flex items-center gap-2 flex-1 min-h-[28px] pr-1">
            <button
              onClick={canRemove && onRemove ? onRemove : undefined}
              className={`p-1 rounded transition-colors flex-shrink-0 ml-1 ${
                canRemove && onRemove
                  ? "text-gray-500 hover:text-red-400 hover:bg-red-900 cursor-pointer"
                  : "text-transparent cursor-default"
              }`}
              title={canRemove ? "Remove node" : ""}
              disabled={!canRemove || !onRemove}
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <div className="w-20 flex items-center">
              <TypeIndicator
                node={node}
                onTypeChange={onTypeChange}
                onFocus={() => onTypeVarFocus(node.type_var || null)}
                onBlur={() => onTypeVarFocus(null)}
                isHighlighted={isHighlighted}
              />
            </div>
          </div>
          <div className="w-1/2 pr-2 pl-2 flex items-center">
            <textarea
              value={node.name}
              onChange={(e) => onNameChange(node.node_id, e.target.value)}
              onFocus={onTextFocus}
              onBlur={onTextBlur}
              placeholder="Node name"
              className="w-full text-xs bg-gray-700 text-gray-200 px-2 py-1 rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none overflow-hidden min-h-[28px]"
              rows={1}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = 'auto';
                target.style.height = target.scrollHeight + 'px';
              }}
            />
          </div>
        </>
      )}
    </div>
  );
}

// Type Indicator Component
interface TypeIndicatorProps {
  node: NodePin;
  onTypeChange: (nodeId: string, newType: string) => void;
  onFocus: () => void;
  onBlur: () => void;
  isHighlighted: boolean;
}

function TypeIndicator({ node, onTypeChange, onFocus, onBlur, isHighlighted }: TypeIndicatorProps) {
  // TODO: Get available types from template
  const availableTypes = ["str", "int", "float", "bool", "datetime"];
  const handleColor = TYPE_COLORS[node.type] || "#6B7280";

  const highlightStyle = isHighlighted
    ? {
        boxShadow: "inset 0 0 0 2px #facc15",
      }
    : {};

  if (availableTypes.length === 1) {
    // Static display
    return (
      <div
        className="text-[10px] px-1 py-0.5 rounded border"
        style={{
          borderLeftColor: handleColor,
          borderLeftWidth: "3px",
          backgroundColor: "#374151",
          color: "#D1D5DB",
          ...highlightStyle,
        }}
      >
        {node.type}
      </div>
    );
  }

  // Dropdown
  return (
    <select
      value={node.type}
      onChange={(e) => onTypeChange(node.node_id, e.target.value)}
      onFocus={onFocus}
      onBlur={onBlur}
      className="w-full text-[10px] bg-gray-700 text-gray-300 px-1 rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500 min-h-[28px]"
      style={{
        borderLeftColor: handleColor,
        borderLeftWidth: "3px",
        ...highlightStyle,
      }}
    >
      {availableTypes.map((type) => (
        <option key={type} value={type}>
          {type}
        </option>
      ))}
    </select>
  );
}

// Configuration Section Component
interface ConfigSectionProps {
  configSchema: any;
  configValues: Record<string, any>;
}

function ConfigSection({ configSchema, configValues }: ConfigSectionProps) {
  // TODO: Parse JSON schema and generate dynamic form fields
  return (
    <div className="text-xs text-gray-400 py-2">
      Configuration parsing coming soon...
      <pre className="text-[10px] mt-2">{JSON.stringify(configSchema, null, 2)}</pre>
    </div>
  );
}
