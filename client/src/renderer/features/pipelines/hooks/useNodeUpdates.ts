/**
 * Node Updates Hook
 * Handles updates to individual pins (type changes, name changes)
 */

import { useCallback } from "react";
import { Node, Edge } from "@xyflow/react";
import { ModuleInstance, NodePin } from "../types";
import {
  calculateTypePropagation,
  applyTypeUpdates,
  findPin,
  getPinsWithTypeVar,
} from "../utils/typeSystem";
import { updateEdgeColors } from "../utils/edgeUtils";
import { updatePinInModule } from "../utils/moduleFactory";

export interface UseNodeUpdatesProps {
  nodes: Node[];
  edges: Edge[];
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>;
  setEdges: React.Dispatch<React.SetStateAction<Edge[]>>;
  viewOnly?: boolean;
}

export interface NodeUpdatesActions {
  updateNodeType: (moduleId: string, pinId: string, newType: string) => void;
  updateNodeName: (moduleId: string, pinId: string, newName: string) => void;
  updateNode: (
    moduleId: string,
    pinId: string,
    updates: Partial<NodePin>
  ) => void;
}

export function useNodeUpdates({
  nodes,
  edges,
  setNodes,
  setEdges,
  viewOnly = false,
}: UseNodeUpdatesProps): NodeUpdatesActions {
  /**
   * Update a pin's type with type propagation through graph
   */
  const updateNodeType = useCallback(
    (moduleId: string, pinId: string, newType: string) => {
      if (viewOnly) return;

      const module = nodes.find((n) => n.id === moduleId);
      if (!module?.data?.moduleInstance) return;

      const moduleInstance = module.data.moduleInstance as ModuleInstance;
      const pin = findPin(moduleInstance, pinId);
      if (!pin) return;

      // Build initial updates list
      const initialUpdates = [{ moduleId, pinId, newType }];

      // If pin has typevar, add all typevar siblings as initial updates
      if (pin.type_var) {
        const typeVarPins = getPinsWithTypeVar(moduleInstance, pin.type_var);
        typeVarPins.forEach((p) => {
          if (p.node_id !== pinId) {
            initialUpdates.push({ moduleId, pinId: p.node_id, newType });
          }
        });
      }

      // Calculate all cascading updates
      const allUpdates = calculateTypePropagation(nodes, edges, initialUpdates);

      // Apply updates
      const updatedNodes = applyTypeUpdates(nodes, allUpdates);
      setNodes(updatedNodes);

      // Update edge colors
      setTimeout(() => {
        setEdges((eds) => updateEdgeColors(updatedNodes, eds));
      }, 0);
    },
    [nodes, edges, setNodes, setEdges, viewOnly]
  );

  /**
   * Update a pin's name
   */
  const updateNodeName = useCallback(
    (moduleId: string, pinId: string, newName: string) => {
      if (viewOnly) return;

      setNodes((nds) =>
        nds.map((node) => {
          if (node.id !== moduleId || !node.data?.moduleInstance) return node;

          const moduleInstance = node.data.moduleInstance as ModuleInstance;
          const updatedModule = updatePinInModule(moduleInstance, pinId, {
            name: newName,
          });

          return {
            ...node,
            data: {
              ...node.data,
              moduleInstance: updatedModule,
            },
          };
        })
      );
    },
    [setNodes, viewOnly]
  );

  /**
   * Generic update for any pin properties
   * If updates include type, uses type propagation
   */
  const updateNode = useCallback(
    (moduleId: string, pinId: string, updates: Partial<NodePin>) => {
      if (viewOnly) return;

      // If this is a type change, use type-aware update
      if (updates.type) {
        updateNodeType(moduleId, pinId, updates.type);

        // If there are other updates besides type, apply them separately
        const otherUpdates = { ...updates };
        delete otherUpdates.type;

        if (Object.keys(otherUpdates).length > 0) {
          setNodes((nds) =>
            nds.map((node) => {
              if (node.id !== moduleId || !node.data?.moduleInstance)
                return node;

              const moduleInstance = node.data.moduleInstance as ModuleInstance;
              const updatedModule = updatePinInModule(
                moduleInstance,
                pinId,
                otherUpdates
              );

              return {
                ...node,
                data: {
                  ...node.data,
                  moduleInstance: updatedModule,
                },
              };
            })
          );
        }
      } else {
        // Non-type update, just apply directly
        setNodes((nds) =>
          nds.map((node) => {
            if (node.id !== moduleId || !node.data?.moduleInstance) return node;

            const moduleInstance = node.data.moduleInstance as ModuleInstance;
            const updatedModule = updatePinInModule(
              moduleInstance,
              pinId,
              updates
            );

            return {
              ...node,
              data: {
                ...node.data,
                moduleInstance: updatedModule,
              },
            };
          })
        );
      }
    },
    [setNodes, updateNodeType, viewOnly]
  );

  return {
    updateNodeType,
    updateNodeName,
    updateNode,
  };
}
