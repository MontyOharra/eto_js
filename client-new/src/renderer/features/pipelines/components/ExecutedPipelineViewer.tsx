/**
 * ExecutedPipelineViewer
 * Read-only pipeline visualization with execution data overlay
 * Uses dedicated ExecutedPipelineGraph component
 */

import { useEffect, useState } from 'react';
import { useMockPipelinesApi } from '../hooks/useMockPipelinesApi';
import { ExecutedPipelineGraph } from './ExecutedPipelineGraph';
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

export function ExecutedPipelineViewer({ pipelineDefinitionId, executionData, extractedData }: ExecutedPipelineViewerProps) {
  const { getPipeline, isLoading, error } = useMockPipelinesApi();
  const [pipelineState, setPipelineState] = useState<PipelineState | null>(null);
  const [visualState, setVisualState] = useState<VisualState | null>(null);
  const [moduleTemplates, setModuleTemplates] = useState<ModuleTemplate[]>([]);
  const [failedModuleIds, setFailedModuleIds] = useState<string[]>([]);
  const [executionValues, setExecutionValues] = useState<Map<string, { value: any; type: string; name: string }>>(new Map());

  // Fetch pipeline definition
  useEffect(() => {
    const loadPipeline = async () => {
      try {
        console.log('[ExecutedPipelineViewer] Fetching pipeline:', pipelineDefinitionId);
        const pipeline = await getPipeline(pipelineDefinitionId);
        console.log('[ExecutedPipelineViewer] Pipeline loaded:', pipeline);

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
            const fieldValue = extractedData[ep.field_reference];
            if (fieldValue !== undefined) {
              executedNodeIds.add(ep.id);
              // Determine type from the value
              let valueType = typeof fieldValue;
              if (valueType === 'object' && fieldValue instanceof Date) {
                valueType = 'datetime';
              } else if (valueType === 'number') {
                valueType = Number.isInteger(fieldValue) ? 'int' : 'float';
              }

              executionValues.set(ep.id, {
                value: fieldValue,
                type: valueType,
                name: ep.label,
              });
            }
          });
        }

        console.log('[ExecutedPipelineViewer] Executed node IDs:', Array.from(executedNodeIds));
        console.log('[ExecutedPipelineViewer] Failed modules:', failedModules);
        console.log('[ExecutedPipelineViewer] Execution values:', Array.from(executionValues.entries()));
        setFailedModuleIds(failedModules);
        setExecutionValues(executionValues);

        // Create module templates from module IDs
        // Module ID format: "string_uppercase:1.0.0"
        // Template needs: id="string_uppercase", version="1.0.0"
        const templates: ModuleTemplate[] = [];
        const seenModuleRefs = new Set<string>();

        apiState.modules.forEach((module: any) => {
          if (!seenModuleRefs.has(module.module_id)) {
            seenModuleRefs.add(module.module_id);

            const [templateId, version] = module.module_id.split(':');
            templates.push(
              createMinimalModuleTemplate(
                templateId,              // Just the ID part (e.g., "string_uppercase")
                version || '1.0.0',      // Version (e.g., "1.0.0")
                getModuleName(templateId),
                getModuleColor(templateId)
              )
            );
          }
        });

        console.log('[ExecutedPipelineViewer] Created module templates:', templates);
        setModuleTemplates(templates);

        // Convert entry points
        const entryPoints: EntryPoint[] = apiState.entry_points.map((ep: any) => {
          // Entry points are always "executed" - they provide the initial data
          executedNodeIds.add(ep.id);

          return {
            node_id: ep.id,
            name: ep.label,
            type: 'str', // Default type for entry points
          };
        });

        // Convert modules to ModuleInstance format
        const modules: ModuleInstance[] = apiState.modules.map((module: any) => {
          const converted = {
            module_instance_id: module.instance_id,
            module_ref: module.module_id,
            module_kind: module.module_id.includes('action_') ? 'action' : 'transform',
            config: module.config || {},
            inputs: module.inputs.map((input: any, idx: number) => ({
              node_id: input.node_id,
              direction: 'in' as const,
              type: input.type[0] || 'str',
              name: input.name,
              label: input.name,
              position_index: idx,
              group_index: 0,
              allowed_types: input.type,
            })),
            outputs: module.outputs.map((output: any, idx: number) => ({
              node_id: output.node_id,
              direction: 'out' as const,
              type: output.type[0] || 'str',
              name: output.name,
              label: output.name,
              position_index: idx,
              group_index: 0,
              allowed_types: output.type,
            })),
          };
          console.log('[ExecutedPipelineViewer] Converted module:', module.instance_id, converted);
          return converted;
        });

        // Convert connections - only show connections where both endpoints have execution data
        const connections = apiState.connections
          .filter((conn: any) => {
            const sourceExists = executedNodeIds.has(conn.source_handle_id);
            const targetExists = executedNodeIds.has(conn.target_handle_id);
            const shouldShow = sourceExists && targetExists;

            if (!shouldShow) {
              console.log('[ExecutedPipelineViewer] Hiding connection:', conn.source_handle_id, '→', conn.target_handle_id,
                `(source: ${sourceExists}, target: ${targetExists})`);
            }

            return shouldShow;
          })
          .map((conn: any) => ({
            from_node_id: conn.source_handle_id,
            to_node_id: conn.target_handle_id,
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
        moduleTemplates={moduleTemplates}
        pipelineState={pipelineState}
        visualState={visualState}
        failedModuleIds={failedModuleIds}
        executionValues={executionValues}
      />
    </div>
  );
}
