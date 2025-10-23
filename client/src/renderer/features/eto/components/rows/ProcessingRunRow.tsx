import { EtoRunListItem } from '../../types';
import { BaseEtoRunRow } from '../base';

interface ProcessingRunRowProps {
  run: EtoRunListItem;
}

export function ProcessingRunRow({ run }: ProcessingRunRowProps) {
  return <BaseEtoRunRow run={run} />;
}
