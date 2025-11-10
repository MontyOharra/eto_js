/**
 * PipelineView
 * Temporary simplified view - pipeline graph with mock entry point
 */

import { useMemo } from 'react';
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
  // Create a minimal mock pipeline with one entry point
  const mockPipelineState: PipelineState = useMemo(() => ({
    modules: [],
    entry_points: [
      {
        entry_point_id: 'mock-entry-1',
        name: 'Entry Point',
        outputs: [
          {
            node_id: 'mock-output-1',
            name: 'output',
            type: 'str',
            allowed_types: ['str'],
          },
        ],
      },
    ],
    connections: [],
  }), []);

  const mockVisualState: VisualState = useMemo(() => ({
    'mock-entry-1': { x: 100, y: 100 },
  }), []);

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Pipeline graph - mock entry point for now */}
      <div className="flex-1">
        <PipelineGraph
          pipelineState={mockPipelineState}
          visualState={mockVisualState}
          mode="view"
        />
      </div>
    </div>
  );
}
