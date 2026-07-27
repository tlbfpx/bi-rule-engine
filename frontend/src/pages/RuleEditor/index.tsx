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
  const store = useRuleEditorStore();
  const { message } = App.useApp();
  const createRule = useCreateRule();
  const updateRule = useUpdateRule();

  const handleSave = async () => {
    if (!store.fieldName.trim()) {
      message.error('请输入目标字段名');
      return;
    }

    if (!store.ruleSetId && !store.editingId) {
      message.error('请先选择所属业务线');
      return;
    }

    const payload = {
      rule_set_id: store.ruleSetId || undefined,
      field_name: store.fieldName,
      field_label: store.fieldLabel || undefined,
      rule_type: store.ruleType,
      priority: store.priority,
      enabled: store.enabled,
      config: store.config,
      depends_on: store.dependsOn.length > 0 ? store.dependsOn : undefined,
      description: store.description || undefined,
    };

    try {
      if (store.editingId) {
        await updateRule.mutateAsync({ id: store.editingId, data: payload });
        message.success('规则已更新');
      } else {
        await createRule.mutateAsync(payload);
        message.success('规则已创建');
      }
      store.resetEditor();
    } catch {
      // 错误已在拦截器中处理
    }
  };

  const isSaving = createRule.isPending || updateRule.isPending;

  return (
    <Drawer
      title={
        <Space>
          <span>{store.editingId ? '编辑规则' : '新建规则'}</span>
          {store.editingId && (
            <span style={{ fontSize: 12, color: '#999', fontFamily: 'monospace' }}>
              {store.fieldName}
            </span>
          )}
        </Space>
      }
      open={store.open}
      onClose={store.resetEditor}
      width={900}
      destroyOnClose
      extra={
        <Space>
          <Button onClick={store.resetEditor}>取消</Button>
          <Button type="primary" onClick={handleSave} loading={isSaving}>
            {store.editingId ? '保存' : '创建'}
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
        {store.ruleType === 'mapping' && <ConditionBuilder />}
        {store.ruleType === 'cleaning' && <CleaningConfig />}
        {store.ruleType === 'lookup' && <LookupConfig />}
        {store.ruleType === 'computed' && <FormulaEditor />}

        <Divider style={{ margin: '12px 0' }} />

        {/* 单条规则逻辑流程图（实时） */}
        <FlowchartPreview />
      </div>
    </Drawer>
  );
}
