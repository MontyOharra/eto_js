import { EtoRunListItem } from '../../types';
import { BaseEtoRunRow } from '../base';

interface FailureRunRowProps {
  run: EtoRunListItem;
  onReview: (runId: number) => void;
  onSkip: (runId: number) => void;
}

export function FailureRunRow({ run, onReview, onSkip }: FailureRunRowProps) {
  return (
    <BaseEtoRunRow run={run}>
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
