import { Button, Select, Input, Space, Typography, Empty } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useRuleEditorStore } from '../../stores/ruleStore';
import { CLEANING_ACTION_OPTIONS as ACTION_OPTIONS } from '../../utils/ruleLabels';

export default function CleaningConfig() {
  const { config, addCleaningStep, removeCleaningStep, updateCleaningStep } = useRuleEditorStore();

  return (
    <div>
      <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 12 }}>
        步骤按顺序执行，上一步的输出作为下一步的输入
      </Typography.Text>

      {config.cleaning_steps.length === 0 ? (
        <Empty description="暂无清洗步骤" style={{ padding: '24px 0' }} />
      ) : (
        config.cleaning_steps.map((step, idx) => (
          <div key={step.id} className="condition-group-card" style={{ padding: 12 }}>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Space>
                <Typography.Text strong>步骤 {idx + 1}</Typography.Text>
                <Select
                  value={step.action}
                  onChange={(v) => updateCleaningStep(step.id, { action: v })}
                  options={ACTION_OPTIONS}
                  style={{ width: 150 }}
                />
                {step.action === 'fill_null' && (
                  <Input
                    value={String(step.params?.fill_value ?? '')}
                    onChange={(e) => updateCleaningStep(step.id, { params: { ...step.params, fill_value: e.target.value } })}
                    placeholder="填充值"
                    style={{ width: 150 }}
                  />
                )}
                {step.action === 'replace_string' && (
                  <>
                    <Input
                      value={String(step.params?.old ?? '')}
                      onChange={(e) => updateCleaningStep(step.id, { params: { ...step.params, old: e.target.value } })}
                      placeholder="查找内容"
                      style={{ width: 150 }}
                    />
                    <Typography.Text type="secondary">→</Typography.Text>
                    <Input
                      value={String(step.params?.new ?? '')}
                      onChange={(e) => updateCleaningStep(step.id, { params: { ...step.params, new: e.target.value } })}
                      placeholder="替换为"
                      style={{ width: 150 }}
                    />
                  </>
                )}
                {step.action === 'regex_extract' && (
                  <Input
                    value={String(step.params?.pattern ?? '')}
                    onChange={(e) => updateCleaningStep(step.id, { params: { ...step.params, pattern: e.target.value } })}
                    placeholder="正则表达式"
                    style={{ width: 200 }}
                  />
                )}
                {step.action === 'case_convert' && (
                  <Select
                    value={step.params?.mode || 'upper'}
                    onChange={(v) => updateCleaningStep(step.id, { params: { ...step.params, mode: v } })}
                    options={[
                      { value: 'upper', label: '转大写' },
                      { value: 'lower', label: '转小写' },
                    ]}
                    style={{ width: 110 }}
                  />
                )}
              </Space>
              <Button size="small" danger icon={<DeleteOutlined />} onClick={() => removeCleaningStep(step.id)} />
            </Space>
          </div>
        ))
      )}

      <Button type="dashed" icon={<PlusOutlined />} onClick={addCleaningStep} block style={{ marginTop: 8 }}>
        添加清洗步骤
      </Button>
    </div>
  );
}
