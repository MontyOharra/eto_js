/**
 * Pipeline Initialization Hook
 * Reconstructs pipeline from saved state or creates from entry points
 */

import { useEffect } from 'react';
import { Node, Edge } from '@xyflow/react';
import { ModuleTemplate, ModuleInstance, NodePin } from '../../../types/moduleTypes';
import { PipelineState, VisualState, EntryPoint } from '../../../types/pipelineTypes';
import { getTypeColor } from '../utils/edgeUtils';

export interface UsePipelineInitializationProps {
  moduleTemplates: ModuleTemplate[];
  initialPipelineState?: PipelineState;
  initialVisualState?: VisualState;
  entryPoints?: EntryPoint[];
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>;
  setEdges: React.Dispatch<React.SetStateAction<Edge[]>>;
}

/**
 * Create entry point nodes from EntryPoint data
 */
function createEntryPointNodes(entryPoints: EntryPoint[], visualState?: VisualState): Node[] {
  return entryPoints.map((ep, index) => {
    const position = visualState?.entryPoints?.[ep.node_id] || {
      x: 50 + index * 200,
      y: 50,
    };

    // Create fake module instance for visual rendering
    // Backend entry points don't have 'type', default to 'str'
    const entryPointType = (ep as any).type || 'str';

    const fakeModuleInstance: ModuleInstance = {
      module_instance_id: `entry-${ep.node_id}`,
      module_ref: 'entry_point:1.0.0',
      module_kind: 'transform',
      config: {},
      inputs: [],
      outputs: [
        {
          node_id: ep.node_id,
          direction: 'out',
          type: entryPointType,
          name: ep.name,
          label: ep.name,
          position_index: 0,
          group_index: 0,
          allowed_types: ['str'],
        },
      ],
    };

    // Create fake template for entry point
    const fakeTemplate: ModuleTemplate = {
      id: 'entry_point',
      version: '1.0.0',
      kind: 'transform',
      title: 'Entry Point',
      description: 'Pipeline entry point',
      color: '#000000',
      config_schema: {},
      meta: {
        io_shape: {
          inputs: { nodes: [] },
          outputs: {
            nodes: [
              {
                label: ep.name,
                min_count: 1,
                max_count: 1,
                typing: {
                  allowed_types: ['str'],
                },
              },
            ],
          },
          type_params: {},
        },
      },
    };

    return {
      id: `entry-${ep.node_id}`,
      type: 'module',
      position: { x: position.x, y: position.y },
      data: {
        moduleInstance: fakeModuleInstance,
        template: fakeTemplate,
        isEntryPoint: true,
        entryPoint: ep,
      },
    };
  });
}

/**
 * Reconstruct full NodePin objects from stored InstanceNodePins
 * Adds back UI-only fields (direction, label, type_var, allowed_types)
 */
function reconstructPins(
  pins: any[],
  direction: 'in' | 'out',
  template: ModuleTemplate
): NodePin[] {
  const ioSide =
    direction === 'in' ? template.meta.io_shape.inputs : template.meta.io_shape.outputs;

  return pins.map((pin) => {
    const group = ioSide.nodes[pin.group_index];
    if (!group) {
      console.warn(`Group not found at index ${pin.group_index}`);
      return pin;
    }

    const typeVar = group.typing.type_var;
    const allowedTypes = typeVar
      ? template.meta.io_shape.type_params[typeVar] || []
      : group.typing.allowed_types || [];

    return {
      ...pin,
      direction,
      label: group.label,
      type_var: typeVar,
      allowed_types: allowedTypes,
    };
  });
}

/**
 * Reconstruct pipeline from saved state
 */
