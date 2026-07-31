import { Select, Tooltip } from 'antd';
import type { ColumnProfile } from '../types';

interface Props {
  value?: string;
  onChange?: (v: string) => void;
  style?: React.CSSProperties;
  placeholder?: string;
  availableFields?: string[];
  columnProfiles?: Record<string, ColumnProfile>;
  fieldLabels?: Record<string, string>;
}

export default function FieldSelect({
  value, onChange, style, placeholder = '选择字段', availableFields, columnProfiles, fieldLabels,
}: Props) {
  const fields = availableFields || [];
  const labels = fieldLabels || {};

  const getLabel = (field: string): string => {
    const lbl = labels[field];
    if (lbl && lbl !== field) return `${lbl} (${field})`;
    return field;
  };

  const getSample = (field: string): string | null => {
    const profile = columnProfiles?.[field];
    if (!profile?.sample_values?.length) return null;
    return profile.sample_values.slice(0, 3).join(', ');
  };

  return (
    <Select
      value={value || undefined}
      onChange={onChange}
      style={{ minWidth: 160, ...style }}
      placeholder={placeholder}
      showSearch
      filterOption={(input, option) => {
        const label = (option?.label as string)?.toLowerCase() || '';
        const fieldName = (option?.value as string)?.toLowerCase() || '';
        const search = input.toLowerCase();
        return label.includes(search) || fieldName.includes(search);
      }}
      options={fields.map((f) => {
        const label = getLabel(f);
        const sample = getSample(f);
        return {
          value: f,
          label: (
            <Tooltip title={sample ? `样本: ${sample}` : undefined} placement="right">
              <span>{label}</span>
            </Tooltip>
          ),
        };
      })}
    />
  );
}
