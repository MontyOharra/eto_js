/**
 * PipelineGraph
 * Interactive pipeline editor and viewer with support for:
 * - View mode: Read-only visualization with pan/zoom and config expansion
 * - Edit mode: Full editing capabilities (add/remove modules, edit connections, etc.)
 */

import { useCallback, useState, useEffect, useMemo, useRef } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  Background,
  ReactFlowProvider,
  useReactFlow,
  BackgroundVariant,
  NodeChange,
  EdgeChange,
  Connection,
  applyNodeChanges,
  applyEdgeChanges,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { PipelineState, VisualState, EntryPoint, NodePin } from '../../types';
import type { ModuleTemplate } from '../../../modules/types';
import {
  createModuleInstance,
  addPinToModule,
  removePinFromModule,
  updatePinInModule,
  enrichModuleWithTemplate,
  enrichEntryPoint,
} from '../../utils/moduleFactory';
import { getTypeColor } from '../../utils/edgeUtils';
import { findPinInPipeline, synchronizeTypeVarUpdate } from '../../utils';
import { calculateNewEntryPointPosition } from '../../utils/layoutUtils';
import { getEffectiveAllowedTypes, validateConnection, calculateTypePropagation, applyTypeUpdates, TypeUpdate } from '../../utils/typeSystem';
import { Module } from './Module';
import { EntryPoint as EntryPointComponent } from './EntryPoint';

interface PipelineGraphProps {
  pipelineState?: PipelineState;
  visualState?: VisualState;
  entryPoints?: EntryPoint[]; // External entry points (overrides pipelineState.entry_points)
  mode?: 'view' | 'edit';
  modules?: ModuleTemplate[];
  selectedModuleId?: string | null;
  onModulePlaced?: () => void;
  onPipelineStateChange?: (newState: PipelineState) => void;
  onVisualStateChange?: (newState: VisualState) => void;
}

const nodeTypes = {
  module: Module,
  entryPoint: EntryPointComponent,
};

const edgeTypes = {
  // TODO: Add custom edge types
};

