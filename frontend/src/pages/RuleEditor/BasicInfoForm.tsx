import { Form, Input, Select, InputNumber, Switch, Space } from 'antd';
import { useMemo } from 'react';
import { useRuleEditorStore } from '../../stores/ruleStore';
import { useRules } from '../../hooks/useRules';
import { RULE_TYPE_OPTIONS } from '../../utils/ruleLabels';

interface Props {
  ruleSetId: string | null;
  editingId: string | null;
}

export default function BasicInfoForm({ ruleSetId, editingId }: Props) {
  const {
    fieldName, fieldLabel, ruleType, priority, enabled, description, dependsOn,
    setFieldName, setFieldLabel, setRuleType, setPriority, setEnabled, setDescription,
    setDependsOn,
  } = useRuleEditorStore();

  // 获取当前规则集的其他规则（供 depends_on 选择）
  const { data: rulesData } = useRules(
    { rule_set_id: ruleSetId ?? undefined, page_size: 100 },
    { enabled: !!ruleSetId },
  );

  const dependsOptions = useMemo(() => {
    const items = rulesData?.items ?? [];
    return items
      .filter((r) => r.id !== editingId) // 编辑时排除自身
      .map((r) => ({
        value: r.field_name,
        label: r.field_label ? `${r.field_label} (${r.field_name})` : r.field_name,
      }));
  }, [rulesData, editingId]);

  return (
    <div style={{ marginBottom: 16 }}>
      <Form layout="vertical" size="middle">
        <Space wrap style={{ width: '100%' }} size="middle">
          <Form.Item label="目标字段" required style={{ marginBottom: 0 }}>
            <Input
              value={fieldName}
              onChange={(e) => setFieldName(e.target.value)}
              placeholder="如: prod_class"
              style={{ width: 180 }}
            />
          </Form.Item>
          <Form.Item label="字段标签" style={{ marginBottom: 0 }}>
            <Input
              value={fieldLabel}
              onChange={(e) => setFieldLabel(e.target.value)}
              placeholder="如: 产品分类"
              style={{ width: 160 }}
            />
          </Form.Item>
          <Form.Item label="规则类型" required style={{ marginBottom: 0 }}>
            <Select
              value={ruleType}
              onChange={setRuleType}
              options={RULE_TYPE_OPTIONS}
              style={{ width: 140 }}
            />
          </Form.Item>
          <Form.Item label="优先级" style={{ marginBottom: 0 }}>
            <InputNumber
              value={priority}
              onChange={(v) => setPriority(v ?? 0)}
              min={0}
              style={{ width: 80 }}
            />
          </Form.Item>
          <Form.Item label="启用" style={{ marginBottom: 0 }}>
            <Switch checked={enabled} onChange={setEnabled} />
          </Form.Item>
        </Space>
        <Form.Item label="描述" style={{ marginTop: 12, marginBottom: 0 }}>
          <Input.TextArea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="规则说明（可选）"
            rows={3}
            maxLength={2000}
            showCount
          />
        </Form.Item>
        <Form.Item
          label="依赖规则"
          tooltip="标记本规则依赖哪些已有规则，确保这些规则先执行"
          style={{ marginTop: 12, marginBottom: 0 }}
        >
          <Select
            mode="multiple"
            value={dependsOn}
            onChange={setDependsOn}
            options={dependsOptions}
            placeholder={ruleSetId ? '选择本规则依赖的字段（可多选）' : '请先选择所属业务线'}
            disabled={!ruleSetId}
            style={{ width: '100%' }}
            notFoundContent="该业务线暂无其他规则"
            allowClear
          />
        </Form.Item>
      </Form>
    </div>
  );
}
