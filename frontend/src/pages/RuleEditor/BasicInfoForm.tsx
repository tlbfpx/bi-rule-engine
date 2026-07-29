import { Form, Input, Select, InputNumber, Switch, Space } from 'antd';
import { useRuleEditorStore } from '../../stores/ruleStore';
import { RULE_TYPE_OPTIONS } from '../../utils/ruleLabels';

export default function BasicInfoForm() {
  const {
    fieldName, fieldLabel, ruleType, priority, enabled, description,
    setFieldName, setFieldLabel, setRuleType, setPriority, setEnabled, setDescription,
  } = useRuleEditorStore();

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
      </Form>
    </div>
  );
}
