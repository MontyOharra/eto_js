/**
 * Pipeline Initialization Hook
 * Reconstructs pipeline from saved state or creates from entry points
 */

import { useEffect, useRef, useState } from 'react';
import { Node, Edge } from '@xyflow/react';
import { ModuleTemplate, ModuleInstance, NodePin } from '../../../types/moduleTypes';
import { PipelineState, VisualState, EntryPoint } from '../../../types/pipelineTypes';
import { getTypeColor } from '../utils/edgeUtils';

const ALL_TYPES = ['str', 'int', 'float', 'bool', 'datetime'];

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
    // Flat visual state: use entry point's node_id directly
    const position = visualState?.[ep.node_id] || {
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
    let allowedTypes: string[];

    if (typeVar) {
      const typeParamTypes = template.meta.io_shape.type_params[typeVar] || [];
      // Empty array means all types allowed (matches moduleFactory.ts logic)
      allowedTypes = typeParamTypes.length === 0 ? ALL_TYPES : typeParamTypes;
    } else {
      const directTypes = group.typing.allowed_types || [];
      // Empty array means all types allowed (matches moduleFactory.ts logic)
      allowedTypes = directTypes.length === 0 ? ALL_TYPES : directTypes;
    }

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

      // Get position from flat visual state
      const position = visualState[moduleInstance.module_instance_id];
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
 * Always reconstructs predictably from parent state
 */
export function usePipelineInitialization({
  moduleTemplates,
  initialPipelineState,
  initialVisualState,
  entryPoints = [],
  setNodes,
  setEdges,
}: UsePipelineInitializationProps) {
  const [isInitialized, setIsInitialized] = useState(false);
  const hasInitializedRef = useRef(false);

  useEffect(() => {
    // Only initialize once per mount
    if (hasInitializedRef.current) {
      console.log('[usePipelineInitialization] Already initialized, skipping');
      return;
    }

    // Wait for modules to load before initializing
    if (moduleTemplates.length === 0) {
      console.log('[usePipelineInitialization] Waiting for modules to load...');
      return;
    }

    console.log('[usePipelineInitialization] Initializing pipeline graph', {
      hasInitialPipelineState: !!initialPipelineState,
      entryPointsInState: initialPipelineState?.entry_points.length ?? 0,
      entryPointsProp: entryPoints.length,
      modulesInState: initialPipelineState?.modules.length ?? 0,
    });

    // ALWAYS reconstruct from state if entry points are present
    if (initialPipelineState && initialPipelineState.entry_points.length > 0) {
      console.log('[usePipelineInitialization] Reconstructing from saved state:', {
        modules: initialPipelineState.modules.length,
        connections: initialPipelineState.connections.length,
        entryPoints: initialPipelineState.entry_points.length,
        visualPositions: initialVisualState ? Object.keys(initialVisualState).length : 0,
        entryPointDetails: initialPipelineState.entry_points,
      });

      const { nodes, edges } = reconstructPipeline(
        initialPipelineState,
        initialVisualState || {},
        moduleTemplates
      );

      setNodes(nodes);
      setEdges(edges);
    } else {
      // Create fresh entry points if no saved state
      console.log('[usePipelineInitialization] Creating fresh entry points:', entryPoints.length);

      const entryPointNodes = createEntryPointNodes(entryPoints, initialVisualState);
      setNodes(entryPointNodes);
      setEdges([]);
    }

    hasInitializedRef.current = true;
    setIsInitialized(true);
    console.log('[usePipelineInitialization] Initialization complete');

    // Cleanup on unmount
    return () => {
      console.log('[usePipelineInitialization] Cleanup - resetting initialization flags');
      hasInitializedRef.current = false;
      setIsInitialized(false);
    };
  }, [initialPipelineState, initialVisualState, entryPoints, moduleTemplates, setNodes, setEdges]);

  console.log('[usePipelineInitialization] Current isInitialized:', isInitialized);
  return { isInitialized };
}
