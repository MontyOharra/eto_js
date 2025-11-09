/**
 * ModuleBody Component
 * Displays inputs and outputs sections side by side
 */

import { ModuleTemplate } from "../../../modules/types";
import { ModuleInstance, NodePin } from "../../types";
import { groupNodesByIndex } from "../../utils/moduleUtils";
import { NodeGroupSection } from "./NodeGroupSection";

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
  // Group inputs and outputs
  const inputGroups = groupNodesByIndex(moduleInstance.inputs);
  const outputGroups = groupNodesByIndex(moduleInstance.outputs);

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

  const hasInputs = moduleInstance.inputs.length > 0;
  const hasOutputs = moduleInstance.outputs.length > 0;

  return (
    <div className="flex relative" style={{ pointerEvents: "auto" }}>
      {/* Inputs Section - only render if has inputs */}
      {hasInputs && (
        <div
          className={`${hasOutputs ? "w-1/2 border-r border-gray-600" : "w-full"} p-3`}
        >
          {Array.from(inputGroups.entries()).map(([groupIndex, nodes]) => (
            <NodeGroupSection
              key={groupIndex}
              groupIndex={groupIndex}
              groupLabel={nodes[0]?.label || "Group"}
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
          ))}
        </div>
      )}

      {/* Outputs Section - only render if has outputs */}
      {hasOutputs && (
        <div className={`${hasInputs ? "w-1/2" : "w-full"} p-3`}>
          {Array.from(outputGroups.entries()).map(([groupIndex, nodes]) => (
            <NodeGroupSection
              key={groupIndex}
              groupIndex={groupIndex}
              groupLabel={nodes[0]?.label || "Group"}
              nodes={nodes}
              direction="output"
              moduleId={moduleInstance.module_instance_id}
              template={template}
              onTypeChange={handleTypeChange}
              onNameChange={handleNameChange}
              onAddNode={onAddNode}
              onRemoveNode={onRemoveNode}
              highlightedTypeVar={highlightedTypeVar}
              onTypeVarFocus={onTypeVarFocus}
              onTextFocus={onTextFocus}
              onTextBlur={onTextBlur}
              onHandleClick={onHandleClick}
              getEffectiveAllowedTypes={getEffectiveAllowedTypes}
            />
          ))}
        </div>
      )}
    </div>
  );
}
