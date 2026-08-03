import { useEffect, useMemo } from 'react';
import { Drawer, Button, Space, Divider, App } from 'antd';
import { useRuleEditorStore } from '../../stores/ruleStore';
import { useRules, useCreateRule, useUpdateRule } from '../../hooks/useRules';
import { useAllRuleSets } from '../../hooks/useRuleSets';
import { dataSourcesApi } from '../../api/dataSources';
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
  const dataContext = useRuleEditorStore((s) => s.dataContext);
  const setDataContext = useRuleEditorStore((s) => s.setDataContext);
  const resetEditor = useRuleEditorStore((s) => s.resetEditor);
  const { message } = App.useApp();
  const createRule = useCreateRule();
  const updateRule = useUpdateRule();

  const { data: allRS } = useAllRuleSets();

  // 加载当前业务线所有规则，提取字段名供条件行下拉使用
  const { data: rulesData } = useRules(
    { rule_set_id: ruleSetId ?? undefined, page_size: 100 },
    { enabled: !!ruleSetId },
  );

  const ruleSetFields = useMemo(() => {
    if (!rulesData?.items) return [];
    return rulesData.items
      .filter((r) => r.id !== editingId)
      .map((r) => r.field_name)
      .filter(Boolean) as string[];
  }, [rulesData, editingId]);

  // 打开编辑器时，如果没有 dataContext（未通过上传文件设置），则通过规则集关联的数据源加载列信息
  useEffect(() => {
    if (open && !dataContext && ruleSetId) {
      // 找到当前规则集，获取其关联的 data_source_id
      const currentRS = allRS?.items?.find((rs) => rs.id === ruleSetId);
      const targetDSId = currentRS?.data_source_id;

      if (targetDSId) {
        // 按规则集绑定的数据源加载字段
        dataSourcesApi.preview(targetDSId, 100).then((res) => {
          if (res.column_profiles) {
            setDataContext({
              columnProfiles: res.column_profiles,
              previewRows: res.preview_rows,
              totalRows: res.total_rows,
            });
          }
        }).catch(() => {
          // 数据源不可用，静默失败
        });
      }
    }
  }, [open, dataContext, ruleSetId, allRS, setDataContext]);

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
        <BasicInfoForm ruleSetId={ruleSetId} editingId={editingId} />

        <Divider style={{ margin: '12px 0' }} />

        {/* 根据规则类型切换配置面板 */}
        {ruleType === 'mapping' && <ConditionBuilder ruleSetFields={ruleSetFields} />}
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
