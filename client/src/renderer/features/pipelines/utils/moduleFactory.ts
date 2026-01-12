/**
 * Module Factory
 * Functions for creating and manipulating module instances
 */

import {
  ModuleTemplate,
  IOSideShape,
} from "../../modules/types";
import {
  ModuleInstance,
  NodePin,
  EntryPoint,
  OutputChannelInstance,
} from "../types";
import { generateModuleId, generateNodeId, generateOutputChannelId } from "./idGenerator";

const ALL_TYPES = ["str", "int", "float", "bool", "datetime"];

/**
 * Get default value for a JSON schema type
 */
function getDefaultForType(type: string): string | number | boolean | unknown[] | Record<string, unknown> | null {
  switch (type) {
    case "string":
      return "";
    case "number":
    case "integer":
      return 0;
    case "boolean":
      return false;
    case "array":
      return [];
    case "object":
      return {};
    default:
      return null;
  }
}

/**
 * Initialize config from JSON schema with defaults
 */
function initializeConfig(configSchema: Record<string, unknown> | undefined): Record<string, unknown> {
  const config: Record<string, unknown> = {};

  if (configSchema && typeof configSchema === 'object' && 'properties' in configSchema) {
    const properties = configSchema.properties as Record<string, unknown>;
    for (const [key, prop] of Object.entries(properties)) {
      const propDef = prop as Record<string, unknown>;
      if (propDef.default !== undefined) {
        config[key] = propDef.default;
      } else {
        config[key] = getDefaultForType(propDef.type as string);
      }
    }
  }

  return config;
}

/**
 * Create pins for a module based on IO shape
 */
function createPins(
  ioShape: IOSideShape | undefined,
  direction: "in" | "out",
  typeParams: Record<string, string[]>
): NodePin[] {
  const pins: NodePin[] = [];

  if (!ioShape?.nodes) return pins;

  ioShape.nodes.forEach((nodeGroup, groupIndex) => {
    const typeVar = nodeGroup.typing?.type_var;

    // Get allowed types: if typeVar exists, look it up in type_params, otherwise use allowed_types
    let allowedTypes: string[];
    if (typeVar && typeParams[typeVar]) {
      const typeParamTypes = typeParams[typeVar];
      // Empty array means all types allowed
      allowedTypes = typeParamTypes.length === 0 ? ALL_TYPES : typeParamTypes;
    } else {
      const directTypes = nodeGroup.typing?.allowed_types || ["str"];
      // Empty array means all types allowed
      allowedTypes = directTypes.length === 0 ? ALL_TYPES : directTypes;
    }

    const defaultType = allowedTypes[0] || "str";

    // Create min_count pins for this group
    for (let i = 0; i < nodeGroup.min_count; i++) {
      // Generate default name
      // Both input and output nodes start with empty strings
      // Input names will be updated when connections are made
      // Output names are set by the user
      const defaultName = "";

      pins.push({
        node_id: generateNodeId(),
        direction,
        type: defaultType,
        name: defaultName,
        label: nodeGroup.label,
        position_index: i,
        group_index: groupIndex,
        type_var: typeVar,
        allowed_types: allowedTypes,
      });
    }
  });

  return pins;
}

/**
 * Create a new module instance from a template
 */
export function createModuleInstance(
  template: ModuleTemplate,
): ModuleInstance {
  const instanceId = generateModuleId();

  const typeParams = template.meta?.io_shape?.type_params || {};
  const inputs = createPins(
    template.meta?.io_shape?.inputs,
    "in",
    typeParams
  );
  const outputs = createPins(
    template.meta?.io_shape?.outputs,
    "out",
    typeParams
  );

  // Initialize config with defaults from schema
  const config = initializeConfig(template.config_schema);

  return {
    module_instance_id: instanceId,
    module_id: template.module_id,
    config,
    inputs,
    outputs,
  };
}

/**
 * Add a new pin to a module instance
 */
