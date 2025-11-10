/**
 * PipelineView
 * Placeholder for pipeline visualization
 */

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
      {/* Placeholder - PipelineGraph causes infinite loop in read-only mode */}
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center max-w-md p-8">
          <div className="mb-4 text-gray-400">
            <svg className="w-16 h-16 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">Pipeline Visualization</h3>
          <p className="text-sm text-gray-400 mb-4">
            {pipelineState.modules.length} modules, {pipelineState.entry_points.length} entry points, {pipelineState.connections.length} connections
          </p>
          <p className="text-xs text-gray-500">
            Pipeline visualization is temporarily unavailable in view mode.
          </p>
        </div>
      </div>
    </div>
  );
}
