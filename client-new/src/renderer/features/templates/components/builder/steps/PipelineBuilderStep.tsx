import { PipelineState, VisualState } from '../../../types';

interface PipelineBuilderStepProps {
  pipelineState: PipelineState;
  visualState: VisualState;
  onPipelineStateChange: (state: PipelineState) => void;
  onVisualStateChange: (state: VisualState) => void;
}

export function PipelineBuilderStep({
  pipelineState,
  visualState,
  onPipelineStateChange,
  onVisualStateChange,
}: PipelineBuilderStepProps) {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center">
        <h3 className="text-2xl font-bold text-white mb-2">
          Step 3: Pipeline Definition
        </h3>
        <p className="text-gray-400 mb-4">
          Define data transformations
        </p>
        <p className="text-sm text-gray-500">
          This is where users will build a visual pipeline to transform extracted data
        </p>
      </div>
    </div>
  );
}