export function addPinToModule(
  moduleInstance: ModuleInstance,
  template: ModuleTemplate,
  direction: "input" | "output",
  groupIndex: number
): ModuleInstance {
  const pins =
    direction === "input" ? moduleInstance.inputs : moduleInstance.outputs;
  const ioSide =
    direction === "input"
      ? template.meta?.io_shape?.inputs
      : template.meta?.io_shape?.outputs;

  if (!ioSide?.nodes[groupIndex]) {
    console.error(`No node group at index ${groupIndex}`);
    return moduleInstance;
  }

  const nodeGroup = ioSide.nodes[groupIndex];
  const typeParams = template.meta?.io_shape?.type_params || {};

  // Get allowed types
  const typeVar = nodeGroup.typing?.type_var;
  let allowedTypes: string[];
  if (typeVar && typeParams[typeVar]) {
    const typeParamTypes = typeParams[typeVar];
    allowedTypes = typeParamTypes.length === 0 ? ALL_TYPES : typeParamTypes;
  } else {
    const directTypes = nodeGroup.typing?.allowed_types || ["str"];
    allowedTypes = directTypes.length === 0 ? ALL_TYPES : directTypes;
  }

  // Find existing pins in this group to determine position
  const groupPins = pins.filter((p) => p.group_index === groupIndex);
  const positionIndex = groupPins.length;

  // If there are existing pins with a typevar, inherit their type
  let defaultType = allowedTypes[0];
  if (typeVar && groupPins.length > 0) {
    defaultType = groupPins[0].type;
  }

  const newPin: NodePin = {
    node_id: generateNodeId(),
    direction: direction === "input" ? "in" : "out",
    type: defaultType,
    name: "",
    label: nodeGroup.label,
    position_index: positionIndex,
    group_index: groupIndex,
    type_var: typeVar,
    allowed_types: allowedTypes,
  };

  if (direction === "input") {
    return {
      ...moduleInstance,
      inputs: [...moduleInstance.inputs, newPin],
    };
  } else {
    return {
      ...moduleInstance,
      outputs: [...moduleInstance.outputs, newPin],
    };
  }
}

/**
 * Remove a pin from a module instance
 */
export function removePinFromModule(
  moduleInstance: ModuleInstance,
  pinId: string
): ModuleInstance {
  return {
    ...moduleInstance,
    inputs: moduleInstance.inputs.filter((p) => p.node_id !== pinId),
    outputs: moduleInstance.outputs.filter((p) => p.node_id !== pinId),
  };
}

/**
 * Update a pin in a module instance
 */
export function updatePinInModule(
  moduleInstance: ModuleInstance,
  pinId: string,
  updates: Partial<NodePin>
): ModuleInstance {
  return {
    ...moduleInstance,
    inputs: moduleInstance.inputs.map((pin) =>
      pin.node_id === pinId ? { ...pin, ...updates } : pin
    ),
    outputs: moduleInstance.outputs.map((pin) =>
      pin.node_id === pinId ? { ...pin, ...updates } : pin
    ),
  };
}

/**
 * Update module config
 */
export function updateModuleConfig(
  moduleInstance: ModuleInstance,
  configKey: string,
  value: any
): ModuleInstance {
  return {
    ...moduleInstance,
    config: {
      ...moduleInstance.config,
      [configKey]: value,
    },
  };
}

/**
 * Entry point template definition (single source of truth)
 * Used by both the factory and EntryPoint component
 */
export const ENTRY_POINT_TEMPLATE: ModuleTemplate = {
  id: "entry_point",
  module_id: 0,  // Synthetic module - not in database
  version: "1.0.0",
  title: "Entry Point",
  description: "Pipeline entry point - provides initial data to the pipeline",
  kind: "entry_point",
  color: "#000000",
  category: "system",
  meta: {
    io_shape: {
      inputs: { nodes: [] },
      outputs: {
        nodes: [
          {
            label: "Output",
            min_count: 1,
            max_count: 1,
            typing: {
              allowed_types: ["str"],
            },
          },
        ],
      },
      type_params: {},
    },
  },
  config_schema: {},
};

/**
 * Create a new entry point from the template
 * Uses ENTRY_POINT_TEMPLATE as the single source of truth for structure
 */