function PipelineGraphInner({
  pipelineState,
  visualState,
  entryPoints,
  mode = 'view',
  modules = [],
  onModulePlaced,
  onPipelineStateChange,
  onVisualStateChange,
}: PipelineGraphProps) {
  const { screenToFlowPosition } = useReactFlow();

  // Internal state - React Flow manages positions
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  // Use external entry points if provided, otherwise use pipelineState.entry_points
  // Enrich entry points with template metadata (similar to modules)
  // Backend only stores: node_id, type, name, position_index, group_index
  // We reconstruct: direction, label, type_var, allowed_types
  const effectiveEntryPoints = useMemo(() => {
    const rawEntryPoints = entryPoints ?? pipelineState?.entry_points ?? [];
    // Enrich each entry point to add missing fields from ENTRY_POINT_TEMPLATE
    return rawEntryPoints.map(enrichEntryPoint);
  }, [entryPoints, pipelineState?.entry_points]);

  // Enrich pipeline state with template metadata when loaded from backend
  // Backend only stores: node_id, type, name, position_index, group_index
  // We reconstruct: direction, label, type_var, allowed_types from templates
  const enrichedPipelineState = useMemo(() => {
    if (!pipelineState) return undefined;

    const enrichedModules = pipelineState.modules.map((moduleInstance) => {
      // Find template by parsing module_ref (e.g., "text_cleaner:1.0.0")
      const [templateId] = moduleInstance.module_ref.split(':');
      const template = modules.find((t) => t.id === templateId);

      if (!template) {
        console.warn(`[PipelineGraph] Template not found for module: ${moduleInstance.module_ref}`);
        return moduleInstance; // Return unchanged if template not found
      }

      // Enrich with template metadata
      return enrichModuleWithTemplate(moduleInstance, template);
    });

    return {
      ...pipelineState,
      modules: enrichedModules,
    };
  }, [pipelineState, modules]);

  // Effective types cache - pre-calculated for all pins
  const [effectiveTypesCache, setEffectiveTypesCache] = useState<
    Map<string, string[]>
  >(new Map());

  // Track connections removed during current drag operation (for immediate validation)
  const removedConnectionsRef = useRef<Set<string>>(new Set());

  // Recalculate effective types cache when connections or modules change
  useEffect(() => {
    if (!enrichedPipelineState) {
      setEffectiveTypesCache(new Map());
      return;
    }

    const newCache = new Map<string, string[]>();

    // Calculate effective types for all pins in all modules (use enriched state for correct allowed_types)
    enrichedPipelineState.modules.forEach((module) => {
      [...module.inputs, ...module.outputs].forEach((pin) => {
        const key = `${module.module_instance_id}:${pin.node_id}`;
        const effectiveTypes = getEffectiveAllowedTypes(
          enrichedPipelineState,
          effectiveEntryPoints,
          module.module_instance_id,
          pin.node_id,
          pin.allowed_types || []
        );
        newCache.set(key, effectiveTypes);
      });
    });

    // Entry points always allow 'str' only
    effectiveEntryPoints.forEach((ep) => {
      ep.outputs.forEach((pin) => {
        const key = `${ep.entry_point_id}:${pin.node_id}`;
        newCache.set(key, ['str']);
      });
    });

    setEffectiveTypesCache(newCache);
  }, [enrichedPipelineState, effectiveEntryPoints]);

  // Helper to get cached effective types for a pin
  const getEffectiveAllowedTypesForPin = useCallback(
    (moduleId: string, pinId: string): string[] => {
      const key = `${moduleId}:${pinId}`;
      return effectiveTypesCache.get(key) || [];
    },
    [effectiveTypesCache]
  );

  // Helper to find a pin by its node_id
  const findPin = useCallback(
    (nodeId: string): NodePin | undefined => {
      if (!pipelineState) return undefined;
      return findPinInPipeline(nodeId, effectiveEntryPoints, pipelineState.modules);
    },
    [pipelineState, effectiveEntryPoints]
  );

  // Handle updating a node (type or name change) with type propagation
  const handleUpdateNode = useCallback(
    (moduleId: string, nodeId: string, updates: Partial<NodePin>) => {
      if (!pipelineState || !enrichedPipelineState || !onPipelineStateChange) return;

      // Find the module to update in both raw and enriched states
      const moduleIndex = pipelineState.modules.findIndex(
        (m) => m.module_instance_id === moduleId
      );
      if (moduleIndex === -1) return;

      const module = pipelineState.modules[moduleIndex];
      const enrichedModule = enrichedPipelineState.modules[moduleIndex];

      // Handle type changes with type propagation
      if (updates.type) {
        console.log('[TypeVar DEBUG] ========== START TYPE UPDATE ==========');
        console.log('[TypeVar DEBUG] Module:', moduleId, 'Pin:', nodeId, 'New Type:', updates.type);

        // First, apply type_var synchronization within the module (use enriched for correct metadata)
        const result = synchronizeTypeVarUpdate(enrichedModule, nodeId, updates.type);

        console.log('[TypeVar DEBUG] After synchronizeTypeVarUpdate:');
        console.log('[TypeVar DEBUG]   wasTypeVarUpdate:', result.wasTypeVarUpdate);
        console.log('[TypeVar DEBUG]   updatedModule inputs:', result.updatedModule.inputs.map(p => ({ id: p.node_id, name: p.name, type: p.type, type_var: p.type_var })));
        console.log('[TypeVar DEBUG]   updatedModule outputs:', result.updatedModule.outputs.map(p => ({ id: p.node_id, name: p.name, type: p.type, type_var: p.type_var })));

        // Apply to temporary enriched state for type propagation calculation
        const updatedEnrichedModules = [...enrichedPipelineState.modules];
        updatedEnrichedModules[moduleIndex] = result.updatedModule;
        const tempEnrichedPipelineState = {
          ...enrichedPipelineState,
          modules: updatedEnrichedModules,
        };

        // Build initial updates for type propagation
        // Include the main pin and all type_var siblings
        const initialUpdates: TypeUpdate[] = [
          { moduleId, pinId: nodeId, newType: updates.type }
        ];

        if (result.wasTypeVarUpdate) {
          const allPins = [...result.updatedModule.inputs, ...result.updatedModule.outputs];
          const targetPin = allPins.find(p => p.node_id === nodeId);
          if (targetPin?.type_var) {
            allPins.forEach(pin => {
              if (pin.type_var === targetPin.type_var && pin.node_id !== nodeId) {
                initialUpdates.push({ moduleId, pinId: pin.node_id, newType: updates.type });
              }
            });
          }
        }

        console.log('[TypeVar DEBUG] initialUpdates:', initialUpdates);

        // Calculate propagation through connections (use enriched state for correct allowed_types)
        const allUpdates = calculateTypePropagation(
          tempEnrichedPipelineState,
          effectiveEntryPoints,
          initialUpdates
        );

        console.log('[TypeVar DEBUG] allUpdates (after propagation):', allUpdates);

        // Apply all type updates to RAW state (we persist raw data)
        const updatedModules = [...pipelineState.modules];
        updatedModules[moduleIndex] = updatePinInModule(module, nodeId, updates);
        const tempRawPipelineState = {
          ...pipelineState,
          modules: updatedModules,
        };
        console.log('[TypeVar DEBUG] tempRawPipelineState module before applyTypeUpdates:', tempRawPipelineState.modules[moduleIndex].inputs.map(p => ({ id: p.node_id, type: p.type })), tempRawPipelineState.modules[moduleIndex].outputs.map(p => ({ id: p.node_id, type: p.type })));

        const finalPipelineState = applyTypeUpdates(tempRawPipelineState, allUpdates);

        console.log('[TypeVar DEBUG] finalPipelineState module after applyTypeUpdates:', finalPipelineState.modules[moduleIndex].inputs.map(p => ({ id: p.node_id, type: p.type })), finalPipelineState.modules[moduleIndex].outputs.map(p => ({ id: p.node_id, type: p.type })));
        console.log('[TypeVar DEBUG] ========== END TYPE UPDATE ==========');

        onPipelineStateChange(finalPipelineState);
      } else {
        // Non-type update (e.g., name change) - no propagation needed
        const updatedModule = updatePinInModule(module, nodeId, updates);
        const updatedModules = [...pipelineState.modules];
        updatedModules[moduleIndex] = updatedModule;

        onPipelineStateChange({
          ...pipelineState,
          modules: updatedModules,
        });
      }
    },
    [pipelineState, enrichedPipelineState, effectiveEntryPoints, onPipelineStateChange]
  );

  // Handle adding a new node to a module
  const handleAddNode = useCallback(
    (moduleId: string, direction: 'input' | 'output', groupIndex: number) => {
      if (!pipelineState || !onPipelineStateChange) return;

      // Find the module to update
      const moduleIndex = pipelineState.modules.findIndex(
        (m) => m.module_instance_id === moduleId
      );
      if (moduleIndex === -1) return;

      const module = pipelineState.modules[moduleIndex];
      const template = modules.find((t) => t.id === module.module_ref.split(':')[0]);
      if (!template) return;

      const updatedModule = addPinToModule(module, template, direction, groupIndex);

      // Update pipeline state
      const updatedModules = [...pipelineState.modules];
      updatedModules[moduleIndex] = updatedModule;

      onPipelineStateChange({
        ...pipelineState,
        modules: updatedModules,
      });
    },
    [pipelineState, onPipelineStateChange, modules]
  );

  // Handle removing a node from a module
  const handleRemoveNode = useCallback(
    (moduleId: string, nodeId: string) => {
      if (!pipelineState || !onPipelineStateChange) return;

      // Find the module to update
      const moduleIndex = pipelineState.modules.findIndex(
        (m) => m.module_instance_id === moduleId
      );
      if (moduleIndex === -1) return;

      const module = pipelineState.modules[moduleIndex];
      const updatedModule = removePinFromModule(module, nodeId);

      // Update pipeline state
      const updatedModules = [...pipelineState.modules];
      updatedModules[moduleIndex] = updatedModule;

      onPipelineStateChange({
        ...pipelineState,
        modules: updatedModules,
      });

      // TODO: Also remove any connections involving this node
    },
    [pipelineState, onPipelineStateChange]
  );

  // Handle deleting an entire module
  const handleDeleteModule = useCallback(
    (moduleId: string) => {
      if (!pipelineState || !onPipelineStateChange || !onVisualStateChange) return;

      // Remove module from pipeline state
      const updatedModules = pipelineState.modules.filter(
        (m) => m.module_instance_id !== moduleId
      );

      onPipelineStateChange({
        ...pipelineState,
        modules: updatedModules,
      });

      // Remove from visual state
      const updatedVisualState = { ...visualState };
      delete updatedVisualState[moduleId];
      onVisualStateChange(updatedVisualState);

      // TODO: Also remove any connections involving this module
    },
    [pipelineState, visualState, onPipelineStateChange, onVisualStateChange]
  );

  // Handle config changes
  const handleConfigChange = useCallback(
    (moduleId: string, configKey: string, value: any) => {
      if (!pipelineState || !onPipelineStateChange) return;

      // Find the module to update
      const moduleIndex = pipelineState.modules.findIndex(
        (m) => m.module_instance_id === moduleId
      );
      if (moduleIndex === -1) return;

      const module = pipelineState.modules[moduleIndex];

      // Update config
      const updatedModule = {
        ...module,
        config: {
          ...module.config,
          [configKey]: value,
        },
      };

      // Update pipeline state
      const updatedModules = [...pipelineState.modules];
      updatedModules[moduleIndex] = updatedModule;

      onPipelineStateChange({
        ...pipelineState,
        modules: updatedModules,
      });
    },
    [pipelineState, onPipelineStateChange]
  );

  // Get the name of the output pin connected to an input pin
  const getConnectedOutputName = useCallback(
    (inputPinId: string): string | undefined => {
      if (!pipelineState) return undefined;

      // Find the connection where this input is the target
      const connection = pipelineState.connections.find(
        (conn) => conn.to_node_id === inputPinId
      );

      if (!connection) return undefined;

      // Find the source output pin
      const sourcePin = findPin(connection.from_node_id);
      return sourcePin?.name;
    },
    [pipelineState, findPin]
  );

  // Initialize/update nodes when pipeline state or modules change
  useEffect(() => {
    if (!enrichedPipelineState) {
      setNodes([]);
      return;
    }

    const newNodes: Node[] = [];
    const newPositions: Record<string, { x: number; y: number }> = {};

    // Create entry point nodes from effectiveEntryPoints
    effectiveEntryPoints.forEach((entryPoint) => {
      let position = visualState?.[entryPoint.entry_point_id];

      if (!position) {
        // Calculate position for new entry point
        position = calculateNewEntryPointPosition(newNodes);
        newPositions[entryPoint.entry_point_id] = position;
      }

      newNodes.push({
        id: entryPoint.entry_point_id,
        type: 'entryPoint',
        position,
        data: {
          entryPoint,
        },
        draggable: mode === 'edit',
      });
    });

    // Create module nodes (using enriched state with template metadata)
    enrichedPipelineState.modules.forEach((moduleInstance) => {
      // Find the template for this module
      const [templateId] = moduleInstance.module_ref.split(':');
      const template = modules.find((t) => t.id === templateId);

      // Skip if template not found
      if (!template) {
        console.warn(`Template not found for module: ${moduleInstance.module_ref}`);
        return;
      }

      // In view mode, mark all outputs as readonly
      const moduleInstanceForDisplay = mode === 'view' ? {
        ...moduleInstance,
        outputs: moduleInstance.outputs.map(output => ({
          ...output,
          readonly: true,
        })),
      } : moduleInstance;

      newNodes.push({
        id: moduleInstance.module_instance_id,
        type: 'module',
        position: visualState?.[moduleInstance.module_instance_id] || { x: 0, y: 0 },
        data: {
          moduleInstance: moduleInstanceForDisplay,
          template,
          // Edit callbacks
          onDeleteModule: mode === 'edit' ? handleDeleteModule : undefined,
          onUpdateNode: mode === 'edit' ? handleUpdateNode : undefined,
          onAddNode: mode === 'edit' ? handleAddNode : undefined,
          onRemoveNode: mode === 'edit' ? handleRemoveNode : undefined,
          onConfigChange: mode === 'edit' ? handleConfigChange : undefined,
          // Type narrowing - provide effective allowed types
          getEffectiveAllowedTypes: getEffectiveAllowedTypesForPin,
          // Connected output name for inputs
          getConnectedOutputName: getConnectedOutputName,
        },
        draggable: mode === 'edit',
      });
    });

    setNodes(newNodes);

    // Persist any newly calculated entry point positions to visualState
    if (Object.keys(newPositions).length > 0 && onVisualStateChange) {
      onVisualStateChange({
        ...visualState,
        ...newPositions,
      });
    }
  }, [enrichedPipelineState, visualState, modules, mode, effectiveEntryPoints, handleDeleteModule, handleUpdateNode, handleAddNode, handleRemoveNode, handleConfigChange, getEffectiveAllowedTypesForPin, getConnectedOutputName, onVisualStateChange]);

  // Initialize/update edges when pipeline state changes
  useEffect(() => {
    if (!pipelineState) {
      setEdges([]);
      return;
    }

    // Create edges from connections
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const newEdges: Edge[] = pipelineState.connections.map((connection, _) => {
      // Find source and target nodes by searching for pins
      let sourceNodeId = '';
      let targetNodeId = '';

      // Check entry points for source
      effectiveEntryPoints.forEach((ep) => {
        if (ep.outputs.some((out) => out.node_id === connection.from_node_id)) {
          sourceNodeId = ep.entry_point_id;
        }
      });

      // Check modules for source/target
      pipelineState.modules.forEach((module) => {
        if (module.outputs.some((out) => out.node_id === connection.from_node_id)) {
          sourceNodeId = module.module_instance_id;
        }
        if (module.inputs.some((inp) => inp.node_id === connection.to_node_id)) {
          targetNodeId = module.module_instance_id;
        }
      });

      // Get the source pin to determine edge color
      const sourcePin = findPin(connection.from_node_id);
      const edgeColor = sourcePin ? getTypeColor(sourcePin.type) : '#6B7280';

      return {
        id: `${connection.from_node_id}-${connection.to_node_id}`,
        source: sourceNodeId,
        target: targetNodeId,
        sourceHandle: connection.from_node_id,
        targetHandle: connection.to_node_id,
        type: 'default',
        reconnectable: mode === 'edit',
        style: {
          stroke: edgeColor,
          strokeWidth: 2,
        },
        data: {
          sourcePin,
        },
      };
    });

    setEdges(newEdges);
  }, [pipelineState, mode, effectiveEntryPoints, findPin]);

  // Handle node position changes
  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      if (mode === 'view') return; // Ignore in view mode

      // Apply changes to internal node state (enables smooth dragging)
      setNodes((nds) => applyNodeChanges(changes, nds));

      // Only update visual state when drag ends (for persistence)
      const isDragEnd = changes.some(
        (change) => change.type === 'position' && change.dragging === false
      );

      if (isDragEnd && onVisualStateChange) {
        // Extract final positions from changes
        setNodes((currentNodes) => {
          const updatedVisualState = { ...visualState };

          currentNodes.forEach((node) => {
            updatedVisualState[node.id] = node.position;
          });

          onVisualStateChange(updatedVisualState);
          return currentNodes;
        });
      }
    },
    [mode, visualState, onVisualStateChange]
  );

  // Handle edge changes
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      if (mode === 'view') return; // Ignore in view mode

      // Apply changes to internal edge state and update selection styling
      setEdges((eds) => {
        const updatedEdges = applyEdgeChanges(changes, eds);

        // Update styling based on selection
        return updatedEdges.map((edge) => ({
          ...edge,
          animated: edge.selected || false,
          className: edge.selected ? 'selected-edge' : '',
        }));
      });

      // Handle edge deletion
      if (pipelineState && onPipelineStateChange) {
        const removedEdges = changes.filter((c) => c.type === 'remove');
        if (removedEdges.length > 0) {
          const edgeIdsToRemove = removedEdges.map((c) => (c as any).id);
          const updatedConnections = pipelineState.connections.filter((conn) => {
            const edgeId = `${conn.from_node_id}-${conn.to_node_id}`;
            return !edgeIdsToRemove.includes(edgeId);
          });

          onPipelineStateChange({
            ...pipelineState,
            connections: updatedConnections,
          });
        }
      }
    },
    [mode, pipelineState, onPipelineStateChange]
  );

  // Validate connection based on effective allowed types (with type narrowing)
  const isValidConnection = useCallback(
    (connection: Connection) => {
      if (!connection.sourceHandle || !connection.targetHandle) return false;
      if (!connection.source || !connection.target) return false;
      if (!enrichedPipelineState) return false;

      // Create temporary pipelineState excluding connections that were removed during this drag
      // This allows validation to work correctly even before React state update completes
      const tempPipelineState = {
        ...enrichedPipelineState,
        connections: enrichedPipelineState.connections.filter((conn) => {
          const connKey = `${conn.from_node_id}-${conn.to_node_id}`;
          return !removedConnectionsRef.current.has(connKey);
        }),
      };

      // Use validateConnection from typeSystem with effective types
      const result = validateConnection(
        tempPipelineState,
        effectiveEntryPoints,
        connection.source,
        connection.sourceHandle,
        connection.target,
        connection.targetHandle
      );

      return result.valid;
    },
    [enrichedPipelineState, effectiveEntryPoints]
  );

  // Handle new connections with type propagation
  const onConnect = useCallback(
    (connection: Connection) => {
      // Clear removed connections tracker (drag operation complete)
      removedConnectionsRef.current.clear();

      if (mode === 'view' || !pipelineState || !enrichedPipelineState || !onPipelineStateChange) return;
      if (!connection.source || !connection.target || !connection.sourceHandle || !connection.targetHandle) return;

      const sourceHandle = connection.sourceHandle;
      const targetHandle = connection.targetHandle;

      // Validate connection and get suggested type (use enriched state for correct allowed_types)
      const validation = validateConnection(
        enrichedPipelineState,
        effectiveEntryPoints,
        connection.source,
        sourceHandle,
        connection.target,
        targetHandle
      );

      if (!validation.valid || !validation.suggestedType) return;

      // Check if this exact connection already exists (prevent duplicates)
      const isDuplicate = pipelineState.connections.some(
        (conn) => conn.from_node_id === sourceHandle && conn.to_node_id === targetHandle
      );
      if (isDuplicate) return;

      // Remove any existing connections from this source or to this target (enforce 1-to-1)
      const updatedConnections = pipelineState.connections.filter(
        (conn) => conn.from_node_id !== sourceHandle && conn.to_node_id !== targetHandle
      );

      // Create new connection
      const newConnection = {
        from_node_id: sourceHandle,
        to_node_id: targetHandle,
      };
      updatedConnections.push(newConnection);

      // Create temporary enriched pipeline state with new connection for type propagation
      const tempEnrichedPipelineState = {
        ...enrichedPipelineState,
        connections: updatedConnections,
      };

      // Calculate type propagation (use enriched state for correct allowed_types)
      const initialUpdates: TypeUpdate[] = [
        { moduleId: connection.source, pinId: sourceHandle, newType: validation.suggestedType },
        { moduleId: connection.target, pinId: targetHandle, newType: validation.suggestedType },
      ];

      const allUpdates = calculateTypePropagation(
        tempEnrichedPipelineState,
        effectiveEntryPoints,
        initialUpdates
      );

      // Apply type updates to RAW pipeline state (not enriched - we persist raw data)
      const tempRawPipelineState = {
        ...pipelineState,
        connections: updatedConnections,
      };
      const finalPipelineState = applyTypeUpdates(tempRawPipelineState, allUpdates);

      // Single state update with connections and type changes
      onPipelineStateChange(finalPipelineState);
    },
    [mode, pipelineState, enrichedPipelineState, effectiveEntryPoints, onPipelineStateChange]
  );

  // Handle connection start - remove existing connections from the pin being dragged
  const onConnectStart = useCallback(
    (_event: any, params: { nodeId: string | null; handleId: string | null; handleType: string | null }) => {
      if (mode === 'view' || !pipelineState || !onPipelineStateChange) return;
      if (!params.handleId) return;

      // Check if this pin already has a connection
      const existingConnection = pipelineState.connections.find(
        (conn) => conn.from_node_id === params.handleId || conn.to_node_id === params.handleId
      );

      // If there's an existing connection, remove it immediately
      if (existingConnection) {
        // Track this removed connection for immediate validation during drag
        const connKey = `${existingConnection.from_node_id}-${existingConnection.to_node_id}`;
        removedConnectionsRef.current.add(connKey);

        const updatedConnections = pipelineState.connections.filter(
          (conn) => conn !== existingConnection
        );

        // Update pipeline state without the connection
        // This allows the pin's type to be unconstrained for the new connection
        onPipelineStateChange({
          ...pipelineState,
          connections: updatedConnections,
        });
      }
    },
    [mode, pipelineState, onPipelineStateChange]
  );

  // Handle connection end (including cancelled drags)
  const onConnectEnd = useCallback(() => {
    // Clear removed connections tracker
    removedConnectionsRef.current.clear();
  }, []);

  // Handle edge reconnection with type propagation
  const onReconnect = useCallback(
    (oldEdge: Edge, newConnection: Connection) => {
      // Clear removed connections tracker (drag operation complete)
      removedConnectionsRef.current.clear();

      if (mode === 'view' || !pipelineState || !onPipelineStateChange) return;
      if (!newConnection.source || !newConnection.target || !newConnection.sourceHandle || !newConnection.targetHandle) return;

      const newSourceHandle = newConnection.sourceHandle;
      const newTargetHandle = newConnection.targetHandle;

      // Validate new connection and get suggested type
      const validation = validateConnection(
        pipelineState,
        effectiveEntryPoints,
        newConnection.source,
        newSourceHandle,
        newConnection.target,
        newTargetHandle
      );

      if (!validation.valid || !validation.suggestedType) return;

      // Check if this exact connection already exists (prevent duplicates)
      const isDuplicate = pipelineState.connections.some(
        (conn) => conn.from_node_id === newSourceHandle && conn.to_node_id === newTargetHandle
      );
      if (isDuplicate) return;

      // Remove old connection
      let updatedConnections = pipelineState.connections.filter(
        (conn) => !(conn.from_node_id === oldEdge.sourceHandle && conn.to_node_id === oldEdge.targetHandle)
      );

      // Remove any existing connections that would conflict with new connection (enforce 1-to-1)
      updatedConnections = updatedConnections.filter(
        (conn) => conn.from_node_id !== newSourceHandle && conn.to_node_id !== newTargetHandle
      );

      const newConn = {
        from_node_id: newSourceHandle,
        to_node_id: newTargetHandle,
      };
      updatedConnections.push(newConn);

      // Create temporary pipeline state with new connection for type propagation
      const tempPipelineState = {
        ...pipelineState,
        connections: updatedConnections,
      };

      // Calculate type propagation
      const initialUpdates: TypeUpdate[] = [
        { moduleId: newConnection.source, pinId: newSourceHandle, newType: validation.suggestedType },
        { moduleId: newConnection.target, pinId: newTargetHandle, newType: validation.suggestedType },
      ];

      const allUpdates = calculateTypePropagation(
        tempPipelineState,
        effectiveEntryPoints,
        initialUpdates
      );

      // Apply type updates to create final pipeline state
      const finalPipelineState = applyTypeUpdates(tempPipelineState, allUpdates);

      // Single state update with connections and type changes
      onPipelineStateChange(finalPipelineState);
    },
    [mode, pipelineState, effectiveEntryPoints, onPipelineStateChange]
  );

  // Handle drag over to enable drop
  const onDragOver = useCallback(
    (event: React.DragEvent) => {
      if (mode === 'view') return;
      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';
    },
    [mode]
  );

  // Handle module drop from selector pane
  const onDrop = useCallback(
    (event: React.DragEvent) => {
      if (mode === 'view' || !pipelineState || !onPipelineStateChange || !onVisualStateChange) return;

      event.preventDefault();

      const data = event.dataTransfer.getData('application/reactflow');
      if (!data) return;

      const { moduleId } = JSON.parse(data);
      const template = modules.find((t) => t.id === moduleId);
      if (!template) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      // Create new module instance
      const newModule = createModuleInstance(template);

      // Add module to pipeline state
      const updatedPipelineState: PipelineState = {
        ...pipelineState,
        modules: [...pipelineState.modules, newModule],
      };

      // Add position to visual state
      const updatedVisualState: VisualState = {
        ...visualState,
        [newModule.module_instance_id]: position,
      };

      // Create new node for immediate rendering
      const newNode: Node = {
        id: newModule.module_instance_id,
        type: 'module',
        position,
        data: {
          moduleInstance: newModule,
          template,
        },
        draggable: mode === 'edit',
      };

      // Add to internal nodes state immediately (for smooth rendering)
      setNodes((nds) => [...nds, newNode]);

      // Update parent states (for persistence)
      onPipelineStateChange(updatedPipelineState);
      onVisualStateChange(updatedVisualState);

      onModulePlaced?.();
    },
    [mode, modules, screenToFlowPosition, pipelineState, visualState, onPipelineStateChange, onVisualStateChange, onModulePlaced]
  );

  // Show message if no pipeline state provided
  if (!pipelineState) {
    return (
      <div className="w-full h-full bg-gray-900 flex items-center justify-center">
        <div className="text-gray-400">No pipeline data provided</div>
      </div>
    );
  }

  return (
    <>
      <style>{`
        .selected-edge path {
          stroke-dasharray: 5 5;
          filter: drop-shadow(0 0 8px currentColor);
        }
      `}</style>
      <div
        className="w-full h-full bg-gray-900"
        onDragOver={onDragOver}
        onDrop={onDrop}
      >
        <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onConnectStart={onConnectStart}
        onConnectEnd={onConnectEnd}
        onReconnect={onReconnect}
        isValidConnection={isValidConnection}
        nodesDraggable={mode === 'edit'}
        nodesConnectable={mode === 'edit'}
        elementsSelectable={mode === 'edit'}
        edgesReconnectable={mode === 'edit'}
        reconnectRadius={20}
        panOnDrag={true}
        zoomOnScroll={true}
        minZoom={0.1}
        maxZoom={4}
        fitView
        fitViewOptions={{
          padding: 0.2,
          maxZoom: 1,
        }}
        >
            <Controls />
            <Background variant={BackgroundVariant.Dots} />
        </ReactFlow>
        </div>
    </>
  );
}

export function PipelineGraph(props: PipelineGraphProps) {
  return (
    <ReactFlowProvider>
      <PipelineGraphInner {...props} />
    </ReactFlowProvider>
  );
}
