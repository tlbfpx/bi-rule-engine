import { useEffect, useMemo } from 'react';
import { Drawer, Button, Space, Divider, App, Modal } from 'antd';
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
import type { RuleConfig, RuleType } from '../../types';

/** 前端配置完整性校验
 *
 * ⚠️ 与后端 backend/app/services/rule_validator.py:validate_rule_config 保持同步。
 * 修改校验规则时，务必同时更新两端代码。
 */
function validateConfigBeforeSave(
  ruleType: RuleType,
  config: RuleConfig,
): string[] {
  const errors: string[] = [];

  if (ruleType === 'mapping') {
    const groups = config.conditions || [];
    if (groups.length === 0) {
      errors.push('至少需要 1 个条件组');
      return errors;
    }

    let hasResult = false;
    for (let gi = 0; gi < groups.length; gi++) {
      const g = groups[gi];
      const gp = `条件组${gi + 1}`;
      const rows = g.rows || [];

      if (rows.length === 0) {
        errors.push(`${gp}: 至少需要 1 个条件行`);
        continue;
      }

      for (let ri = 0; ri < rows.length; ri++) {
        const row = rows[ri];
        const rp = `${gp}/行${ri + 1}`;
        if (!row.field) errors.push(`${rp}: 字段名未填写`);
        if (!row.operator) errors.push(`${rp}: 操作符未选择`);
        const op = row.operator || '';
        const val = row.value;
        if (op !== 'is_null' && op !== 'is_not_null' && (val === null || val === undefined || val === '')) {
          errors.push(`${rp}: 比较值未填写`);
        }
      }

      if (g.result_value !== null && g.result_value !== undefined && g.result_value !== '') {
        hasResult = true;
      }
    }

    // 检查兜底值
    const hasDefault =
      config.default_result !== null &&
      config.default_result !== undefined &&
      config.default_result !== '';
    if (!hasResult && !hasDefault) {
      errors.push('所有条件组均未设置结果值，且没有默认值兜底');
    }
  } else if (ruleType === 'cleaning') {
    if (!config.cleaning_steps?.length) {
      errors.push('至少需要 1 个清洗步骤');
    }
  } else if (ruleType === 'lookup') {
    if (!config.lookup_table_id) errors.push('需要选择字典表');
    if (!config.lookup_key_field) errors.push('需要指定匹配键字段');
    if (!config.lookup_value_field) errors.push('需要指定取值字段');
  } else if (ruleType === 'computed') {
    if (!config.formula_expression?.trim()) {
      errors.push('需要填写计算公式');
    }
  }

  return errors;
}

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

  // 按规则集绑定的数据源 ID（稳定的依赖值，避免 allRS 对象引用变化导致 effect 重复执行）
  const targetDSId = allRS?.items?.find((rs) => rs.id === ruleSetId)?.data_source_id ?? null;

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
    if (open && !dataContext && targetDSId) {
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
  }, [open, dataContext, targetDSId, setDataContext]);

  const handleSave = async () => {
    if (!fieldName.trim()) {
      message.error('请输入目标字段名');
      return;
    }

    if (!ruleSetId && !editingId) {
      message.error('请先选择所属业务线');
      return;
    }

    // 校验配置完整性
    const errors = validateConfigBeforeSave(ruleType, config);
    if (errors.length > 0) {
      Modal.warning({
        title: '规则配置不完整',
        content: (
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {errors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        ),
        okText: '返回修改',
      });
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
      size="large"
      destroyOnHidden
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
