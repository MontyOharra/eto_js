import { EtoRunListItem } from '../../types';
import { BaseEtoRunRow } from '../base';

interface SkippedRunRowProps {
  run: EtoRunListItem;
  onReprocess: (runId: number) => void;
  onDelete: (runId: number) => void;
}

export function SkippedRunRow({ run, onReprocess, onDelete }: SkippedRunRowProps) {
  return (
    <BaseEtoRunRow run={run}>
      <button
        onClick={() => onReprocess(run.id)}
        className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
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
