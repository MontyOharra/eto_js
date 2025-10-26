/**
 * ExecutedPipelineViewer
 * Read-only pipeline visualization with execution data overlay
 * Uses dedicated ExecutedPipelineGraph component
 */

import { useEffect, useState, forwardRef, useImperativeHandle, useRef } from 'react';
import { usePipelinesApi } from '../hooks/usePipelinesApi';
import { useModulesApi } from '../../modules/hooks/useModulesApi';
import { ExecutedPipelineGraph, ExecutedPipelineGraphRef } from './ExecutedPipelineGraph';
import { applyLayeredLayout } from '../utils/layeredLayout';
import type { PipelineState, VisualState, ModuleTemplate } from '../../../types/pipelineTypes';
import type { EtoPipelineExecutionStep } from '../../eto/types';

export interface ExecutedPipelineViewerProps {
  pipelineDefinitionId: number;
  executionData?: {
    steps: EtoPipelineExecutionStep[];
    executed_actions?: Array<{
      action_module_name: string;
      inputs: Record<string, any>;
    }>;
  };
  extractedData?: Record<string, any>;
}

export interface ExecutedPipelineViewerRef {
  fitView: () => void;
}

// Minimal module templates for executed pipeline viewer
// In production, these would come from GET /modules endpoint
const createMinimalModuleTemplate = (moduleId: string, version: string, moduleName: string, color: string): ModuleTemplate => {
  return {
    id: moduleId,
    version,
    title: moduleName,
    description: '',
    kind: 'transform',
    color,
    meta: {
      io_shape: {
        inputs: { nodes: [] },
        outputs: { nodes: [] },
        type_params: {},
      },
    },
    config_schema: {},
  };
};

