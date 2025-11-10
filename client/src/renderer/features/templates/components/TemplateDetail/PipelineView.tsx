/**
 * PipelineView
 * Read-only view of pipeline using PipelineGraph in view mode
 */

import { PipelineGraph } from '../../../pipelines/components/PipelineGraph';
import { useModules } from '../../../modules';
import type { PipelineState, VisualState } from '../../../pipelines/types';

interface PipelineViewProps {
  pipelineState: PipelineState;
  visualState: VisualState;
}

export function PipelineView({
  pipelineState,
  visualState,
}: PipelineViewProps) {
  // Fetch modules using TanStack Query - returns stable cached reference
  const { data: modules = [] } = useModules();

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Pipeline graph with stable modules array */}
      <div className="flex-1">
        <PipelineGraph
          pipelineState={pipelineState}
          visualState={visualState}
          mode="view"
          modules={modules}
        />
      </div>
    </div>
  );
}
