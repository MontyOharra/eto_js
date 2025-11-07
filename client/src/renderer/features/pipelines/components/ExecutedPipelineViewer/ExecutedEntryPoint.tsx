/**
 * ExecutedEntryPoint
 * Wrapper around ExecutedModule with hardcoded values for entry points
 *
 * Entry points reuse the ExecutedModule component but with:
 * - Black header color
 * - "Entry Point" as module name
 * - No inputs
 * - Single string output with the entry point name
 */

import { ExecutedModule } from "./ExecutedModule";

interface ExecutedEntryPointProps {
  data: {
    name: string;
    nodeId: string; // The node_id for the output handle
  };
}

export function ExecutedEntryPoint({ data }: ExecutedEntryPointProps) {
  const { name, nodeId } = data;

  // Hardcoded values for entry points
  const moduleData = {
    moduleName: "Entry Point",
    moduleColor: "#000000", // Black header
    inputs: {}, // No inputs for entry points
    outputs: {
      [nodeId]: {
        name: name,
        value: "", // No value to display
        type: "str", // Always string type
      },
    },
    status: "executed" as const,
  };

  return <ExecutedModule data={moduleData} />;
}
