/**
 * ExecutedEntryPoint
 * Wrapper around ExecutedModule with hardcoded values for entry points
 *
 * Entry points reuse the ExecutedModule component but with:
 * - Black header color
 * - "Entry Point" as module name
 * - No inputs
 * - Single string output with the entry point name
 *
 * Supports cross-component highlighting via FieldHighlightContext
 */

import { useCallback } from "react";
import { ExecutedModule } from "./ExecutedModule";
import { useFieldHighlight } from "../../contexts";

interface ExecutedEntryPointProps {
  data: {
    name: string;
    nodeId: string; // The node_id for the output handle
    entryPointId: string;
  };
}

export function ExecutedEntryPoint({ data }: ExecutedEntryPointProps) {
  const { name, nodeId, entryPointId } = data;
  const highlightContext = useFieldHighlight();

  // Check if this entry point is highlighted
  const isHighlighted = highlightContext?.highlightedFieldName === name;

  // Handlers for hover (only if context is available)
  const handleMouseEnter = useCallback(() => {
    highlightContext?.setHighlightedFieldName(name);
  }, [highlightContext, name]);

  const handleMouseLeave = useCallback(() => {
    highlightContext?.setHighlightedFieldName(null);
  }, [highlightContext]);

  // Hardcoded values for entry points
  const moduleData = {
    moduleName: "Entry Point",
    moduleColor: "#000000", // Black header
    moduleId: entryPointId,
    inputs: {}, // No inputs for entry points
    outputs: {
      [nodeId]: {
        name: name,
        value: "", // No value to display
        type: "str", // Always string type
        group_index: 0,
        label: "Output",
      },
    },
    status: "executed" as const,
    isHighlighted,
    onMouseEnter: highlightContext ? handleMouseEnter : undefined,
    onMouseLeave: highlightContext ? handleMouseLeave : undefined,
  };

  return <ExecutedModule data={moduleData} />;
}
