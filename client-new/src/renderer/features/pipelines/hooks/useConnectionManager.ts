/**
 * Connection Manager Hook
 * Handles connection creation, deletion, and type propagation
 */

import { useCallback } from 'react';
import { Node, Edge } from '@xyflow/react';
import { ModuleInstance, NodePin } from '../../../types/moduleTypes';
import {
  validateConnection,
  calculateTypePropagation,
  applyTypeUpdates,
  findPin,
} from '../utils/typeSystem';
import {
  createStyledEdge,
  updateEdgeColors,
  findConnectedEdges,
  removePinEdges,
} from '../utils/edgeUtils';

export interface UseConnectionManagerProps {
  nodes: Node[];
  edges: Edge[];
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>;
  setEdges: React.Dispatch<React.SetStateAction<Edge[]>>;
  viewOnly?: boolean;
}

export interface ConnectionManagerActions {
  createConnection: (
    sourceModuleId: string,
    sourcePinId: string,
    targetModuleId: string,
    targetPinId: string
  ) => boolean;
  deleteConnection: (edgeId: string) => void;
  deleteConnectionsForPin: (moduleId: string, pinId: string) => void;
  deleteConnectionsForModule: (moduleId: string) => void;
}

export function useConnectionManager({
  nodes,
  edges,
  setNodes,
  setEdges,
  viewOnly = false,
}: UseConnectionManagerProps): ConnectionManagerActions {
  /**
   * Create a connection between two pins with type propagation
   */
  const createConnection = useCallback(
    (
      sourceModuleId: string,
      sourcePinId: string,
      targetModuleId: string,
      targetPinId: string
    ): boolean => {
      if (viewOnly) return false;

      // Get both nodes and their pins
      const sourceNode = nodes.find((n) => n.id === sourceModuleId);
      const targetNode = nodes.find((n) => n.id === targetModuleId);

      if (!sourceNode?.data?.moduleInstance || !targetNode?.data?.moduleInstance) {
        console.error('Could not find source or target module');
        return false;
      }

      const sourceModule = sourceNode.data.moduleInstance as ModuleInstance;
      const targetModule = targetNode.data.moduleInstance as ModuleInstance;

      const sourcePin = findPin(sourceModule, sourcePinId);
      const targetPin = findPin(targetModule, targetPinId);

      if (!sourcePin || !targetPin) {
        console.error('Could not find source or target pin');
        return false;
      }

      // Validate connection
      const validation = validateConnection(sourcePin, targetPin);
      if (!validation.valid || !validation.suggestedType) {
        console.warn('Cannot connect: No shared types between nodes');
        return false;
      }

      const targetType = validation.suggestedType;

      // Remove any existing connection to the target pin (inputs can only have one connection)
      setEdges((eds) => removePinEdges(eds, targetModuleId, targetPinId));

      // Calculate type propagation
      const initialUpdates = [
        { moduleId: sourceModuleId, pinId: sourcePinId, newType: targetType },
        { moduleId: targetModuleId, pinId: targetPinId, newType: targetType },
      ];

      const allUpdates = calculateTypePropagation(nodes, edges, initialUpdates);

      // Apply type updates to nodes
      const updatedNodes = applyTypeUpdates(nodes, allUpdates);
      setNodes(updatedNodes);

      // Create the edge
      const newEdge = createStyledEdge(
        sourceModuleId,
        sourcePinId,
        targetModuleId,
        targetPinId,
        targetType
      );

      setEdges((eds) => [...eds, newEdge]);

      // Update all edge colors after type propagation
      setTimeout(() => {
        setEdges((eds) => updateEdgeColors(updatedNodes, eds));
      }, 0);

      return true;
    },
    [nodes, edges, setNodes, setEdges, viewOnly]
  );

  /**
   * Delete a connection by edge ID
   */
  const deleteConnection = useCallback(
    (edgeId: string) => {
      if (viewOnly) return;

      setEdges((eds) => eds.filter((e) => e.id !== edgeId));
    },
    [setEdges, viewOnly]
  );

  /**
   * Delete all connections for a specific pin
   */
  const deleteConnectionsForPin = useCallback(
    (moduleId: string, pinId: string) => {
      if (viewOnly) return;

      setEdges((eds) => removePinEdges(eds, moduleId, pinId));
    },
    [setEdges, viewOnly]
  );

  /**
   * Delete all connections for a module
   */
  const deleteConnectionsForModule = useCallback(
    (moduleId: string) => {
      if (viewOnly) return;

      setEdges((eds) => eds.filter((e) => e.source !== moduleId && e.target !== moduleId));
    },
    [setEdges, viewOnly]
  );

  return {
    createConnection,
    deleteConnection,
    deleteConnectionsForPin,
    deleteConnectionsForModule,
  };
}
