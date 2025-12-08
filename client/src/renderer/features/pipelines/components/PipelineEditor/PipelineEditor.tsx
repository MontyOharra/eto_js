/**
 * PipelineEditor
 * Unified component combining ModuleSelectorPane and PipelineGraph
 * Handles module fetching and provides a complete pipeline editing experience
 * Always operates in edit mode
 */

import { useState } from "react";
import { useModules, useOutputChannels, ModuleSelectorPane } from "../../../modules";
import { PipelineGraph } from "../PipelineGraph";
import type { PipelineState, VisualState, EntryPoint } from "../../types";

interface PipelineEditorProps {
  pipelineState: PipelineState;
  visualState: VisualState;
  entryPoints?: EntryPoint[]; // Optional: external entry points that override pipelineState.entry_points
  onPipelineStateChange: (state: PipelineState) => void;
  onVisualStateChange: (state: VisualState) => void;
}

export function PipelineEditor({
  pipelineState,
  visualState,
  entryPoints,
  onPipelineStateChange,
  onVisualStateChange,
}: PipelineEditorProps) {
  // Fetch modules and output channels using TanStack Query
  const { data: modules = [], isLoading: modulesLoading } = useModules();
  const { data: outputChannels = [] } = useOutputChannels();

  // Module selection state
  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);

  const handleModuleSelect = (moduleId: string | null) => {
    setSelectedModuleId(moduleId);
  };

  const handleModulePlaced = () => {
    setSelectedModuleId(null);
  };

  // Use external entry points if provided, otherwise use pipelineState.entry_points
  const effectiveEntryPoints = entryPoints ?? pipelineState.entry_points;

  // Show loading state while modules are loading
  if (modulesLoading) {
    return (
      <div className="flex h-full bg-gray-900">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading modules...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* Module Selector Pane */}
      <ModuleSelectorPane
        modules={modules}
        outputChannels={outputChannels}
        selectedModuleId={selectedModuleId}
        onModuleSelect={handleModuleSelect}
      />

      {/* Pipeline Graph - always in edit mode */}
      <div className="flex-1">
        <PipelineGraph
          pipelineState={pipelineState}
          visualState={visualState}
          entryPoints={effectiveEntryPoints}
          mode="edit"
          modules={modules}
          outputChannels={outputChannels}
          selectedModuleId={selectedModuleId}
          onModulePlaced={handleModulePlaced}
          onPipelineStateChange={onPipelineStateChange}
          onVisualStateChange={onVisualStateChange}
        />
      </div>
    </div>
  );
}
