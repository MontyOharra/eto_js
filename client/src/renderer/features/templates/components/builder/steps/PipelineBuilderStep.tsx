import { useState, useEffect, useCallback } from 'react';
import { PipelineGraph } from '../../../../pipelines/components/PipelineGraph';
import { ModuleSelectorPane } from '../../../../pipelines/components/ModuleSelectorPane';
import { useModulesApi } from '../../../../../features/modules/hooks';
import type { ModuleTemplate } from '../../../../../types/moduleTypes';
import type { PipelineState, VisualState } from '../../../../../types/pipelineTypes';

interface PipelineBuilderStepProps {
  pipelineState: PipelineState;
  visualState: VisualState;
  onPipelineStateChange: (state: PipelineState) => void;
  onVisualStateChange: (state: VisualState) => void;
}

export function PipelineBuilderStep({
  pipelineState,
  visualState,
  onPipelineStateChange,
  onVisualStateChange,
}: PipelineBuilderStepProps) {
  const { getModules, isLoading: isLoadingModules } = useModulesApi();
  const [modules, setModules] = useState<ModuleTemplate[]>([]);
  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);

  // Load modules from API
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
  }, [getModules]);

  // Handle pipeline state changes from graph (modules, connections)
  const handlePipelineChange = useCallback((state: PipelineState) => {
    // Entry points already in state from ExtractionFieldsStep, just pass through
    onPipelineStateChange(state);
  }, [onPipelineStateChange]);

  // Handle visual state changes (node positions on drag end)
  const handleVisualChange = useCallback((visualState: VisualState) => {
    console.log('[PipelineBuilderStep] Visual state changed:', {
      nodeCount: Object.keys(visualState).length,
      positions: visualState,
    });
    onVisualStateChange(visualState);
  }, [onVisualStateChange]);

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
          moduleTemplates={modules}
          selectedModuleId={selectedModuleId}
          onModulePlaced={handleModulePlaced}
          onChange={handlePipelineChange}
          onVisualChange={handleVisualChange}
          initialPipelineState={pipelineState}
          initialVisualState={visualState}
          viewOnly={false}
          entryPoints={pipelineState.entry_points}
        />
      </div>
    </div>
  );
}