// Get module name from module_id
const getModuleName = (moduleId: string): string => {
  return moduleId
    .split(':')[0]
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

// Get module color by kind
const getModuleColor = (moduleId: string): string => {
  if (moduleId.includes('action_')) return '#10B981'; // Green for actions
  if (moduleId.includes('logic_')) return '#F59E0B'; // Amber for logic
  return '#3B82F6'; // Blue for transforms
};

export const ExecutedPipelineViewer = forwardRef<ExecutedPipelineViewerRef, ExecutedPipelineViewerProps>(({ pipelineDefinitionId, executionData, extractedData }, ref) => {
  const { getPipeline, isLoading, error } = usePipelinesApi();
  const { getModules } = useModulesApi();
  const [pipelineState, setPipelineState] = useState<PipelineState | null>(null);
  const [visualState, setVisualState] = useState<VisualState | null>(null);
  const [moduleTemplates, setModuleTemplates] = useState<ModuleTemplate[]>([]);
  const [failedModuleIds, setFailedModuleIds] = useState<string[]>([]);
  const [executionValues, setExecutionValues] = useState<Map<string, { value: any; type: string; name: string }>>(new Map());
  const graphRef = useRef<ExecutedPipelineGraphRef>(null);

  // Expose fitView to parent component
  useImperativeHandle(ref, () => ({
    fitView: () => {
      graphRef.current?.fitView();
    },
  }), []);

  // Fetch pipeline definition and module templates
  useEffect(() => {
    const loadPipeline = async () => {
      try {
        console.log('[ExecutedPipelineViewer] Fetching pipeline:', pipelineDefinitionId);
        const [pipeline, modulesResponse] = await Promise.all([
          getPipeline(pipelineDefinitionId),
          getModules()
        ]);
        console.log('[ExecutedPipelineViewer] Pipeline loaded:', pipeline);
        console.log('[ExecutedPipelineViewer] Modules loaded:', modulesResponse);

        const allModules = modulesResponse.modules;

        // Extract all node IDs that have execution data and build value map
        const executedNodeIds = new Set<string>();
        const failedModules: string[] = [];
        const executionValues = new Map<string, { value: any; type: string; name: string }>();

        if (executionData?.steps) {
          executionData.steps.forEach(step => {
            // Collect all input node IDs and values
            if (step.inputs) {
              Object.entries(step.inputs).forEach(([nodeId, data]) => {
                executedNodeIds.add(nodeId);
                executionValues.set(nodeId, {
                  value: data.value,
                  type: data.type,
                  name: data.name,
                });
              });
            }

            // Collect all output node IDs and values
            if (step.outputs) {
              Object.entries(step.outputs).forEach(([nodeId, data]) => {
                executedNodeIds.add(nodeId);
                executionValues.set(nodeId, {
                  value: data.value,
                  type: data.type,
                  name: data.name,
                });
              });
            }

            // Track failed modules
            if (step.error) {
              failedModules.push(step.module_instance_id);
            }
          });
        }

        // Convert API format to PipelineGraph format
        const apiState = pipeline.pipeline_state as any;
        const apiVisual = pipeline.visual_state as any;

        // Add entry point values from extracted data
        if (extractedData && apiState.entry_points) {
          apiState.entry_points.forEach((ep: any) => {
            // extractedData is keyed by entry point name
            const fieldValue = extractedData[ep.name];
            if (fieldValue !== undefined) {
              executedNodeIds.add(ep.node_id);
              // Determine pipeline type from the value (map JS types to pipeline types)
              let valueType: string;
              if (fieldValue instanceof Date) {
                valueType = 'datetime';
              } else if (typeof fieldValue === 'number') {
                valueType = Number.isInteger(fieldValue) ? 'int' : 'float';
              } else if (typeof fieldValue === 'boolean') {
                valueType = 'bool';
              } else if (typeof fieldValue === 'string') {
                valueType = 'str';
              } else {
                valueType = 'str'; // Default to string for objects/unknown
              }

              executionValues.set(ep.node_id, {
                value: fieldValue,
                type: valueType,
                name: ep.name,
              });
            }
          });
        }

        console.log('[ExecutedPipelineViewer] Executed node IDs:', Array.from(executedNodeIds));
        console.log('[ExecutedPipelineViewer] Failed modules:', failedModules);
        console.log('[ExecutedPipelineViewer] Execution values:', Array.from(executionValues.entries()));
        setFailedModuleIds(failedModules);
        setExecutionValues(executionValues);

        // Map real module templates from fetched modules
        const templates: ModuleTemplate[] = [];
        const seenModuleRefs = new Set<string>();

        apiState.modules.forEach((module: any) => {
          if (!seenModuleRefs.has(module.module_ref)) {
            seenModuleRefs.add(module.module_ref);

            const [moduleId, version] = module.module_ref.split(':');

            // Find the actual module template from fetched modules
            const actualModule = allModules.find((m: ModuleTemplate) => m.id === moduleId);

            if (actualModule) {
              // Use the real module template
              templates.push(actualModule);
            } else {
              // Fallback to minimal template if module not found
              console.warn(`[ExecutedPipelineViewer] Module ${moduleId} not found in modules list, using fallback`);
              templates.push(
                createMinimalModuleTemplate(
                  moduleId,
                  version || '1.0.0',
                  getModuleName(moduleId),
                  getModuleColor(moduleId)
                )
              );
            }
          }
        });

        console.log('[ExecutedPipelineViewer] Module templates:', templates);
        setModuleTemplates(templates);

        // Convert entry points
        const entryPoints: EntryPoint[] = apiState.entry_points.map((ep: any) => {
          // Entry points are always "executed" - they provide the initial data
          executedNodeIds.add(ep.node_id);

          return {
            node_id: ep.node_id,
            name: ep.name,
            type: 'str', // Default type for entry points
          };
        });

        // Convert modules to ModuleInstance format
        const modules: ModuleInstance[] = apiState.modules.map((module: any) => {
          const converted = {
            module_instance_id: module.module_instance_id,
            module_ref: module.module_ref,
            module_kind: module.module_kind,
            config: module.config || {},
            inputs: module.inputs.map((input: any, idx: number) => ({
              node_id: input.node_id,
              direction: 'in' as const,
              type: input.type || 'str',
              name: input.name,
              label: input.name,
              position_index: input.position_index ?? idx,
              group_index: input.group_index ?? 0,
              allowed_types: Array.isArray(input.type) ? input.type : [input.type],
            })),
            outputs: module.outputs.map((output: any, idx: number) => ({
              node_id: output.node_id,
              direction: 'out' as const,
              type: output.type || 'str',
              name: output.name,
              label: output.name,
              position_index: output.position_index ?? idx,
              group_index: output.group_index ?? 0,
              allowed_types: Array.isArray(output.type) ? output.type : [output.type],
            })),
          };
          console.log('[ExecutedPipelineViewer] Converted module:', module.module_instance_id, converted);
          return converted;
        });

        // Convert connections - only show connections where both endpoints have execution data
        const connections = apiState.connections
          .filter((conn: any) => {
            const sourceExists = executedNodeIds.has(conn.from_node_id);
            const targetExists = executedNodeIds.has(conn.to_node_id);
            const shouldShow = sourceExists && targetExists;

            if (!shouldShow) {
              console.log('[ExecutedPipelineViewer] Hiding connection:', conn.from_node_id, '→', conn.to_node_id,
                `(source: ${sourceExists}, target: ${targetExists})`);
            }

            return shouldShow;
          })
          .map((conn: any) => ({
            from_node_id: conn.from_node_id,
            to_node_id: conn.to_node_id,
          }));

        console.log('[ExecutedPipelineViewer] Showing', connections.length, 'of', apiState.connections.length, 'connections');

        const convertedState: PipelineState = {
          entry_points: entryPoints,
          modules,
          connections,
        };

        // Apply layered layout (left-to-right by execution order)
        // Must be done AFTER converting to PipelineState format
        const autoPositions = applyLayeredLayout(
          entryPoints,
          modules,
          connections
        );

        const convertedVisual: VisualState = {
          modules: {},
          entryPoints: {},
        };

        // Apply auto-layout positions
        // Visual state keys should match the node_id/instance_id, NOT the React Flow node ID
        // React Flow nodes for entry points have 'entry-' prefix, but visual state uses raw node_id
        console.log('[ExecutedPipelineViewer] Auto-layout positions:', autoPositions);
        Object.keys(autoPositions).forEach(nodeId => {
          const pos = autoPositions[nodeId];
          const isEntryPoint = apiState.entry_points.some((ep: any) => ep.id === nodeId);

          console.log('[ExecutedPipelineViewer] Positioning node:', nodeId, 'isEntryPoint:', isEntryPoint, 'pos:', pos);

          if (isEntryPoint) {
            // Entry point visual state key = entry point's node_id (same as API id)
            convertedVisual.entryPoints![nodeId] = pos;
          } else {
            // Module visual state key = module's instance_id
            convertedVisual.modules[nodeId] = pos;
          }
        });

        console.log('[ExecutedPipelineViewer] Final visual state:', convertedVisual);

        console.log('[ExecutedPipelineViewer] Converted state:', convertedState);
        console.log('[ExecutedPipelineViewer] Auto-layout positions:', convertedVisual);

        setPipelineState(convertedState);
        setVisualState(convertedVisual);
      } catch (err) {
        console.error('[ExecutedPipelineViewer] Failed to load pipeline:', err);
      }
    };

    loadPipeline();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pipelineDefinitionId]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-900">
        <div className="text-blue-400">Loading pipeline...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-900">
        <div className="text-red-400">Error: {error}</div>
      </div>
    );
  }

  if (!pipelineState || !visualState) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-900">
        <div className="text-gray-400">No pipeline data available</div>
      </div>
    );
  }

  return (
    <div className="w-full h-full">
      <ExecutedPipelineGraph
        ref={graphRef}
        moduleTemplates={moduleTemplates}
        pipelineState={pipelineState}
        visualState={visualState}
        failedModuleIds={failedModuleIds}
        executionValues={executionValues}
      />
    </div>
  );
});
