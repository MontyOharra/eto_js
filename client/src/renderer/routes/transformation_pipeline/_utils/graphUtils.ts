/**
 * Graph utility functions for the transformation pipeline
 */
import { BaseModuleTemplate } from '../../../types/modules';
import { NodeState, ModuleNodeState, PlacedModule, NodeConnection } from './types';

/**
 * Get color associated with a data type
 */
export const getTypeColor = (type: string): string => {
  switch (type) {
    case 'string': return '#3B82F6'; // Blue
    case 'number': return '#EF4444'; // Red  
    case 'boolean': return '#10B981'; // Green
    case 'datetime': return '#8B5CF6'; // Purple
    default: return '#6B7280'; // Gray
  }
};

/**
 * Get node type from module state
 */
export const getNodeType = (
  placedModules: PlacedModule[], 
  moduleId: string, 
  nodeType: 'input' | 'output', 
  nodeIndex: number
): string => {
  const module = placedModules.find(m => m.id === moduleId);
  if (!module) return 'string';
  
  const nodeList = nodeType === 'input' ? module.nodes.inputs : module.nodes.outputs;
  const node = nodeList[nodeIndex];
  return node?.type || 'string';
};

/**
 * Helper function to initialize module nodes from template
 */
export const initializeModuleNodes = (template: BaseModuleTemplate, config: Record<string, unknown>): ModuleNodeState => {
  let inputs: NodeState[] = [];
  let outputs: NodeState[] = [];
  
  // Use generateNodes if available for dynamic modules
  if (template.generateNodes) {
    const generated = template.generateNodes(config);
    inputs = generated.inputs.map((input, index) => ({
      id: `${template.id}_input_${index}`,
      name: input.name || `Input ${index + 1}`,
      type: input.type,
      description: input.description,
      required: input.required
    }));
    outputs = generated.outputs.map((output, index) => ({
      id: `${template.id}_output_${index}`,
      name: output.name || `Output ${index + 1}`,
      type: output.type,
      description: output.description,
      required: output.required || false
    }));
  } else {
    // Use static template definition
    inputs = template.inputs.map((input, index) => ({
      id: `${template.id}_input_${index}`,
      name: input.name || `Input ${index + 1}`,
      type: input.type,
      description: input.description,
      required: input.required
    }));
    outputs = template.outputs.map((output, index) => ({
      id: `${template.id}_output_${index}`,
      name: output.name || `Output ${index + 1}`,
      type: output.type,
      description: output.description,
      required: output.required || false
    }));
  }
  
  return { inputs, outputs };
};

/**
 * Get display name for input based on connections
 */
export const getInputDisplayName = (
  placedModules: PlacedModule[], 
  connections: NodeConnection[], 
  moduleId: string, 
  inputIndex: number
): string => {
  // Find connection to this input
  const connection = connections.find(conn => 
    conn.toModuleId === moduleId && conn.toInputIndex === inputIndex
  );
  
  if (!connection) {
    return "Not connected";
  }
  
  // Find the source module and output
  const sourceModule = placedModules.find(m => m.id === connection.fromModuleId);
  if (!sourceModule) {
    return "Not connected";
  }
  
  const sourceOutput = sourceModule.nodes.outputs[connection.fromOutputIndex];
  return sourceOutput?.name || `${sourceModule.template.name} Output`;
};

/**
 * Check if node type configuration is allowed
 */
export const getNodeTypeConfigAllowed = (placedModules: PlacedModule[], moduleId: string, nodeType: 'input' | 'output'): boolean => {
  const module = placedModules.find(m => m.id === moduleId);
  if (!module) return false;

  if (nodeType === 'input') {
    return module.template.dynamicInputs?.allowTypeConfiguration || false;
  } else {
    return module.template.dynamicOutputs?.allowTypeConfiguration || false;
  }
};

/**
 * Helper function to check if a node can change type based on connections
 */
export const canNodeChangeType = (
  placedModules: PlacedModule[], 
  connections: NodeConnection[], 
  moduleId: string, 
  nodeType: 'input' | 'output', 
  nodeIndex: number
): boolean => {
  // First check if this node itself allows type configuration
  if (!getNodeTypeConfigAllowed(placedModules, moduleId, nodeType)) {
    return false;
  }

  if (nodeType === 'input') {
    // Check if input is connected
    const connection = connections.find(conn => 
      conn.toModuleId === moduleId && conn.toInputIndex === nodeIndex
    );
    
    if (!connection) {
      return true; // No connection, can change type
    }
    
    // Input is connected - can only change if the output it's connected to also allows changes
    const sourceModule = placedModules.find(m => m.id === connection.fromModuleId);
    if (!sourceModule) return false;
    
    return canNodeChangeType(placedModules, connections, connection.fromModuleId, 'output', connection.fromOutputIndex);
  } else {
    // For outputs, check all connections that use this output
    const outputConnections = connections.filter(conn => 
      conn.fromModuleId === moduleId && conn.fromOutputIndex === nodeIndex
    );
    
    // If no connections, can change type freely
    if (outputConnections.length === 0) {
      return true;
    }
    
    // Check if all connected inputs allow type changes
    return outputConnections.every(conn => {
      const targetModule = placedModules.find(m => m.id === conn.toModuleId);
      if (!targetModule) return false;
      
      return canNodeChangeType(placedModules, connections, conn.toModuleId, 'input', conn.toInputIndex);
    });
  }
};

/**
 * Calculate grid size based on zoom level
 */
export const getGridSize = (zoomLevel: number): number => {
  if (zoomLevel <= 0.25) {
    return 100; // Large grid for very zoomed out
  } else if (zoomLevel <= 0.5) {
    return 50; // Medium grid for moderately zoomed out
  } else {
    return 20; // Fine grid for normal/zoomed in
  }
};

/**
 * Calculate grid opacity based on zoom level
 */
export const getGridOpacity = (zoomLevel: number): number => {
  if (zoomLevel <= 0.25) {
    return 0.2; // Less visible when very zoomed out
  } else if (zoomLevel <= 0.5) {
    return 0.25; // Slightly more visible
  } else {
    return 0.3; // Normal visibility
  }
};