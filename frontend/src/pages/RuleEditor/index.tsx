import { Drawer, Button, Space, Divider, App } from 'antd';
import { useRuleEditorStore } from '../../stores/ruleStore';
import { useCreateRule, useUpdateRule } from '../../hooks/useRules';
import BasicInfoForm from './BasicInfoForm';
import ConditionBuilder from './ConditionBuilder';
import CleaningConfig from './CleaningConfig';
import LookupConfig from './LookupConfig';
import FormulaEditor from './FormulaEditor';
import FlowchartPreview from './FlowchartPreview';

export default function RuleEditorDrawer() {
  const open = useRuleEditorStore((s) => s.open);
  const editingId = useRuleEditorStore((s) => s.editingId);
  const fieldName = useRuleEditorStore((s) => s.fieldName);
  const ruleSetId = useRuleEditorStore((s) => s.ruleSetId);
  const fieldLabel = useRuleEditorStore((s) => s.fieldLabel);
  const ruleType = useRuleEditorStore((s) => s.ruleType);
  const priority = useRuleEditorStore((s) => s.priority);
  const enabled = useRuleEditorStore((s) => s.enabled);
  const config = useRuleEditorStore((s) => s.config);
  const dependsOn = useRuleEditorStore((s) => s.dependsOn);
  const description = useRuleEditorStore((s) => s.description);
  const resetEditor = useRuleEditorStore((s) => s.resetEditor);
  const { message } = App.useApp();
  const createRule = useCreateRule();
  const updateRule = useUpdateRule();

  const handleSave = async () => {
    if (!fieldName.trim()) {
      message.error('请输入目标字段名');
      return;
    }

    if (!ruleSetId && !editingId) {
      message.error('请先选择所属业务线');
      return;
    }

    const payload = {
      rule_set_id: ruleSetId || undefined,
      field_name: fieldName,
      field_label: fieldLabel || undefined,
      rule_type: ruleType,
      priority: priority,
      enabled: enabled,
      config: config,
      depends_on: dependsOn.length > 0 ? dependsOn : undefined,
      description: description || undefined,
    };

    try {
      if (editingId) {
        await updateRule.mutateAsync({ id: editingId, data: payload });
        message.success('规则已更新');
      } else {
        await createRule.mutateAsync(payload);
        message.success('规则已创建');
      }
      resetEditor();
    } catch {
      // 错误已在拦截器中处理
    }
  };

  const isSaving = createRule.isPending || updateRule.isPending;

  return (
    <Drawer
      title={
        <Space>
          <span>{editingId ? '编辑规则' : '新建规则'}</span>
          {editingId && (
            <span style={{ fontSize: 12, color: '#999', fontFamily: 'monospace' }}>
              {fieldName}
            </span>
          )}
        </Space>
      }
      open={open}
      onClose={resetEditor}
      width={900}
      destroyOnClose
      extra={
        <Space>
          <Button onClick={resetEditor}>取消</Button>
          <Button type="primary" onClick={handleSave} loading={isSaving}>
            {editingId ? '保存' : '创建'}
          </Button>
        </Space>
      }
      styles={{ body: { paddingBottom: 80 } }}
    >
      <div className="rule-editor-body">
        {/* 基本信息 */}
        <BasicInfoForm />

        <Divider style={{ margin: '12px 0' }} />

        {/* 根据规则类型切换配置面板 */}
        {ruleType === 'mapping' && <ConditionBuilder />}
        {ruleType === 'cleaning' && <CleaningConfig />}
        {ruleType === 'lookup' && <LookupConfig />}
        {ruleType === 'computed' && <FormulaEditor />}

        <Divider style={{ margin: '12px 0' }} />

        {/* 单条规则逻辑流程图（实时） */}
        <FlowchartPreview />
      </div>
    </Drawer>
  );
}
