import { EtoRunListItem } from '../../types';
import { BaseEtoRunRow } from '../base';

interface NotStartedRunRowProps {
  run: EtoRunListItem;
}

export function NotStartedRunRow({ run }: NotStartedRunRowProps) {
  return <BaseEtoRunRow run={run} />;
}
