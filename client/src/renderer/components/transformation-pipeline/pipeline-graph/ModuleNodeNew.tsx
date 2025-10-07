import React, { useState, useCallback, useEffect } from "react";
import { Handle, Position } from "@xyflow/react";
import { ModuleTemplate, ModuleInstance, NodePin } from "../../../types/moduleTypes";
import { ConfigSection as ImportedConfigSection } from "./ConfigSection";

interface ModuleNodeNewProps {
  data: {
    moduleInstance: ModuleInstance;
    template: ModuleTemplate;
    onDeleteModule?: (moduleId: string) => void;
    onUpdateNode?: (moduleId: string, nodeId: string, updates: Partial<NodePin>) => void;
    onAddNode?: (moduleId: string, direction: "input" | "output", groupIndex: number) => void;
    onRemoveNode?: (moduleId: string, nodeId: string) => void;
    onConfigChange?: (moduleId: string, configKey: string, value: any) => void;
    onTextFocus?: () => void;
    onTextBlur?: () => void;
    onHandleClick?: (nodeId: string, handleId: string, handleType: 'source' | 'target') => void;
    pendingConnection?: {
      sourceHandleId: string;
      sourceNodeId: string;
      handleType: 'source' | 'target';
    } | null;
    getEffectiveAllowedTypes?: (moduleId: string, pinId: string, baseAllowedTypes: string[]) => string[];
    getConnectedOutputName?: (moduleId: string, inputPinId: string) => string | undefined;
  };
}

