/**
 * PipelineStep
 * Step 3: Build the transformation pipeline using extraction field entry points
 */

import { PipelineEditor } from '../../../pipelines/components/PipelineEditor';
import type { PipelineState, VisualState } from '../../../pipelines/types';

interface PipelineStepProps {
  pipelineState: PipelineState;
  visualState: VisualState;
  onPipelineStateChange: (state: PipelineState) => void;
  onVisualStateChange: (state: VisualState) => void;
}

export function PipelineStep({
  pipelineState,
  visualState,
  onPipelineStateChange,
  onVisualStateChange,
}: PipelineStepProps) {
  return (
    <div className="h-full w-full overflow-hidden">
      <PipelineEditor
        pipelineState={pipelineState}
        visualState={visualState}
        entryPoints={pipelineState.entry_points}
        onPipelineStateChange={onPipelineStateChange}
        onVisualStateChange={onVisualStateChange}
      />
    </div>
  );
}