function reconstructPipeline(
  pipelineState: PipelineState,
  visualState: VisualState,
  moduleTemplates: ModuleTemplate[]
): { nodes: Node[]; edges: Edge[] } {
  console.log('Reconstructing pipeline from initial state...');

  // Build entry point nodes
  const entryPointNodes = createEntryPointNodes(
    pipelineState.entry_points || [],
    visualState
  );

  // Build nodes from module instances
  const moduleNodes: Node[] = pipelineState.modules
    .map((moduleInstance) => {
      // Find the template for this module
      const [templateId, version] = moduleInstance.module_ref.split(':');
      const template = moduleTemplates.find(
        (t) => t.id === templateId && t.version === version
      );

      if (!template) {
        console.warn(`Template not found for module: ${moduleInstance.module_ref}`);
        return null;
      }

      // Get position from visual state
      const position = visualState.modules[moduleInstance.module_instance_id];
      if (!position) {
        console.warn(`Position not found for module: ${moduleInstance.module_instance_id}`);
        return null;
      }

      const fullModuleInstance: ModuleInstance = {
        ...moduleInstance,
        inputs: reconstructPins(moduleInstance.inputs, 'in', template),
        outputs: reconstructPins(moduleInstance.outputs, 'out', template),
      };

      return {
        id: moduleInstance.module_instance_id,
        type: 'module',
        position: { x: position.x, y: position.y },
        data: {
          moduleInstance: fullModuleInstance,
          template,
        },
      };
    })
    .filter(Boolean) as Node[];

  // Combine entry point nodes and module nodes
  const reconstructedNodes = [...entryPointNodes, ...moduleNodes];

  // Build edges from connections
  const reconstructedEdges: Edge[] = pipelineState.connections.map((connection, index) => {
    // Find source and target modules
    let sourceModuleId = '';
    let targetModuleId = '';
    let edgeColor = '#6B7280'; // default gray

    reconstructedNodes.forEach((node) => {
      const moduleInstance = node.data.moduleInstance as ModuleInstance;

      if (moduleInstance.outputs.some((p) => p.node_id === connection.from_node_id)) {
        sourceModuleId = node.id;

        // Get type for edge color
        const sourcePin = moduleInstance.outputs.find(
          (p) => p.node_id === connection.from_node_id
        );
        if (sourcePin) {
          edgeColor = getTypeColor(sourcePin.type);
        }
      }

      if (moduleInstance.inputs.some((p) => p.node_id === connection.to_node_id)) {
        targetModuleId = node.id;
      }
    });

    return {
      id: `edge-${index}`,
      source: sourceModuleId,
      sourceHandle: connection.from_node_id,
      target: targetModuleId,
      targetHandle: connection.to_node_id,
      style: { stroke: edgeColor, strokeWidth: 2 },
    };
  });

  console.log(
    `Reconstructed ${entryPointNodes.length} entry points, ${moduleNodes.length} modules (${reconstructedNodes.length} total nodes), and ${reconstructedEdges.length} edges`
  );

  return {
    nodes: reconstructedNodes,
    edges: reconstructedEdges,
  };
}

/**
 * Hook to initialize pipeline from state or entry points
 */
export function usePipelineInitialization({
  moduleTemplates,
  initialPipelineState,
  initialVisualState,
  entryPoints = [],
  setNodes,
  setEdges,
}: UsePipelineInitializationProps) {
  // Reconstruct from initial state (view mode)
  useEffect(() => {
    if (!initialPipelineState || !initialVisualState) return;

    const { nodes, edges } = reconstructPipeline(
      initialPipelineState,
      initialVisualState,
      moduleTemplates
    );

    setNodes(nodes);
    setEdges(edges);
  }, [initialPipelineState, initialVisualState, moduleTemplates, setNodes, setEdges]);

  // Create entry point nodes (create mode)
  useEffect(() => {
    if (initialPipelineState || initialVisualState) return; // Skip if in view mode
    if (entryPoints.length === 0) return;

    const entryPointNodes = createEntryPointNodes(entryPoints);
    setNodes(entryPointNodes);
  }, [entryPoints, initialPipelineState, initialVisualState, setNodes]);
}
