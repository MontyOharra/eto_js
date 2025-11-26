import { EtoRunListItem } from '../../types';
import { BaseEtoRunRow } from './BaseEtoRunRow';

interface SkippedRunRowProps {
  run: EtoRunListItem;
  onReprocess: (runId: number) => void;
  onDelete: (runId: number) => void;
  isSelected?: boolean;
  onToggleSelect?: (runId: number) => void;
}

export function SkippedRunRow({ run, onReprocess, onDelete, isSelected, onToggleSelect }: SkippedRunRowProps) {
  return (
    <BaseEtoRunRow run={run} isSelected={isSelected} onToggleSelect={onToggleSelect}>
      <button
        onClick={() => onReprocess(run.id)}
        className="px-3 py-1 text-xs bg-green-600 hover:bg-green-700 text-white rounded transition-colors"
      >
        Reprocess
      </button>
      <button
        onClick={() => onDelete(run.id)}
        className="px-3 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
      >
        Delete
      </button>
    </BaseEtoRunRow>
  );
}
