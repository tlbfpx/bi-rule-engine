import { useState, useMemo } from 'react';
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
  value, onChange, style, placeholder = '选择或输入字段名', availableFields, columnProfiles, fieldLabels,
}: Props) {
  const fields = availableFields || [];
  const labels = fieldLabels || {};
  const [searchText, setSearchText] = useState('');

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

  // 搜索文本不在已有字段中时，追加为自定义选项
  const options = useMemo(() => {
    const opts = fields.map((f) => ({ value: f, label: getLabel(f) }));
    const trimmed = searchText.trim();
    if (trimmed && !fields.some((f) => f.toLowerCase() === trimmed.toLowerCase())) {
      opts.push({ value: trimmed, label: `"${trimmed}" (自定义)` });
    }
    return opts;
  }, [fields, searchText]);

  return (
    <Select
      value={value || undefined}
      onChange={(v) => {
        onChange?.(v);
        setSearchText('');
      }}
      onSearch={setSearchText}
      onBlur={() => setSearchText('')}
      style={{ minWidth: 160, ...style }}
      placeholder={placeholder}
      showSearch
      notFoundContent={fields.length === 0 ? '暂无可选字段，可直接输入自定义字段名' : undefined}
      filterOption={(input, option) => {
        const fieldName = String(option?.value ?? '').toLowerCase();
        const labelStr = String(option?.label ?? '').toLowerCase();
        const search = input.toLowerCase();
        return labelStr.includes(search) || fieldName.includes(search);
      }}
      options={options}
      optionRender={(option) => {
        const sample = getSample(option.value as string);
        if (sample) {
          return (
            <Tooltip title={`样本: ${sample}`} placement="right">
              <span>{option.label as string}</span>
            </Tooltip>
          );
        }
        return <span>{option.label as string}</span>;
      }}
    />
  );
}
