import { Select } from 'antd';
import type { OperatorType } from '../types';

const OPERATOR_OPTIONS: { value: OperatorType; label: string }[] = [
  { value: 'eq', label: '等于 (=)' },
  { value: 'neq', label: '不等于 (≠)' },
  { value: 'contains', label: '包含' },
  { value: 'matches', label: '正则匹配' },
  { value: 'starts_with', label: '开头是' },
  { value: 'ends_with', label: '结尾是' },
  { value: 'in', label: '在列表中' },
  { value: 'between', label: '在范围内' },
  { value: 'gt', label: '大于 (>)' },
  { value: 'gte', label: '大于等于 (≥)' },
  { value: 'lt', label: '小于 (<)' },
  { value: 'lte', label: '小于等于 (≤)' },
  { value: 'is_null', label: '为空' },
  { value: 'is_not_null', label: '不为空' },
];

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
