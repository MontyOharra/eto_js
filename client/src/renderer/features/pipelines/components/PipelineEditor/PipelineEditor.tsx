/**
 * PipelineEditor
 * Unified component combining ModuleSelectorPane and PipelineGraph
 * Handles module fetching and provides a complete pipeline editing experience
 * Always operates in edit mode
 */

import { useState } from "react";
import { useModules, ModuleSelectorPane } from "../../../modules";
import { PipelineGraph } from "../PipelineGraph";
import type { PipelineState, VisualState } from "../../types";

interface PipelineEditorProps {
  pipelineState: PipelineState;
  visualState: VisualState;
  onPipelineStateChange: (state: PipelineState) => void;
  onVisualStateChange: (state: VisualState) => void;
}

export function PipelineEditor({
  pipelineState,
  visualState,
  onPipelineStateChange,
  onVisualStateChange,
}: PipelineEditorProps) {
  // Fetch modules using TanStack Query
  const { data: modules = [], isLoading: modulesLoading } = useModules();

  // Module selection state
  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);

  const handleModuleSelect = (moduleId: string | null) => {
    setSelectedModuleId(moduleId);
  };

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
        selectedModuleId={selectedModuleId}
        onModuleSelect={handleModuleSelect}
      />

      {/* Pipeline Graph - always in edit mode */}
      <div className="flex-1">
        <PipelineGraph
          pipelineState={pipelineState}
          visualState={visualState}
          mode="edit"
          onPipelineStateChange={onPipelineStateChange}
          onVisualStateChange={onVisualStateChange}
        />
      </div>
    </div>
  );
}
