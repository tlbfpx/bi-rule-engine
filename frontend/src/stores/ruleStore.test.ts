import { describe, it, expect, beforeEach } from 'vitest';
import { useRuleEditorStore, generateId } from '../stores/ruleStore';
import type { RuleConfig, RuleType } from '../types';

describe('ruleStore (规则编辑器 Zustand store)', () => {
  beforeEach(() => {
    // 每个测试前重置 store
    useRuleEditorStore.getState().resetEditor();
  });

  // ============ generateId ============

  describe('generateId', () => {
    it('生成唯一的 UUID 格式 ID', () => {
      const id = generateId();
      expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
    });

    it('每次调用生成不同的 ID', () => {
      const id1 = generateId();
      const id2 = generateId();
      expect(id1).not.toBe(id2);
    });
  });

  // ============ 初始状态 ============

  describe('初始状态', () => {
    it('open 为 false', () => {
      expect(useRuleEditorStore.getState().open).toBe(false);
    });

    it('editingId 为 null', () => {
      expect(useRuleEditorStore.getState().editingId).toBeNull();
    });

    it('ruleType 默认为 mapping', () => {
      expect(useRuleEditorStore.getState().ruleType).toBe('mapping');
    });

    it('enabled 默认为 true', () => {
      expect(useRuleEditorStore.getState().enabled).toBe(true);
    });

    it('config 为默认空配置', () => {
      const config = useRuleEditorStore.getState().config;
      expect(config.conditions).toEqual([]);
      expect(config.cleaning_steps).toEqual([]);
      expect(config.lookup_table_id).toBeNull();
      expect(config.lookup_fallbacks).toEqual([]);
      expect(config.formula_expression).toBeNull();
      expect(config.default_result).toBeNull();
    });
  });

  // ============ openEditor / closeEditor ============

  describe('openEditor', () => {
    it('无参数时以新建模式打开', () => {
      useRuleEditorStore.getState().openEditor();
      const state = useRuleEditorStore.getState();
      expect(state.open).toBe(true);
      expect(state.editingId).toBeNull();
      expect(state.fieldName).toBe('');
    });

    it('传入规则时以编辑模式打开，正确填充字段', () => {
      const mockRule = {
        id: 'rule_001',
        rule_set_id: 'rs_001',
        field_name: 'amount',
        field_label: '金额',
        rule_type: 'computed' as RuleType,
        priority: 5,
        enabled: false,
        description: '计算字段',
        depends_on: ['rule_000'],
        config: {
          conditions: [],
          cleaning_steps: [],
          lookup_table_id: 'lt_001',
          lookup_key_field: 'key',
          lookup_value_field: 'value',
          lookup_fallbacks: [],
          formula_expression: 'amount * 0.1',
          default_result: 0,
        } as RuleConfig,
      };

      useRuleEditorStore.getState().openEditor(mockRule);
      const state = useRuleEditorStore.getState();

      expect(state.open).toBe(true);
      expect(state.editingId).toBe('rule_001');
      expect(state.fieldName).toBe('amount');
      expect(state.fieldLabel).toBe('金额');
      expect(state.ruleType).toBe('computed');
      expect(state.priority).toBe(5);
      expect(state.enabled).toBe(false);
      expect(state.description).toBe('计算字段');
      expect(state.dependsOn).toEqual(['rule_000']);
      expect(state.config.formula_expression).toBe('amount * 0.1');
    });

    it('新建模式保留传入的 ruleSetId', () => {
      useRuleEditorStore.getState().openEditor({ rule_set_id: 'rs_002' });
      expect(useRuleEditorStore.getState().ruleSetId).toBe('rs_002');
      expect(useRuleEditorStore.getState().editingId).toBeNull();
    });
  });

  describe('closeEditor', () => {
    it('open 设为 false', () => {
      useRuleEditorStore.getState().openEditor();
      useRuleEditorStore.getState().closeEditor();
      expect(useRuleEditorStore.getState().open).toBe(false);
    });
  });

  describe('resetEditor', () => {
    it('完全重置到初始状态', () => {
      useRuleEditorStore.getState().openEditor({
        id: 'test',
        field_name: 'test',
        rule_type: 'cleaning',
        priority: 10,
        enabled: false,
        description: 'desc',
        depends_on: [],
        config: {} as RuleConfig,
      });
      useRuleEditorStore.getState().setFieldName('changed');

      useRuleEditorStore.getState().resetEditor();
      const state = useRuleEditorStore.getState();

      expect(state.open).toBe(false);
      expect(state.editingId).toBeNull();
      expect(state.fieldName).toBe('');
      expect(state.ruleType).toBe('mapping');
      expect(state.priority).toBe(0);
      expect(state.enabled).toBe(true);
    });
  });

  // ============ 基本信息设置 ============

  describe('基本信息 setter', () => {
    it('setFieldName', () => {
      useRuleEditorStore.getState().setFieldName('new_field');
      expect(useRuleEditorStore.getState().fieldName).toBe('new_field');
    });

    it('setFieldLabel', () => {
      useRuleEditorStore.getState().setFieldLabel('新字段');
      expect(useRuleEditorStore.getState().fieldLabel).toBe('新字段');
    });

    it('setRuleType', () => {
      useRuleEditorStore.getState().setRuleType('lookup');
      expect(useRuleEditorStore.getState().ruleType).toBe('lookup');
    });

    it('setPriority', () => {
      useRuleEditorStore.getState().setPriority(99);
      expect(useRuleEditorStore.getState().priority).toBe(99);
    });

    it('setEnabled', () => {
      useRuleEditorStore.getState().setEnabled(false);
      expect(useRuleEditorStore.getState().enabled).toBe(false);
    });

    it('setDescription', () => {
      useRuleEditorStore.getState().setDescription('新描述');
      expect(useRuleEditorStore.getState().description).toBe('新描述');
    });

    it('setDependsOn', () => {
      useRuleEditorStore.getState().setDependsOn(['dep1', 'dep2']);
      expect(useRuleEditorStore.getState().dependsOn).toEqual(['dep1', 'dep2']);
    });
  });

  // ============ 条件组操作 ============

  describe('条件组操作', () => {
    beforeEach(() => {
      useRuleEditorStore.getState().openEditor();
    });

    it('addConditionGroup 添加新条件组，priority 递增', () => {
      useRuleEditorStore.getState().addConditionGroup();
      let groups = useRuleEditorStore.getState().config.conditions;
      expect(groups).toHaveLength(1);
      expect(groups[0].priority).toBe(1);
      expect(groups[0].logic).toBe('AND');
      expect(groups[0].rows).toHaveLength(1);
      expect(groups[0].result_type).toBe('constant');

      useRuleEditorStore.getState().addConditionGroup();
      groups = useRuleEditorStore.getState().config.conditions;
      expect(groups).toHaveLength(2);
      expect(groups[1].priority).toBe(2);
    });

    it('removeConditionGroup 按 ID 删除条件组', () => {
      useRuleEditorStore.getState().addConditionGroup();
      useRuleEditorStore.getState().addConditionGroup();
      const groups = useRuleEditorStore.getState().config.conditions;
      const firstId = groups[0].id;

      useRuleEditorStore.getState().removeConditionGroup(firstId);
      const remaining = useRuleEditorStore.getState().config.conditions;
      expect(remaining).toHaveLength(1);
      expect(remaining[0].id).not.toBe(firstId);
    });

    it('updateConditionGroup 更新条件组属性', () => {
      useRuleEditorStore.getState().addConditionGroup();
      const groupId = useRuleEditorStore.getState().config.conditions[0].id;

      useRuleEditorStore.getState().updateConditionGroup(groupId, {
        logic: 'OR',
        result_type: 'field_value',
        result_value: 'target_field',
      });

      const group = useRuleEditorStore.getState().config.conditions[0];
      expect(group.logic).toBe('OR');
      expect(group.result_type).toBe('field_value');
      expect(group.result_value).toBe('target_field');
    });

    it('reorderConditionGroups 重新排列并更新 priority', () => {
      useRuleEditorStore.getState().addConditionGroup();
      useRuleEditorStore.getState().addConditionGroup();
      useRuleEditorStore.getState().addConditionGroup();

      // 交换第 0 和第 2 个
      useRuleEditorStore.getState().reorderConditionGroups(0, 2);

      const groups = useRuleEditorStore.getState().config.conditions;
      expect(groups).toHaveLength(3);
      // priority 应该是 1, 2, 3
      expect(groups.map((g) => g.priority)).toEqual([1, 2, 3]);
    });
  });

  // ============ 条件行操作 ============

  describe('条件行操作', () => {
    beforeEach(() => {
      useRuleEditorStore.getState().openEditor();
      useRuleEditorStore.getState().addConditionGroup();
    });

    it('addConditionRow 在指定条件组中添加行', () => {
      const groupId = useRuleEditorStore.getState().config.conditions[0].id;
      useRuleEditorStore.getState().addConditionRow(groupId);

      const rows = useRuleEditorStore.getState().config.conditions[0].rows;
      expect(rows).toHaveLength(2);
      expect(rows[1].operator).toBe('eq');
    });

    it('removeConditionRow 从指定条件组中删除行', () => {
      const groupId = useRuleEditorStore.getState().config.conditions[0].id;
      useRuleEditorStore.getState().addConditionRow(groupId);
      const rows = useRuleEditorStore.getState().config.conditions[0].rows;
      const rowId = rows[1].id;

      useRuleEditorStore.getState().removeConditionRow(groupId, rowId);
      expect(useRuleEditorStore.getState().config.conditions[0].rows).toHaveLength(1);
    });

    it('updateConditionRow 更新行的字段/操作符/值', () => {
      const groupId = useRuleEditorStore.getState().config.conditions[0].id;
      const rowId = useRuleEditorStore.getState().config.conditions[0].rows[0].id;

      useRuleEditorStore.getState().updateConditionRow(groupId, rowId, {
        field: 'status',
        operator: 'gt',
        value: 100,
      });

      const row = useRuleEditorStore.getState().config.conditions[0].rows[0];
      expect(row.field).toBe('status');
      expect(row.operator).toBe('gt');
      expect(row.value).toBe(100);
    });
  });

  // ============ 清洗步骤操作 ============

  describe('清洗步骤操作', () => {
    beforeEach(() => {
      useRuleEditorStore.getState().openEditor();
    });

    it('addCleaningStep 添加清洗步骤，默认 action 为 fill_null', () => {
      useRuleEditorStore.getState().addCleaningStep();
      const steps = useRuleEditorStore.getState().config.cleaning_steps;
      expect(steps).toHaveLength(1);
      expect(steps[0].action).toBe('fill_null');
      expect(steps[0].params).toEqual({});
    });

    it('removeCleaningStep 按 ID 删除', () => {
      useRuleEditorStore.getState().addCleaningStep();
      useRuleEditorStore.getState().addCleaningStep();
      const steps = useRuleEditorStore.getState().config.cleaning_steps;
      const firstId = steps[0].id;

      useRuleEditorStore.getState().removeCleaningStep(firstId);
      expect(useRuleEditorStore.getState().config.cleaning_steps).toHaveLength(1);
    });

    it('updateCleaningStep 更新步骤属性', () => {
      useRuleEditorStore.getState().addCleaningStep();
      const stepId = useRuleEditorStore.getState().config.cleaning_steps[0].id;

      useRuleEditorStore.getState().updateCleaningStep(stepId, {
        action: 'regex_extract',
        params: { pattern: '\\d+' },
      });

      const step = useRuleEditorStore.getState().config.cleaning_steps[0];
      expect(step.action).toBe('regex_extract');
      expect(step.params.pattern).toBe('\\d+');
    });
  });

  // ============ 查找配置操作 ============

  describe('查找配置操作', () => {
    beforeEach(() => {
      useRuleEditorStore.getState().openEditor();
    });

    it('setLookupConfig 设置查找表/键字段/值字段', () => {
      useRuleEditorStore.getState().setLookupConfig('lt_001', 'code', 'name');
      const config = useRuleEditorStore.getState().config;
      expect(config.lookup_table_id).toBe('lt_001');
      expect(config.lookup_key_field).toBe('code');
      expect(config.lookup_value_field).toBe('name');
    });

    it('setLookupConfig 传 null 清除配置', () => {
      useRuleEditorStore.getState().setLookupConfig('lt_001', 'code', 'name');
      useRuleEditorStore.getState().setLookupConfig(null, null, null);
      const config = useRuleEditorStore.getState().config;
      expect(config.lookup_table_id).toBeNull();
      expect(config.lookup_key_field).toBeNull();
      expect(config.lookup_value_field).toBeNull();
    });

    it('addLookupFallback 添加查找回退', () => {
      useRuleEditorStore.getState().addLookupFallback();
      const fallbacks = useRuleEditorStore.getState().config.lookup_fallbacks;
      expect(fallbacks).toHaveLength(1);
      expect(fallbacks[0].condition_operator).toBe('eq');
    });

    it('removeLookupFallback 按 ID 删除', () => {
      useRuleEditorStore.getState().addLookupFallback();
      useRuleEditorStore.getState().addLookupFallback();
      const fallbacks = useRuleEditorStore.getState().config.lookup_fallbacks;
      const firstId = fallbacks[0].id;

      useRuleEditorStore.getState().removeLookupFallback(firstId);
      expect(useRuleEditorStore.getState().config.lookup_fallbacks).toHaveLength(1);
    });

    it('updateLookupFallback 更新回退属性', () => {
      useRuleEditorStore.getState().addLookupFallback();
      const fbId = useRuleEditorStore.getState().config.lookup_fallbacks[0].id;

      useRuleEditorStore.getState().updateLookupFallback(fbId, {
        condition_field: 'type',
        condition_operator: 'contains',
        condition_value: 'VIP',
        fallback_value: '高级',
      });

      const fb = useRuleEditorStore.getState().config.lookup_fallbacks[0];
      expect(fb.condition_field).toBe('type');
      expect(fb.condition_operator).toBe('contains');
      expect(fb.condition_value).toBe('VIP');
      expect(fb.fallback_value).toBe('高级');
    });
  });

  // ============ 公式和默认值 ============

  describe('公式和默认值', () => {
    beforeEach(() => {
      useRuleEditorStore.getState().openEditor();
    });

    it('setFormulaExpression 设置公式表达式', () => {
      useRuleEditorStore.getState().setFormulaExpression('a + b * c');
      expect(useRuleEditorStore.getState().config.formula_expression).toBe('a + b * c');
    });

    it('setFormulaExpression 传 null 清除公式', () => {
      useRuleEditorStore.getState().setFormulaExpression('a + b');
      useRuleEditorStore.getState().setFormulaExpression(null);
      expect(useRuleEditorStore.getState().config.formula_expression).toBeNull();
    });

    it('setDefaultResult 设置默认值', () => {
      useRuleEditorStore.getState().setDefaultResult(0);
      expect(useRuleEditorStore.getState().config.default_result).toBe(0);

      useRuleEditorStore.getState().setDefaultResult('N/A');
      expect(useRuleEditorStore.getState().config.default_result).toBe('N/A');

      useRuleEditorStore.getState().setDefaultResult(null);
      expect(useRuleEditorStore.getState().config.default_result).toBeNull();
    });
  });
});