export function createEntryPoint(
  entryPointId: string,
  name: string
): EntryPoint {
  const typeParams = ENTRY_POINT_TEMPLATE.meta?.io_shape?.type_params || {};

  // Create outputs using the template
  const outputs = createPins(
    ENTRY_POINT_TEMPLATE.meta?.io_shape?.outputs,
    "out",
    typeParams
  );

  // Override the generated output with the user-provided name and readonly flag
  if (outputs.length > 0) {
    outputs[0] = {
      ...outputs[0],
      node_id: `${entryPointId}_out`,
      name: name,
      readonly: true, // Entry point names are read-only
    };
  }

  return {
    entry_point_id: entryPointId,
    name: name,
    outputs: outputs,
  };
}

/**
 * Enrich a module instance loaded from backend with template metadata
 *
 * When modules are loaded from backend, pins only have:
 *   node_id, type, name, position_index, group_index
 *
 * This function reconstructs missing fields from the template:
 *   direction, label, type_var, allowed_types
 *
 * These fields are needed for proper rendering and type checking.
 */
export function enrichModuleWithTemplate(
  moduleInstance: ModuleInstance,
  template: ModuleTemplate
): ModuleInstance {
  const typeParams = template.meta?.io_shape?.type_params || {};
  const inputShape = template.meta?.io_shape?.inputs;
  const outputShape = template.meta?.io_shape?.outputs;

  // Enrich input pins
  const enrichedInputs = moduleInstance.inputs.map((pin) => {
    // Find the NodeGroup for this pin using group_index
    const nodeGroup = inputShape?.nodes?.[pin.group_index];
    if (!nodeGroup) {
      console.warn(`No NodeGroup found for input pin at group_index ${pin.group_index}`);
      return pin;
    }

    const typeVar = nodeGroup.typing?.type_var;

    // Calculate allowed_types the same way createPins does
    let allowedTypes: string[];
    if (typeVar && typeParams[typeVar]) {
      const typeParamTypes = typeParams[typeVar];
      allowedTypes = typeParamTypes.length === 0 ? ALL_TYPES : typeParamTypes;
    } else {
      const directTypes = nodeGroup.typing?.allowed_types || ["str"];
      allowedTypes = directTypes.length === 0 ? ALL_TYPES : directTypes;
    }

    return {
      ...pin,
      direction: "in" as const,
      label: nodeGroup.label,
      type_var: typeVar,
      allowed_types: allowedTypes,
    };
  });

  // Enrich output pins
  const enrichedOutputs = moduleInstance.outputs.map((pin) => {
    // Find the NodeGroup for this pin using group_index
    const nodeGroup = outputShape?.nodes?.[pin.group_index];
    if (!nodeGroup) {
      console.warn(`No NodeGroup found for output pin at group_index ${pin.group_index}`);
      return pin;
    }

    const typeVar = nodeGroup.typing?.type_var;

    // Calculate allowed_types the same way createPins does
    let allowedTypes: string[];
    if (typeVar && typeParams[typeVar]) {
      const typeParamTypes = typeParams[typeVar];
      allowedTypes = typeParamTypes.length === 0 ? ALL_TYPES : typeParamTypes;
    } else {
      const directTypes = nodeGroup.typing?.allowed_types || ["str"];
      allowedTypes = directTypes.length === 0 ? ALL_TYPES : directTypes;
    }

    return {
      ...pin,
      direction: "out" as const,
      label: nodeGroup.label,
      type_var: typeVar,
      allowed_types: allowedTypes,
    };
  });

  return {
    ...moduleInstance,
    inputs: enrichedInputs,
    outputs: enrichedOutputs,
  };
}

/**
 * Enrich an entry point loaded from backend with template metadata
 *
 * When entry points are loaded from backend, outputs only have:
 *   node_id, type, name, position_index, group_index
 *
 * This function reconstructs missing fields from ENTRY_POINT_TEMPLATE:
 *   direction, label, type_var, allowed_types
 */
