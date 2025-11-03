import { EtoRunListItem } from '../../types';
import { BaseEtoRunRow } from '../base';

interface FailureRunRowProps {
  run: EtoRunListItem;
  onReview: (runId: number) => void;
  onSkip: (runId: number) => void;
  isSelected?: boolean;
  onToggleSelect?: (runId: number) => void;
}

export function FailureRunRow({ run, onReview, onSkip, isSelected, onToggleSelect }: FailureRunRowProps) {
  return (
    <BaseEtoRunRow run={run} isSelected={isSelected} onToggleSelect={onToggleSelect}>
      <button
        onClick={() => onReview(run.id)}
        className="px-3 py-1 text-xs bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
      >
        Review
      </button>
      <button
        onClick={() => onSkip(run.id)}
        className="px-3 py-1 text-xs bg-yellow-600 hover:bg-yellow-700 text-white rounded transition-colors"
      >
        Skip
      </button>
    </BaseEtoRunRow>
  );
}
