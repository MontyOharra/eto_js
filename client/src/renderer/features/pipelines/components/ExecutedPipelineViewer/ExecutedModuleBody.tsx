/**
 * ExecutedModuleBody
 * Body section for executed module showing inputs/outputs in two-column layout
 */

import { ExecutedModuleRow } from "./ExecutedModuleRow";

interface ExecutedModuleBodyProps {
  inputs: Record<string, { name: string; value: string; type: string }>;
  outputs: Record<string, { name: string; value: string; type: string }>;
  error?: string | null;
}

export function ExecutedModuleBody({
  inputs,
  outputs,
  error,
}: ExecutedModuleBodyProps) {
  const inputEntries = Object.entries(inputs);
  const outputEntries = Object.entries(outputs);
  const hasInputs = inputEntries.length > 0;
  const hasOutputs = outputEntries.length > 0;

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
            {inputEntries.map(([nodeId, data]) => (
              <ExecutedModuleRow
                key={nodeId}
                nodeId={nodeId}
                name={data.name}
                type={data.type}
                value={data.value}
                direction="input"
              />
            ))}
          </div>
        )}

        {/* Outputs Section - Right Column */}
        {hasOutputs && (
          <div className={`${hasInputs ? "w-1/2" : "w-full"} px-3 py-2`}>
            {outputEntries.map(([nodeId, data]) => (
              <ExecutedModuleRow
                key={nodeId}
                nodeId={nodeId}
                name={data.name}
                type={data.type}
                value={data.value}
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