// Type to color mapping
const TYPE_COLORS: Record<string, string> = {
  str: "#3B82F6", // blue-500
  int: "#F59E0B", // orange-500
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

// Group nodes by their group_index
function groupNodesByIndex(nodes: NodePin[]): Map<number, NodePin[]> {
  const groups = new Map<number, NodePin[]>();

  nodes.forEach((node) => {
    const groupIndex = node.group_index;
    if (!groups.has(groupIndex)) {
      groups.set(groupIndex, []);
    }
    groups.get(groupIndex)!.push(node);
  });

  return groups;
}

export function ModuleNodeNew({ data }: ModuleNodeNewProps) {
  const { moduleInstance, template, onDeleteModule, onUpdateNode, onAddNode, onRemoveNode, onConfigChange, onTextFocus, onTextBlur, onHandleClick, pendingConnection, getEffectiveAllowedTypes, getConnectedOutputName: getConnectedOutputNameFromParent } = data;
  const [isConfigExpanded, setIsConfigExpanded] = useState(false);
  const [highlightedTypeVar, setHighlightedTypeVar] = useState<string | null>(null);

  // Auto-correct types when effective allowed types change and current type becomes invalid
  useEffect(() => {
    if (!getEffectiveAllowedTypes || !onUpdateNode) return;

    const allPins = [...moduleInstance.inputs, ...moduleInstance.outputs];

    allPins.forEach((pin) => {
      const effectiveTypes = getEffectiveAllowedTypes(
        moduleInstance.module_instance_id,
        pin.node_id,
        pin.allowed_types || []
      );

      // If current type is not in effective types, update to first valid type
      if (effectiveTypes.length > 0 && !effectiveTypes.includes(pin.type)) {
        onUpdateNode(moduleInstance.module_instance_id, pin.node_id, { type: effectiveTypes[0] });
      }
    });
  }, [moduleInstance, getEffectiveAllowedTypes, onUpdateNode]);

  // Group inputs and outputs
  const inputGroups = groupNodesByIndex(moduleInstance.inputs);
  const outputGroups = groupNodesByIndex(moduleInstance.outputs);

  // Get connected output name for an input node by looking at edges across modules
  const getConnectedOutputName = useCallback((inputNodeId: string): string | undefined => {
    if (!getConnectedOutputNameFromParent) return undefined;
    return getConnectedOutputNameFromParent(moduleInstance.module_instance_id, inputNodeId);
  }, [getConnectedOutputNameFromParent, moduleInstance.module_instance_id]);

  const handleTypeChange = (nodeId: string, newType: string) => {
    if (!onUpdateNode) return;

    // Find the node being changed to get its typevar
    const allNodes = [...moduleInstance.inputs, ...moduleInstance.outputs];
    const changedNode = allNodes.find(n => n.node_id === nodeId);

    if (!changedNode || !changedNode.type_var) {
      // No typevar, just update this node
      onUpdateNode(moduleInstance.module_instance_id, nodeId, { type: newType });
      return;
    }

    // Update all nodes with the same typevar
    const typeVar = changedNode.type_var;
    allNodes.forEach(node => {
      if (node.type_var === typeVar) {
        onUpdateNode(moduleInstance.module_instance_id, node.node_id, { type: newType });
      }
    });
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

  const handleConfigChange = (configKey: string, value: any) => {
    if (onConfigChange) {
      onConfigChange(moduleInstance.module_instance_id, configKey, value);
    }
  };

  const headerColor = template.color || "#4B5563";
  const textColor = getTextColor(headerColor);

  return (
    <div className="bg-gray-800 rounded-lg border-2 border-gray-600 min-w-[400px] w-min">
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
          {Array.from(inputGroups.entries()).map(([groupIndex, nodes]) => (
            <NodeGroupSection
              key={groupIndex}
              groupIndex={groupIndex}
              groupLabel={nodes[0]?.label || 'Group'}
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
              onHandleClick={onHandleClick}
              pendingConnection={pendingConnection}
              getEffectiveAllowedTypes={getEffectiveAllowedTypes}
            />
          ))}
        </div>

        {/* Outputs Section */}
        <div className="w-1/2 p-3">
          {Array.from(outputGroups.entries()).map(([groupIndex, nodes]) => (
            <NodeGroupSection
              key={groupIndex}
              groupIndex={groupIndex}
              groupLabel={nodes[0]?.label || 'Group'}
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
              onHandleClick={onHandleClick}
              pendingConnection={pendingConnection}
              getEffectiveAllowedTypes={getEffectiveAllowedTypes}
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
          <ImportedConfigSection
            schema={template.config_schema}
            config={moduleInstance.config}
            onConfigChange={handleConfigChange}
          />
        )}
      </div>
    </div>
  );
}

// NodeGroup Section Component
interface NodeGroupSectionProps {
  groupIndex: number;
  groupLabel: string;
  nodes: NodePin[];
  direction: "input" | "output";
  moduleId: string;
  template: ModuleTemplate;
  onTypeChange: (nodeId: string, newType: string) => void;
  onNameChange: (nodeId: string, newName: string) => void;
  onAddNode?: (moduleId: string, direction: "input" | "output", groupIndex: number) => void;
  onRemoveNode?: (moduleId: string, nodeId: string) => void;
  getConnectedOutputName?: (inputNodeId: string) => string | undefined;
  highlightedTypeVar: string | null;
  onTypeVarFocus: (typeVar: string | null) => void;
  onTextFocus?: () => void;
  onTextBlur?: () => void;
  onHandleClick?: (nodeId: string, handleId: string, handleType: 'source' | 'target') => void;
  pendingConnection?: {
    sourceHandleId: string;
    sourceNodeId: string;
    handleType: 'source' | 'target';
  } | null;
  getEffectiveAllowedTypes?: (moduleId: string, pinId: string, baseAllowedTypes: string[]) => string[];
}

function NodeGroupSection({
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
}: NodeGroupSectionProps) {
  // Get the NodeGroup from template
  const ioShape = direction === "input"
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
        <span className="px-2 text-[10px] text-gray-400 uppercase font-semibold">
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
            onRemove={onRemoveNode ? () => onRemoveNode(moduleId, node.node_id) : undefined}
            getConnectedOutputName={getConnectedOutputName}
            highlightedTypeVar={highlightedTypeVar}
            onTypeVarFocus={onTypeVarFocus}
            onTextFocus={onTextFocus}
            onTextBlur={onTextBlur}
            onHandleClick={onHandleClick}
            pendingConnection={pendingConnection}
            getEffectiveAllowedTypes={getEffectiveAllowedTypes}
          />
        ))}

        {/* Add Node Button */}
        {canAdd && onAddNode && (
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
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M12 4v16m8-8H4" />
              </svg>
            </button>
            <div className="flex-1 text-xs text-gray-300 font-medium px-2 py-1.5 border-2 border-dashed border-gray-500 bg-gray-800 rounded cursor-pointer group-hover:border-gray-400 group-hover:bg-gray-700 group-hover:text-white transition-colors text-center" onClick={() => onAddNode(moduleId, direction, groupIndex)}>
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
  onHandleClick?: (nodeId: string, handleId: string, handleType: 'source' | 'target') => void;
  pendingConnection?: {
    sourceHandleId: string;
    sourceNodeId: string;
    handleType: 'source' | 'target';
  } | null;
  getEffectiveAllowedTypes?: (moduleId: string, pinId: string, baseAllowedTypes: string[]) => string[];
}

function NodeRow({
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
  pendingConnection,
  getEffectiveAllowedTypes,
}: NodeRowProps) {
  const isHighlighted = node.type_var && node.type_var === highlightedTypeVar;
  const handleColor = TYPE_COLORS[node.type] || "#6B7280";

  // Check if this handle is the source of the pending connection
  const isPendingSource = pendingConnection?.sourceHandleId === node.node_id;

  // Handle click
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onHandleClick) {
      const handleType = direction === "input" ? "target" : "source";
      onHandleClick(moduleId, node.node_id, handleType);
    }
  };

  // For input nodes, display connected output name (even if empty) or "Not Connected"
  const connectedOutputName = direction === "input" ? getConnectedOutputName?.(node.node_id) : undefined;
  const displayName =
    direction === "input"
      ? connectedOutputName !== undefined ? connectedOutputName : "Not Connected"
      : node.name || "";

  // Ref for input textarea to auto-resize
  const inputTextareaRef = React.useRef<HTMLTextAreaElement>(null);

  // Auto-resize input textarea when displayName changes
  React.useEffect(() => {
    if (inputTextareaRef.current && direction === "input") {
      inputTextareaRef.current.style.height = 'auto';
      inputTextareaRef.current.style.height = inputTextareaRef.current.scrollHeight + 'px';
    }
  }, [displayName, direction]);

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
        // Input layout: [handle] name - type - delete
        <div className="flex items-center w-full gap-2">
          <div className="flex-[2] min-w-0 nodrag flex items-center">
            <textarea
              ref={inputTextareaRef}
              value={displayName}
              readOnly
              rows={1}
              className="text-[10px] text-gray-300 px-1.5 py-0.5 bg-gray-700 rounded border border-gray-600 w-full resize-none overflow-hidden cursor-default min-h-[24px]"
              style={{
                height: 'auto',
              }}
            />
          </div>
          <div className="flex-shrink-0 w-12 flex items-center">
            <TypeIndicator
              node={node}
              onTypeChange={onTypeChange}
              onFocus={() => onTypeVarFocus(node.type_var || null)}
              onBlur={() => onTypeVarFocus(null)}
              isHighlighted={isHighlighted}
              effectiveAllowedTypes={getEffectiveAllowedTypes?.(moduleId, node.node_id, node.allowed_types || [])}
            />
          </div>
          <div className="flex-shrink-0">
            <button
              onClick={canRemove && onRemove ? onRemove : undefined}
              className={`p-0.5 rounded transition-colors ${
                canRemove && onRemove
                  ? "text-gray-500 hover:text-red-400 hover:bg-red-900 cursor-pointer"
                  : "invisible cursor-default"
              }`}
              title={canRemove ? "Remove node" : ""}
              disabled={!canRemove || !onRemove}
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      ) : (
        // Output layout: delete - type - name [handle]
        <div className="flex items-center w-full gap-2">
          <div className="flex-shrink-0">
            <button
              onClick={canRemove && onRemove ? onRemove : undefined}
              className={`p-0.5 rounded transition-colors ${
                canRemove && onRemove
                  ? "text-gray-500 hover:text-red-400 hover:bg-red-900 cursor-pointer"
                  : "invisible cursor-default"
              }`}
              title={canRemove ? "Remove node" : ""}
              disabled={!canRemove || !onRemove}
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="flex-shrink-0 w-12 flex items-center">
            <TypeIndicator
              node={node}
              onTypeChange={onTypeChange}
              onFocus={() => onTypeVarFocus(node.type_var || null)}
              onBlur={() => onTypeVarFocus(null)}
              isHighlighted={isHighlighted}
              effectiveAllowedTypes={getEffectiveAllowedTypes?.(moduleId, node.node_id, node.allowed_types || [])}
            />
          </div>
          <div className="flex-[2] min-w-0 nodrag flex items-center">
            <textarea
              value={node.name}
              onChange={(e) => onNameChange(node.node_id, e.target.value)}
              onFocus={onTextFocus}
              onBlur={onTextBlur}
              placeholder="Node name"
              className="w-full text-[10px] bg-gray-700 text-gray-200 px-1.5 py-0.5 rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none overflow-hidden min-h-[24px] nodrag"
              rows={1}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = 'auto';
                target.style.height = target.scrollHeight + 'px';
              }}
            />
          </div>
        </div>
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
  effectiveAllowedTypes?: string[]; // Types that are actually available based on connections
}

