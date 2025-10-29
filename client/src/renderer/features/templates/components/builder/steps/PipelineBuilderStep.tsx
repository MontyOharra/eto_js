import { useState, useEffect, useCallback, useRef } from 'react';
import { PipelineGraph, PipelineGraphRef } from '../../../../pipelines/components/PipelineGraph';
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
  const pipelineGraphRef = useRef<PipelineGraphRef>(null);

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

  // Handle pipeline state changes from graph (reactive updates via onChange)
  const handlePipelineChange = useCallback((state: PipelineState) => {
    // Entry points already in state from ExtractionFieldsStep, just pass through
    onPipelineStateChange(state);

    // Also extract and save visual state
    // We need to use the ref since onChange doesn't provide visual state
    if (pipelineGraphRef.current) {
      const currentVisualState = pipelineGraphRef.current.getVisualState();
      console.log('[PipelineBuilderStep] Visual state changed:', {
        nodeCount: Object.keys(currentVisualState).length,
        positions: currentVisualState,
      });
      onVisualStateChange(currentVisualState);
    }
  }, [onPipelineStateChange, onVisualStateChange]);

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
          onChange={handlePipelineChange}
          initialPipelineState={pipelineState}
          initialVisualState={visualState}
          viewOnly={false}
          entryPoints={pipelineState.entry_points}
        />
      </div>
    </div>
  );
}
