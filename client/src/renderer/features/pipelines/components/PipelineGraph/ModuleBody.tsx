/**
 * ModuleBody Component
 * Displays inputs and outputs sections side by side
 */

import { ModuleTemplate, IOSideShape } from "../../../modules/types";
import { ModuleInstance, NodePin } from "../../types";
import { groupNodesByIndex } from "../../utils/moduleUtils";
import { NodeGroupSection } from "./NodeGroupSection";

/**
 * Get all group indices that should be rendered for an IO side.
 * This includes groups defined in the template even if they have no pins yet (min_count: 0).
 */
function getGroupIndices(ioShape: IOSideShape | undefined, pins: NodePin[]): number[] {
  const indices = new Set<number>();

  // Add all group indices from the template
  if (ioShape?.nodes) {
    ioShape.nodes.forEach((_, index) => indices.add(index));
  }

  // Also add any indices from existing pins (should already be covered, but just in case)
  pins.forEach(pin => indices.add(pin.group_index));

  return Array.from(indices).sort((a, b) => a - b);
}


export interface ModuleBodyProps {
  moduleInstance: ModuleInstance;
  template: ModuleTemplate;
  onUpdateNode?: (
    moduleId: string,
    nodeId: string,
    updates: Partial<NodePin>
  ) => void;
  onAddNode?: (
    moduleId: string,
    direction: "input" | "output",
    groupIndex: number
  ) => void;
  onRemoveNode?: (moduleId: string, nodeId: string) => void;
  onTextFocus?: () => void;
  onTextBlur?: () => void;
  onHandleClick?: (
    nodeId: string,
    handleId: string,
    handleType: "source" | "target"
  ) => void;
  getEffectiveAllowedTypes?: (
    moduleId: string,
    pinId: string,
    baseAllowedTypes: string[]
  ) => string[];
  getConnectedOutputName?: (
    inputPinId: string
  ) => string | undefined;
  highlightedTypeVar?: string | null;
  onTypeVarFocus?: (typeVar: string | null) => void;
}

export function ModuleBody({
  moduleInstance,
  template,
  onUpdateNode,
  onAddNode,
  onRemoveNode,
  onTextFocus,
  onTextBlur,
  onHandleClick,
  getEffectiveAllowedTypes,
  getConnectedOutputName,
  highlightedTypeVar = null,
  onTypeVarFocus = () => {},
}: ModuleBodyProps) {

  // Group inputs and outputs by their group_index
  const inputGroups = groupNodesByIndex(moduleInstance.inputs);
  const outputGroups = groupNodesByIndex(moduleInstance.outputs);

  // Get all group indices from templates (includes groups with min_count: 0 that have no pins yet)
  const inputGroupIndices = getGroupIndices(template.meta?.io_shape?.inputs, moduleInstance.inputs);
  const outputGroupIndices = getGroupIndices(template.meta?.io_shape?.outputs, moduleInstance.outputs);

  // Handle type changes (type_var synchronization handled by parent)
  const handleTypeChange = (nodeId: string, newType: string) => {
    if (!onUpdateNode) return;
    onUpdateNode(moduleInstance.module_instance_id, nodeId, {
      type: newType,
    });
  };

  const handleNameChange = (nodeId: string, newName: string) => {
    if (onUpdateNode) {
      onUpdateNode(moduleInstance.module_instance_id, nodeId, {
        name: newName,
      });
    }
  };

  // Wrapper to get connected output name
  const getConnectedName = (inputNodeId: string): string | undefined => {
    if (!getConnectedOutputName) return undefined;
    return getConnectedOutputName(
      inputNodeId
    );
  };

  const hasInputGroups = inputGroupIndices.length > 0;
  const hasOutputGroups = outputGroupIndices.length > 0;

  return (
    <div className="flex relative" style={{ pointerEvents: "auto" }}>
      {/* Inputs Section - render if template defines input groups */}
      {hasInputGroups && (
        <div
          className={`${hasOutputGroups ? "w-1/2 border-r border-gray-600" : "w-full"} p-3`}
        >
          {inputGroupIndices.map((groupIndex) => {
            const nodes = inputGroups.get(groupIndex) || [];
            const nodeGroup = template.meta?.io_shape?.inputs?.nodes[groupIndex];
            return (
              <NodeGroupSection
                key={groupIndex}
                groupIndex={groupIndex}
                groupLabel={nodes[0]?.label || nodeGroup?.label || "Group"}
                nodes={nodes}
                direction="input"
                moduleId={moduleInstance.module_instance_id}
                template={template}
                onTypeChange={handleTypeChange}
                onNameChange={handleNameChange}
                onAddNode={onAddNode}
                onRemoveNode={onRemoveNode}
                getConnectedOutputName={getConnectedName}
                highlightedTypeVar={highlightedTypeVar}
                onTypeVarFocus={onTypeVarFocus}
                onTextFocus={onTextFocus}
                onTextBlur={onTextBlur}
                onHandleClick={onHandleClick}
                getEffectiveAllowedTypes={getEffectiveAllowedTypes}
              />
            );
          })}
        </div>
      )}

      {/* Outputs Section - only render if has output groups */}
      {hasOutputGroups && (
        <div
          className={`${hasInputGroups ? "w-1/2 border-r border-gray-600" : "w-full"} p-3`}
        >
          {outputGroupIndices.map((groupIndex) => {
            const nodes = outputGroups.get(groupIndex) || [];
            const nodeGroup = template.meta?.io_shape?.outputs?.nodes[groupIndex];
            return (
              <NodeGroupSection
                key={groupIndex}
                groupIndex={groupIndex}
                groupLabel={nodes[0]?.label || nodeGroup?.label || "Group"}
                nodes={nodes}
                direction="output"
                moduleId={moduleInstance.module_instance_id}
                template={template}
                onTypeChange={handleTypeChange}
                onNameChange={handleNameChange}
                onAddNode={onAddNode}
                onRemoveNode={onRemoveNode}
                getConnectedOutputName={getConnectedName}
                highlightedTypeVar={highlightedTypeVar}
                onTypeVarFocus={onTypeVarFocus}
                onTextFocus={onTextFocus}
                onTextBlur={onTextBlur}
                onHandleClick={onHandleClick}
                getEffectiveAllowedTypes={getEffectiveAllowedTypes}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
