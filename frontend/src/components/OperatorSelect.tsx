import { Select } from 'antd';
import type { OperatorType } from '../types';
import { OPERATOR_OPTIONS } from '../utils/ruleLabels';

interface Props {
  value?: OperatorType;
  onChange?: (v: OperatorType) => void;
  style?: React.CSSProperties;
}

export default function OperatorSelect({ value, onChange, style }: Props) {
  return (
    <Select
      value={value}
      onChange={onChange}
      style={{ minWidth: 140, ...style }}
      options={OPERATOR_OPTIONS}
      placeholder="选择运算符"
    />
  );
}
