import { EtoRunListItem } from '../../types';
import { BaseEtoRunRow } from './BaseEtoRunRow';

interface FailureRunRowProps {
  run: EtoRunListItem;
  onView: (runId: number) => void;
  onSkip: (runId: number) => void;
  onReprocess: (runId: number) => void;
  isSelected?: boolean;
  onToggleSelect?: (runId: number) => void;
}

export function FailureRunRow({ run, onView, onSkip, onReprocess, isSelected, onToggleSelect }: FailureRunRowProps) {
  return (
    <BaseEtoRunRow run={run} isSelected={isSelected} onToggleSelect={onToggleSelect}>
      <button
        onClick={() => onView(run.id)}
        className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
      >
        View
      </button>
      <button
        onClick={() => onReprocess(run.id)}
        className="px-3 py-1 text-xs bg-green-600 hover:bg-green-700 text-white rounded transition-colors"
      >
        Reprocess
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
