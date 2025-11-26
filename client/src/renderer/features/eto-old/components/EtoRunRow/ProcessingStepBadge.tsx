import { EtoProcessingStep } from '../../types';

interface ProcessingStepBadgeProps {
  step: EtoProcessingStep;
}

export function ProcessingStepBadge({ step }: ProcessingStepBadgeProps) {
  const getStepColor = (step: EtoProcessingStep) => {
    switch (step) {
      case 'template_matching':
        return 'text-purple-400';
      case 'data_extraction':
        return 'text-blue-400';
      case 'data_transformation':
        return 'text-cyan-400';
      default:
        return 'text-gray-400';
    }
  };

  const getStepLabel = (step: EtoProcessingStep) => {
    switch (step) {
      case 'template_matching':
        return 'Template Matching';
      case 'data_extraction':
        return 'Data Extraction';
      case 'data_transformation':
        return 'Data Transformation';
      default:
        return step;
    }
  };

  return (
    <span className={`text-xs font-medium ${getStepColor(step)}`}>
      ({getStepLabel(step)})
    </span>
  );
}
