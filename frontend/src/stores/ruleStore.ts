import { create } from 'zustand';
import type { ConditionGroup, CleaningStep, LookupFallback, RuleType, RuleConfig } from '../types';

export const generateId = () =>
  typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `temp_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

const defaultConfig = (): RuleConfig => ({
  conditions: [],
  cleaning_steps: [],
  lookup_table_id: null,
  lookup_key_field: null,
  lookup_value_field: null,
  lookup_fallbacks: [],
  formula_expression: null,
  default_result: null,
});

const emptyConditionGroup = (priority: number): ConditionGroup => ({
  id: generateId(),
  priority,
  logic: 'AND',
  rows: [{ id: generateId(), field: '', operator: 'eq', value: '' }],
  result_type: 'constant',
  result_value: '',
});

interface RuleEditorState {
  // 编辑器是否打开
  open: boolean;
  // 当前编辑的规则 ID（null = 新建）
  editingId: string | null;
  // 当前规则集 ID
  ruleSetId: string | null;
  // 基本信息
  fieldName: string;
  fieldLabel: string;
  ruleType: RuleType;
  priority: number;
  enabled: boolean;
  description: string;
  dependsOn: string[];
  // 规则配置
  config: RuleConfig;
  // 数据画像上下文（来自上传文件的列信息，供编辑器使用）
  dataContext: {
    columnProfiles: Record<string, { distinct_count: number; top_values: unknown[]; sample_values: string[]; null_rate: number; dtype: string }>;
    previewRows: Record<string, unknown>[];
    totalRows: number;
  } | null;
  setDataContext: (ctx: RuleEditorState['dataContext']) => void;

  // 操作
  openEditor: (rule?: Partial<{
    id: string;
    rule_set_id: string | null;
    field_name: string;
    field_label: string | null;
    rule_type: RuleType;
    priority: number;
    enabled: boolean;
    description: string | null;
    depends_on: string[];
    config: RuleConfig;
  }>) => void;
  closeEditor: () => void;
  resetEditor: () => void;

  // 基本信息
  setFieldName: (v: string) => void;
  setFieldLabel: (v: string) => void;
  setRuleType: (v: RuleType) => void;
  setPriority: (v: number) => void;
  setEnabled: (v: boolean) => void;
  setDescription: (v: string) => void;
  setDependsOn: (v: string[]) => void;

  // 条件组操作
  addConditionGroup: () => void;
  removeConditionGroup: (groupId: string) => void;
  updateConditionGroup: (groupId: string, updates: Partial<ConditionGroup>) => void;
  reorderConditionGroups: (fromIndex: number, toIndex: number) => void;

  // 条件行操作
  addConditionRow: (groupId: string) => void;
  removeConditionRow: (groupId: string, rowId: string) => void;
  updateConditionRow: (groupId: string, rowId: string, updates: Partial<ConditionGroup['rows'][0]>) => void;

  // 清洗步骤
  addCleaningStep: () => void;
  removeCleaningStep: (stepId: string) => void;
  updateCleaningStep: (stepId: string, updates: Partial<CleaningStep>) => void;

  // 查找配置
  setLookupConfig: (tableId: string | null, keyField: string | null, valueField: string | null) => void;
  addLookupFallback: () => void;
  removeLookupFallback: (fbId: string) => void;
  updateLookupFallback: (fbId: string, updates: Partial<LookupFallback>) => void;

  // 公式
  setFormulaExpression: (expr: string | null) => void;

  // 默认值
  setDefaultResult: (v: unknown) => void;
}

export const useRuleEditorStore = create<RuleEditorState>((set, get) => ({
  open: false,
  editingId: null,
  ruleSetId: null,
  fieldName: '',
  fieldLabel: '',
  ruleType: 'mapping',
  priority: 0,
  enabled: true,
  description: '',
  dependsOn: [],
  config: defaultConfig(),
  dataContext: null,

  openEditor: (rule?) => {
    if (rule?.id) {
      set({
        open: true,
        editingId: rule.id,
        ruleSetId: rule.rule_set_id || null,
        fieldName: rule.field_name || '',
        fieldLabel: rule.field_label || '',
        ruleType: rule.rule_type || 'mapping',
        priority: rule.priority ?? 0,
        enabled: rule.enabled ?? true,
        description: rule.description || '',
        dependsOn: rule.depends_on || [],
        config: rule.config || defaultConfig(),
      });
    } else {
      // 新建模式：保留当前 ruleSetId（可能从 RuleSetDetail 页面传入）
      const currentRuleSetId = rule?.rule_set_id || get().ruleSetId;
      set({
        open: true,
        editingId: null,
        ruleSetId: currentRuleSetId || null,
        fieldName: '',
        fieldLabel: '',
        ruleType: 'mapping',
        priority: 0,
        enabled: true,
        description: '',
        dependsOn: [],
        config: defaultConfig(),
      });
    }
  },

  closeEditor: () => set({ open: false }),

  resetEditor: () => set({
    open: false, editingId: null, ruleSetId: null, fieldName: '', fieldLabel: '', ruleType: 'mapping',
    priority: 0, enabled: true, description: '', dependsOn: [], config: defaultConfig(), dataContext: null,
  }),

  setDataContext: (ctx) => set({ dataContext: ctx }),

  setFieldName: (v) => set({ fieldName: v }),
  setFieldLabel: (v) => set({ fieldLabel: v }),
  setRuleType: (v) => set({ ruleType: v }),
  setPriority: (v) => set({ priority: v }),
  setEnabled: (v) => set({ enabled: v }),
  setDescription: (v) => set({ description: v }),
  setDependsOn: (v) => set({ dependsOn: v }),

  addConditionGroup: () => {
    const groups = get().config.conditions;
    const maxP = groups.length > 0 ? Math.max(...groups.map((g) => g.priority)) : 0;
    set({ config: { ...get().config, conditions: [...groups, emptyConditionGroup(maxP + 1)] } });
  },

  removeConditionGroup: (groupId) => {
    set({ config: { ...get().config, conditions: get().config.conditions.filter((g) => g.id !== groupId) } });
  },

  updateConditionGroup: (groupId, updates) => {
    set({
      config: {
        ...get().config,
        conditions: get().config.conditions.map((g) => (g.id === groupId ? { ...g, ...updates } : g)),
      },
    });
  },

  reorderConditionGroups: (fromIndex, toIndex) => {
    const groups = [...get().config.conditions];
    const [removed] = groups.splice(fromIndex, 1);
    groups.splice(toIndex, 0, removed);
    const reordered = groups.map((g, i) => ({ ...g, priority: i + 1 }));
    set({ config: { ...get().config, conditions: reordered } });
  },

  addConditionRow: (groupId) => {
    set({
      config: {
        ...get().config,
        conditions: get().config.conditions.map((g) =>
          g.id === groupId
            ? { ...g, rows: [...g.rows, { id: generateId(), field: '', operator: 'eq', value: '' }] }
            : g
        ),
      },
    });
  },

  removeConditionRow: (groupId, rowId) => {
    set({
      config: {
        ...get().config,
        conditions: get().config.conditions.map((g) =>
          g.id === groupId ? { ...g, rows: g.rows.filter((r) => r.id !== rowId) } : g
        ),
      },
    });
  },

  updateConditionRow: (groupId, rowId, updates) => {
    set({
      config: {
        ...get().config,
        conditions: get().config.conditions.map((g) =>
          g.id === groupId
            ? { ...g, rows: g.rows.map((r) => (r.id === rowId ? { ...r, ...updates } : r)) }
            : g
        ),
      },
    });
  },

  addCleaningStep: () => {
    set({
      config: {
        ...get().config,
        cleaning_steps: [
          ...get().config.cleaning_steps,
          { id: generateId(), action: 'fill_null', params: {} },
        ],
      },
    });
  },

  removeCleaningStep: (stepId) => {
    set({ config: { ...get().config, cleaning_steps: get().config.cleaning_steps.filter((s) => s.id !== stepId) } });
  },

  updateCleaningStep: (stepId, updates) => {
    set({
      config: {
        ...get().config,
        cleaning_steps: get().config.cleaning_steps.map((s) => (s.id === stepId ? { ...s, ...updates } : s)),
      },
    });
  },

  setLookupConfig: (tableId, keyField, valueField) => {
    set({ config: { ...get().config, lookup_table_id: tableId, lookup_key_field: keyField, lookup_value_field: valueField } });
  },

  addLookupFallback: () => {
    set({
      config: {
        ...get().config,
        lookup_fallbacks: [
          ...get().config.lookup_fallbacks,
          { id: generateId(), condition_field: '', condition_operator: 'eq', condition_value: '', fallback_value: '' },
        ],
      },
    });
  },

  removeLookupFallback: (fbId) => {
    set({ config: { ...get().config, lookup_fallbacks: get().config.lookup_fallbacks.filter((f) => f.id !== fbId) } });
  },

  updateLookupFallback: (fbId, updates) => {
    set({
      config: {
        ...get().config,
        lookup_fallbacks: get().config.lookup_fallbacks.map((f) => (f.id === fbId ? { ...f, ...updates } : f)),
      },
    });
  },

  setFormulaExpression: (expr) => set({ config: { ...get().config, formula_expression: expr } }),

  setDefaultResult: (v) => set({ config: { ...get().config, default_result: v } }),
}));
