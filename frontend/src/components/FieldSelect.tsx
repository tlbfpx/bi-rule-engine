import { Select } from 'antd';

interface Props {
  value?: string;
  onChange?: (v: string) => void;
  style?: React.CSSProperties;
  placeholder?: string;
  availableFields?: string[];
}

export default function FieldSelect({ value, onChange, style, placeholder = '选择字段', availableFields }: Props) {
  const fields = availableFields || [];
  return (
    <Select
      value={value || undefined}
      onChange={onChange}
      style={{ minWidth: 160, ...style }}
      placeholder={placeholder}
      showSearch
      filterOption={(input, option) =>
        (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
      }
      options={fields.map((f) => ({ value: f, label: f }))}
    />
  );
}
