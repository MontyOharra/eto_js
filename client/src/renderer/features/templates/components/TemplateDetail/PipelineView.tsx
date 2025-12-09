/**
 * PipelineView
 * Read-only view of pipeline using PipelineGraph in view mode
 */

import { useMemo } from 'react';
import { PipelineGraph } from '../../../pipelines/components/PipelineGraph';
import { useModules, useOutputChannels } from '../../../modules';
import type { PipelineState, VisualState } from '../../../pipelines/types';
import type { ModuleTemplate, OutputChannelType } from '../../../modules/types';

// Stable empty arrays to prevent infinite re-renders
const EMPTY_MODULES: ModuleTemplate[] = [];
const EMPTY_OUTPUT_CHANNELS: OutputChannelType[] = [];

interface PipelineViewProps {
  pipelineState: PipelineState;
  visualState: VisualState;
}

export function PipelineView({
  pipelineState,
  visualState,
}: PipelineViewProps) {
  // Fetch modules and output channels using TanStack Query
  const { data: modulesData, isLoading: modulesLoading } = useModules();
  const { data: outputChannelsData, isLoading: channelsLoading } = useOutputChannels();

  // Memoize to ensure stable references
  const modules = useMemo(() => modulesData ?? EMPTY_MODULES, [modulesData]);
  const outputChannels = useMemo(() => outputChannelsData ?? EMPTY_OUTPUT_CHANNELS, [outputChannelsData]);

  // Show loading state while data is loading
  if (modulesLoading || channelsLoading) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading pipeline data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Pipeline graph with stable modules and output channels arrays */}
      <div className="flex-1">
        <PipelineGraph
          pipelineState={pipelineState}
          visualState={visualState}
          mode="view"
          modules={modules}
          outputChannels={outputChannels}
        />
      </div>
    </div>
  );
}
