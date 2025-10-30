/**
 * Module Operations Hook
 * Handles adding/removing modules and pins
 */

import { useCallback } from "react";
import { Node } from "@xyflow/react";
import {
  ModuleTemplate,
  ModuleInstance,
} from "../../../shared/types/moduleTypes";
import {
  createModuleInstance,
  addPinToModule,
  removePinFromModule,
  updateModuleConfig,
} from "../utils/moduleFactory";

export interface UseModuleOperationsProps {
  nodes: Node[];
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>;
  viewOnly?: boolean;
}

export interface ModuleOperationsActions {
  addModule: (
    template: ModuleTemplate,
    position: { x: number; y: number }
  ) => string | null;
  deleteModule: (moduleId: string) => void;
  addPin: (
    moduleId: string,
    template: ModuleTemplate,
    direction: "input" | "output",
    groupIndex: number
  ) => void;
  removePin: (moduleId: string, pinId: string) => void;
  updateConfig: (moduleId: string, configKey: string, value: any) => void;
}

export function useModuleOperations({
  nodes,
  setNodes,
  viewOnly = false,
}: UseModuleOperationsProps): ModuleOperationsActions {
  /**
   * Add a new module to the graph
   */
  const addModule = useCallback(
    (
      template: ModuleTemplate,
      position: { x: number; y: number }
    ): string | null => {
      if (viewOnly) return null;

      const moduleInstance = createModuleInstance(template);
      const newNode: Node = {
        id: moduleInstance.module_instance_id,
        type: "module",
        position,
        data: {
          moduleInstance,
          template,
        },
      };

      setNodes((nds) => [...nds, newNode]);
      return moduleInstance.module_instance_id;
    },
    [setNodes, viewOnly]
  );

  /**
   * Delete a module from the graph
   */
  const deleteModule = useCallback(
    (moduleId: string) => {
      if (viewOnly) return;

      setNodes((nds) => nds.filter((n) => n.id !== moduleId));
      // Note: Edges are removed separately via useConnectionManager.deleteConnectionsForModule
    },
    [setNodes, viewOnly]
  );

  /**
   * Add a pin to a module
   */
  const addPin = useCallback(
    (
      moduleId: string,
      template: ModuleTemplate,
      direction: "input" | "output",
      groupIndex: number
    ) => {
      if (viewOnly) return;

      setNodes((nds) =>
        nds.map((node) => {
          if (node.id !== moduleId || !node.data?.moduleInstance) return node;

          const moduleInstance = node.data.moduleInstance as ModuleInstance;
          const updatedModule = addPinToModule(
            moduleInstance,
            template,
            direction,
            groupIndex
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
    },
    [setNodes, viewOnly]
  );

  /**
   * Remove a pin from a module
   */
  const removePin = useCallback(
    (moduleId: string, pinId: string) => {
      if (viewOnly) return;

      setNodes((nds) =>
        nds.map((node) => {
          if (node.id !== moduleId || !node.data?.moduleInstance) return node;

          const moduleInstance = node.data.moduleInstance as ModuleInstance;
          const updatedModule = removePinFromModule(moduleInstance, pinId);

          return {
            ...node,
            data: {
              ...node.data,
              moduleInstance: updatedModule,
            },
          };
        })
      );
      // Note: Edges are removed separately via useConnectionManager.deleteConnectionsForPin
    },
    [setNodes, viewOnly]
  );

  /**
   * Update module configuration
   */
  const updateConfig = useCallback(
    (moduleId: string, configKey: string, value: any) => {
      if (viewOnly) return;

      setNodes((nds) =>
        nds.map((node) => {
          if (node.id !== moduleId || !node.data?.moduleInstance) return node;

          const moduleInstance = node.data.moduleInstance as ModuleInstance;
          const updatedModule = updateModuleConfig(
            moduleInstance,
            configKey,
            value
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
    },
    [setNodes, viewOnly]
  );

  return {
    addModule,
    deleteModule,
    addPin,
    removePin,
    updateConfig,
  };
}