export function enrichEntryPoint(entryPoint: EntryPoint): EntryPoint {
  const typeParams = ENTRY_POINT_TEMPLATE.meta?.io_shape?.type_params || {};
  const outputShape = ENTRY_POINT_TEMPLATE.meta?.io_shape?.outputs;

  // Enrich output pins (entry points only have outputs)
  const enrichedOutputs = entryPoint.outputs.map((pin) => {
    // Entry points always use the first (and only) NodeGroup in the template
    const nodeGroup = outputShape?.nodes?.[0];
    if (!nodeGroup) {
      console.warn(`No NodeGroup found in ENTRY_POINT_TEMPLATE`);
      return pin;
    }

    const typeVar = nodeGroup.typing?.type_var;

    // Calculate allowed_types (should always be ["str"] for entry points)
    let allowedTypes: string[];
    if (typeVar && typeParams[typeVar]) {
      const typeParamTypes = typeParams[typeVar];
      allowedTypes = typeParamTypes.length === 0 ? ALL_TYPES : typeParamTypes;
    } else {
      const directTypes = nodeGroup.typing?.allowed_types || ["str"];
      allowedTypes = directTypes.length === 0 ? ALL_TYPES : directTypes;
    }

    return {
      ...pin,
      direction: "out" as const,
      label: nodeGroup.label,
      type_var: typeVar,
      allowed_types: allowedTypes,
      readonly: true, // Entry point names are always read-only
    };
  });

  return {
    ...entryPoint,
    outputs: enrichedOutputs,
  };
}

// ============================================================================
// Output Channel Functions
// ============================================================================

/**
 * Color used for all output channel nodes
 */
export const OUTPUT_CHANNEL_COLOR = "#FFFFFF"; // white

/**
 * Create a ModuleTemplate for an output channel
 * Unlike ENTRY_POINT_TEMPLATE, this is generated per-channel since each has different types
 */
export function createOutputChannelTemplate(
  channelName: string,
  channelLabel: string,
  dataType: string
): ModuleTemplate {
  return {
    id: `output_channel_${channelName}`,
    module_id: 0,  // Synthetic - not from database
    version: "1.0.0",
    title: channelLabel,
    description: `Output channel for ${channelLabel}`,
    kind: "output_channel",
    color: OUTPUT_CHANNEL_COLOR,
    category: "system",
    meta: {
      io_shape: {
        inputs: {
          nodes: [
            {
              label: "Input",
              min_count: 1,
              max_count: 1,
              typing: {
                allowed_types: [dataType],
              },
            },
          ],
        },
        outputs: { nodes: [] },
        type_params: {},
      },
    },
    config_schema: {},
  };
}

/**
 * Create a new output channel instance
 */
export function createOutputChannelInstance(
  channelType: string,
  channelLabel: string,
  dataType: string
): OutputChannelInstance {
  const instanceId = generateOutputChannelId();
  const template = createOutputChannelTemplate(channelType, channelLabel, dataType);

  // Create input pin using the template
  const typeParams = template.meta?.io_shape?.type_params || {};
  const inputs = createPins(
    template.meta?.io_shape?.inputs,
    "in",
    typeParams
  );

  // Set the node_id to be based on the instance ID for consistency
  if (inputs.length > 0) {
    inputs[0] = {
      ...inputs[0],
      node_id: `${instanceId}_in`,
    };
  }

  return {
    output_channel_instance_id: instanceId,
    channel_type: channelType,
    inputs,
  };
}

/**
 * Enrich an output channel loaded from backend with template metadata
 */
export function enrichOutputChannel(
  outputChannel: OutputChannelInstance,
  channelLabel: string,
  dataType: string
): OutputChannelInstance {
  const template = createOutputChannelTemplate(
    outputChannel.channel_type,
    channelLabel,
    dataType
  );

  const inputShape = template.meta?.io_shape?.inputs;

  // Enrich input pins
  const enrichedInputs = outputChannel.inputs.map((pin) => {
    const nodeGroup = inputShape?.nodes?.[0];
    if (!nodeGroup) {
      console.warn(`No NodeGroup found for output channel input`);
      return pin;
    }

    return {
      ...pin,
      direction: "in" as const,
      label: nodeGroup.label,
      allowed_types: nodeGroup.typing?.allowed_types || [dataType],
    };
  });

  return {
    ...outputChannel,
    inputs: enrichedInputs,
  };
}
