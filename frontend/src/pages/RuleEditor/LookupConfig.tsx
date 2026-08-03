import { Select, Input, Space, Typography, Button, Empty } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useRuleEditorStore } from '../../stores/ruleStore';
import { useLookupTables } from '../../hooks/useLookupTables';
import OperatorSelect from '../../components/OperatorSelect';

export default function LookupConfig() {
  const { config, setLookupConfig, addLookupFallback, removeLookupFallback, updateLookupFallback } =
    useRuleEditorStore();
  const { data: tablesData } = useLookupTables({ page_size: 100 });

  const tables = tablesData?.items || [];
  const selectedTable = tables.find((t) => t.id === config.lookup_table_id);
  const tableColumns = selectedTable?.columns
    ? Object.keys(selectedTable.data?.[0] || {}).length > 0
      ? Object.keys(selectedTable.data?.[0] || {})
      : ['key', 'value']
    : [];

  return (
    <div>
      <Space orientation="vertical" style={{ width: '100%' }} size="middle">
        <div>
          <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>选择映射表</Typography.Text>
          <Select
            value={config.lookup_table_id}
            onChange={(v) => {
              setLookupConfig(v, config.lookup_key_field, config.lookup_value_field);
            }}
            options={tables.map((t) => ({ value: t.id, label: `${t.name} (${t.row_count} 行)` }))}
            placeholder="选择映射表"
            style={{ width: '100%' }}
            allowClear
            showSearch
            filterOption={(input, option) =>
              (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
            }
          />
        </div>

        {selectedTable && (
          <Space>
            <div>
              <Typography.Text type="secondary" style={{ display: 'block' }}>查找键列</Typography.Text>
              <Select
                value={config.lookup_key_field}
                onChange={(v) => setLookupConfig(config.lookup_table_id, v, config.lookup_value_field)}
                options={tableColumns.map((c) => ({ value: c, label: c }))}
                style={{ width: 160 }}
              />
            </div>
            <div>
              <Typography.Text type="secondary" style={{ display: 'block' }}>取值列</Typography.Text>
              <Select
                value={config.lookup_value_field}
                onChange={(v) => setLookupConfig(config.lookup_table_id, config.lookup_key_field, v)}
                options={tableColumns.map((c) => ({ value: c, label: c }))}
                style={{ width: 160 }}
              />
            </div>
          </Space>
        )}

        {/* 兜底规则 */}
        <div>
          <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>
            兜底规则（查找不到时）
          </Typography.Text>
          {config.lookup_fallbacks.length === 0 ? (
            <Empty description="暂无兜底规则" style={{ padding: 12 }} />
          ) : (
            config.lookup_fallbacks.map((fb) => (
              <div key={fb.id} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                <Typography.Text type="secondary">当</Typography.Text>
                <Input
                  value={fb.condition_field}
                  onChange={(e) => updateLookupFallback(fb.id, { condition_field: e.target.value })}
                  placeholder="字段"
                  style={{ width: 140 }}
                />
                <OperatorSelect
                  value={fb.condition_operator}
                  onChange={(v) => updateLookupFallback(fb.id, { condition_operator: v })}
                  style={{ width: 140 }}
                />
                <Input
                  value={String(fb.condition_value ?? '')}
                  onChange={(e) => updateLookupFallback(fb.id, { condition_value: e.target.value })}
                  placeholder="条件值"
                  style={{ width: 120 }}
                />
                <Typography.Text type="secondary">→</Typography.Text>
                <Input
                  value={String(fb.fallback_value ?? '')}
                  onChange={(e) => updateLookupFallback(fb.id, { fallback_value: e.target.value })}
                  placeholder="兜底值"
                  style={{ width: 120 }}
                />
                <Button size="small" danger icon={<DeleteOutlined />} onClick={() => removeLookupFallback(fb.id)} />
              </div>
            ))
          )}
          <Button size="small" type="dashed" icon={<PlusOutlined />} onClick={addLookupFallback}>
            添加兜底规则
          </Button>
        </div>
      </Space>
    </div>
  );
}
