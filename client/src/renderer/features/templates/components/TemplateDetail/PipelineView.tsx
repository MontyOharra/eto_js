/**
 * PipelineView
 * Read-only view of pipeline using PipelineGraph in view mode
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
  // No-op callbacks for view mode (prevent infinite loop)
  const handlePipelineStateChange = () => {
    // Read-only view - no state changes
  };

  const handleVisualStateChange = () => {
    // Read-only view - no state changes
  };

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Info banner */}
      <div className="border-b border-gray-700 bg-gray-800 px-6 py-3">
        <p className="text-sm text-gray-400">
          Read-only view of the pipeline.
          <span className="ml-2 text-gray-500">
            {pipelineState.modules.length} modules, {pipelineState.entry_points.length} entry points, {pipelineState.connections.length} connections
          </span>
        </p>
      </div>

      {/* Pipeline graph */}
      <div className="flex-1">
        <PipelineGraph
          pipelineState={pipelineState}
          visualState={visualState}
          mode="view"
          onPipelineStateChange={handlePipelineStateChange}
          onVisualStateChange={handleVisualStateChange}
        />
      </div>
    </div>
  );
}
