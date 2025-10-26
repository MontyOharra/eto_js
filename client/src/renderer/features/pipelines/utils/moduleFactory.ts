/**
 * Module Factory
 * Functions for creating and manipulating module instances
 */

import { ModuleTemplate, ModuleInstance, NodePin, IOSideShape } from '../../../types/moduleTypes';
import { initializeConfig } from '../../../utils/moduleFactoryNew';
import { generateModuleId, generateNodeId } from './idGenerator';

const ALL_TYPES = ['str', 'int', 'float', 'bool', 'datetime'];

/**
 * Create pins for a module based on IO shape
 */
function createPins(
  instanceId: string,
  ioShape: IOSideShape | undefined,
  direction: 'in' | 'out',
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
      const directTypes = nodeGroup.typing?.allowed_types || ['str'];
      // Empty array means all types allowed
      allowedTypes = directTypes.length === 0 ? ALL_TYPES : directTypes;
    }

    const defaultType = allowedTypes[0] || 'str';

    // Create min_count pins for this group
    for (let i = 0; i < nodeGroup.min_count; i++) {
      pins.push({
        node_id: generateNodeId(),
        direction,
        type: defaultType,
        name: '',
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
  instanceIdPrefix: string = 'module' // Kept for API compatibility but not used
): ModuleInstance {
  const instanceId = generateModuleId();

  const typeParams = template.meta?.io_shape?.type_params || {};
  const inputs = createPins(instanceId, template.meta?.io_shape?.inputs, 'in', typeParams);
  const outputs = createPins(instanceId, template.meta?.io_shape?.outputs, 'out', typeParams);

  // Initialize config with defaults from schema
  const config = initializeConfig(template.config_schema);

  return {
    module_instance_id: instanceId,
    module_ref: `${template.id}:${template.version}`,
    module_kind: template.kind,
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
  direction: 'input' | 'output',
  groupIndex: number
): ModuleInstance {
  const pins = direction === 'input' ? moduleInstance.inputs : moduleInstance.outputs;
  const ioSide =
    direction === 'input'
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
    const directTypes = nodeGroup.typing?.allowed_types || ['str'];
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
    direction: direction === 'input' ? 'in' : 'out',
    type: defaultType,
    name: '',
    label: nodeGroup.label,
    position_index: positionIndex,
    group_index: groupIndex,
    type_var: typeVar,
    allowed_types: allowedTypes,
  };

  if (direction === 'input') {
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
