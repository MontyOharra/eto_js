/**
 * ExecutedModuleBody
 * Body section for executed module showing inputs/outputs in two-column layout
 * Groups pins by group_index and displays group labels
 */

import { ExecutedNodeGroup } from "./ExecutedNodeGroup";

interface PinData {
  name: string;
  value: string;
  type: string;
  group_index: number;
  label: string;
}

interface ExecutedModuleBodyProps {
  inputs: Record<string, PinData>;
  outputs: Record<string, PinData>;
  error?: string | null;
}

// Helper to group pins by group_index
function groupPinsByIndex(pins: Record<string, PinData>): Map<number, Array<{ nodeId: string; data: PinData }>> {
  const groups = new Map<number, Array<{ nodeId: string; data: PinData }>>();

  Object.entries(pins).forEach(([nodeId, data]) => {
    const groupIndex = data.group_index;
    if (!groups.has(groupIndex)) {
      groups.set(groupIndex, []);
    }
    groups.get(groupIndex)!.push({ nodeId, data });
  });

  return groups;
}

export function ExecutedModuleBody({
  inputs,
  outputs,
  error,
}: ExecutedModuleBodyProps) {
  // Group inputs and outputs by group_index
  const inputGroups = groupPinsByIndex(inputs);
  const outputGroups = groupPinsByIndex(outputs);

  const hasInputs = Object.keys(inputs).length > 0;
  const hasOutputs = Object.keys(outputs).length > 0;

  return (
    <>
      {/* Body - Two Column Layout */}
      <div className="flex">
        {/* Inputs Section - Left Column */}
        {hasInputs && (
          <div
            className={`${
              hasOutputs ? "w-1/2 border-r border-gray-600" : "w-full"
            } px-3 py-2`}
          >
            {Array.from(inputGroups.entries()).map(([groupIndex, pins]) => (
              <ExecutedNodeGroup
                key={groupIndex}
                groupLabel={pins[0]?.data.label || "Group"}
                nodes={pins.map(({ nodeId, data }) => ({
                  nodeId,
                  name: data.name,
                  type: data.type,
                  value: data.value,
                }))}
                direction="input"
              />
            ))}
          </div>
        )}

        {/* Outputs Section - Right Column */}
        {hasOutputs && (
          <div className={`${hasInputs ? "w-1/2" : "w-full"} px-3 py-2`}>
            {Array.from(outputGroups.entries()).map(([groupIndex, pins]) => (
              <ExecutedNodeGroup
                key={groupIndex}
                groupLabel={pins[0]?.data.label || "Group"}
                nodes={pins.map(({ nodeId, data }) => ({
                  nodeId,
                  name: data.name,
                  type: data.type,
                  value: data.value,
                }))}
                direction="output"
              />
            ))}
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="mx-3 mb-3 bg-red-900/50 border border-red-700 rounded px-3 py-2">
          <div className="text-xs text-red-300 font-semibold mb-1">ERROR</div>
          <div className="text-xs text-red-200">{error}</div>
        </div>
      )}
    </>
  );
}