function TypeIndicator({ node, onTypeChange, onFocus, onBlur, isHighlighted, effectiveAllowedTypes }: TypeIndicatorProps) {
  // Get available types from node's allowed_types, or all types if not specified
  const availableTypes = node.allowed_types || ["str", "int", "float", "bool", "datetime"];

  // Use effective types if provided (for showing disabled options), otherwise use available types
  const effectiveTypes = effectiveAllowedTypes || availableTypes;

  const highlightStyle = isHighlighted
    ? {
        boxShadow: "inset 0 0 0 2px #facc15",
      }
    : {};

  if (availableTypes.length === 1) {
    // Static display - same size as dropdown
    return (
      <div
        className="w-full text-[9px] px-0.5 py-0.5 rounded border border-gray-600 min-h-[24px] flex items-center justify-center"
        style={{
          backgroundColor: "#374151",
          color: "#D1D5DB",
          ...highlightStyle,
        }}
      >
        {node.type}
      </div>
    );
  }

  // Dropdown with disabled options for types not in effectiveTypes
  return (
    <select
      value={node.type}
      onChange={(e) => onTypeChange(node.node_id, e.target.value)}
      onFocus={onFocus}
      onBlur={onBlur}
      className="w-full text-[9px] bg-gray-700 text-gray-300 px-0.5 py-0.5 rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500 min-h-[24px]"
      style={highlightStyle}
    >
      {availableTypes.map((type) => {
        const isDisabled = !effectiveTypes.includes(type);
        return (
          <option key={type} value={type} disabled={isDisabled} className={isDisabled ? "text-gray-500" : ""}>
            {type}
          </option>
        );
      })}
    </select>
  );
}

