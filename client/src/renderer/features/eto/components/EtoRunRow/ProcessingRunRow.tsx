import { EtoRunListItem } from '../../types';
import { BaseEtoRunRow } from './BaseEtoRunRow';

interface ProcessingRunRowProps {
  run: EtoRunListItem;
  isSelected?: boolean;
  onToggleSelect?: (runId: number) => void;
}

export function ProcessingRunRow({ run, isSelected, onToggleSelect }: ProcessingRunRowProps) {
  return <BaseEtoRunRow run={run} isSelected={isSelected} onToggleSelect={onToggleSelect} />;
}
