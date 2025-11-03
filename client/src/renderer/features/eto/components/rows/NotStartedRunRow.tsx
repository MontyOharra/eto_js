import { EtoRunListItem } from '../../types';
import { BaseEtoRunRow } from '../base';

interface NotStartedRunRowProps {
  run: EtoRunListItem;
  isSelected?: boolean;
  onToggleSelect?: (runId: number) => void;
}

export function NotStartedRunRow({ run, isSelected, onToggleSelect }: NotStartedRunRowProps) {
  return <BaseEtoRunRow run={run} isSelected={isSelected} onToggleSelect={onToggleSelect} />;
}
