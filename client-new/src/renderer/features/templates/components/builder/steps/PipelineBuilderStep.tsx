import { useState, useEffect, useMemo, useRef } from 'react';
import { PipelineState, VisualState, ExtractionField } from '../../../types';
import { PipelineGraph, PipelineGraphRef } from '../../../../pipelines/components/PipelineGraph';
import { ModuleSelectorPane } from '../../../../pipelines/components/ModuleSelectorPane';
import { useMockModulesApi } from '../../../../../features/modules/hooks';
import type { ModuleTemplate } from '../../../../../types/moduleTypes';
import type { EntryPoint } from '../../../../../types/pipelineTypes';

interface PipelineBuilderStepProps {
  extractionFields: ExtractionField[];
  pipelineState: PipelineState;
  visualState: VisualState;
  onPipelineStateChange: (state: PipelineState) => void;
  onVisualStateChange: (state: VisualState) => void;
}

export function PipelineBuilderStep({
  extractionFields,
  pipelineState,
  visualState,
  onPipelineStateChange,
  onVisualStateChange,
}: PipelineBuilderStepProps) {
  const { getModules, isLoading: isLoadingModules } = useMockModulesApi();
  const [modules, setModules] = useState<ModuleTemplate[]>([]);
  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);
  const pipelineGraphRef = useRef<PipelineGraphRef>(null);

  // Convert extraction fields to entry points
  const entryPoints: EntryPoint[] = useMemo(() => {
    return extractionFields.map((field) => ({
      node_id: `entry_${field.field_id}`,
      name: field.label,
      type: 'str', // Extraction fields always output strings
    }));
  }, [extractionFields]);

  // Load modules from mock API
  useEffect(() => {
    async function loadModules() {
      try {
        const response = await getModules();
        setModules(response.modules);
      } catch (error) {
        console.error('Failed to load modules:', error);
        setModules([]);
      }
    }
    loadModules();
  }, []);

  // Sync graph state changes back to parent
  useEffect(() => {
    if (!pipelineGraphRef.current) return;

    // Set up a periodic sync or use a callback mechanism
    const syncState = () => {
      if (!pipelineGraphRef.current) return;

      try {
        const currentPipelineState = pipelineGraphRef.current.getPipelineState();
        const currentVisualState = pipelineGraphRef.current.getVisualState();

        // Include entry points in the pipeline state
        const stateWithEntryPoints = {
          ...currentPipelineState,
          entry_points: entryPoints,
        };

        // Update parent state
        onPipelineStateChange(stateWithEntryPoints);
        onVisualStateChange(currentVisualState);
      } catch (error) {
        // Graph might not be ready yet
        console.debug('Graph state not ready for sync');
      }
    };

    // Sync on a timer (this could be optimized with callbacks from the graph)
    const interval = setInterval(syncState, 1000);
    return () => clearInterval(interval);
  }, [onPipelineStateChange, onVisualStateChange, entryPoints]);

  const handleModuleSelect = (moduleId: string | null) => {
    setSelectedModuleId(moduleId);
  };

  const handleModulePlaced = () => {
    setSelectedModuleId(null);
  };

  if (isLoadingModules) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-white text-lg mb-2">Loading modules...</div>
          <div className="text-gray-400 text-sm">Please wait</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex overflow-hidden">
      {/* Module Selector Pane */}
      <ModuleSelectorPane
        modules={modules}
        selectedModuleId={selectedModuleId}
        onModuleSelect={handleModuleSelect}
      />

      {/* Pipeline Graph */}
      <div className="flex-1">
        <PipelineGraph
          ref={pipelineGraphRef}
          moduleTemplates={modules}
          selectedModuleId={selectedModuleId}
          onModulePlaced={handleModulePlaced}
          viewOnly={false}
          entryPoints={entryPoints}
        />
      </div>
    </div>
  );
}
