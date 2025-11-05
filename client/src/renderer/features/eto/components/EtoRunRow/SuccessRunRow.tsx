import { EtoRunListItem } from '../../types';
import { BaseEtoRunRow } from './BaseEtoRunRow';

interface SuccessRunRowProps {
  run: EtoRunListItem;
  onView: (runId: number) => void;
  isSelected?: boolean;
  onToggleSelect?: (runId: number) => void;
}

export function SuccessRunRow({ run, onView, isSelected, onToggleSelect }: SuccessRunRowProps) {
  return (
    <BaseEtoRunRow run={run} isSelected={isSelected} onToggleSelect={onToggleSelect}>
      <button
        onClick={() => onView(run.id)}
        className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
      >
        View
      </button>
    </BaseEtoRunRow>
  );
}
