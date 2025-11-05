import { EtoRunListItem } from '../../types';
import { BaseEtoRunRow } from './BaseEtoRunRow';

interface NeedsTemplateRunRowProps {
  run: EtoRunListItem;
  onBuildTemplate: (runId: number) => void;
  onReprocess: (runId: number) => void;
  onSkip: (runId: number) => void;
  isSelected?: boolean;
  onToggleSelect?: (runId: number) => void;
}

export function NeedsTemplateRunRow({ run, onBuildTemplate, onReprocess, onSkip, isSelected, onToggleSelect }: NeedsTemplateRunRowProps) {
  return (
    <BaseEtoRunRow run={run} isSelected={isSelected} onToggleSelect={onToggleSelect}>
      <button
        onClick={() => onBuildTemplate(run.id)}
        className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
      >
        Build Template
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
