import { useState, useCallback } from "react";
import { PipelineGraph } from "../../../../pipelines/components/PipelineGraph-old/PipelineGraph";
import { ModuleSelectorPane } from "../../../../pipelines/components/ModuleSelectorPane";
import type { ModuleTemplate } from "../../../../modules/types";
import type { PipelineState, VisualState } from "../../../../pipelines/types";

interface PipelineBuilderStepProps {
  pipelineState: PipelineState;
  visualState: VisualState;
  moduleTemplates: ModuleTemplate[]; // Passed from parent instead of loading here
  onPipelineStateChange: (state: PipelineState) => void;
  onVisualStateChange: (state: VisualState) => void;
}

export function PipelineBuilderStep({
  pipelineState,
  visualState,
  moduleTemplates,
  onPipelineStateChange,
  onVisualStateChange,
}: PipelineBuilderStepProps) {
  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);

  // Handle pipeline state changes from graph (modules, connections)
  const handlePipelineChange = useCallback(
    (state: PipelineState) => {
      // Entry points already in state from ExtractionFieldsStep, just pass through
      onPipelineStateChange(state);
    },
    [onPipelineStateChange]
  );

  // Handle visual state changes (node positions on drag end)
  const handleVisualChange = useCallback(
    (visualState: VisualState) => {
      console.log("[PipelineBuilderStep] Visual state changed:", {
        nodeCount: Object.keys(visualState).length,
        positions: visualState,
      });
      onVisualStateChange(visualState);
    },
    [onVisualStateChange]
  );

  const handleModuleSelect = (moduleId: string | null) => {
    setSelectedModuleId(moduleId);
  };

  const handleModulePlaced = () => {
    setSelectedModuleId(null);
  };

  return (
    <div className="h-full w-full flex overflow-hidden">
      {/* Module Selector Pane */}
      <ModuleSelectorPane
        modules={moduleTemplates}
        selectedModuleId={selectedModuleId}
        onModuleSelect={handleModuleSelect}
      />

      {/* Pipeline Graph */}
      <div className="flex-1">
        <PipelineGraph
          moduleTemplates={moduleTemplates}
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
