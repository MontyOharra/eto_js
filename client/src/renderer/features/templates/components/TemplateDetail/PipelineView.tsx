/**
 * PipelineView
 * Temporary simplified view - empty pipeline graph
 */

import { PipelineGraph } from '../../../pipelines/components/PipelineGraph';
import type { PipelineState, VisualState } from '../../../pipelines/types';

interface PipelineViewProps {
  pipelineState: PipelineState;
  visualState: VisualState;
}

export function PipelineView({
  pipelineState,
  visualState,
}: PipelineViewProps) {
  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Pipeline graph - empty for now */}
      <div className="flex-1">
        <PipelineGraph mode="view" />
      </div>
    </div>
  );
}
