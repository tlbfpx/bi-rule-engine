import { describe, it, expect } from 'vitest';
import { buildGraph } from './buildGraph';
import { formatValue, formatConditionRow } from './format';
import type { RuleConfig, ConditionGroup } from '../../../types';

const EMPTY_CONFIG: RuleConfig = {
  conditions: [],
  cleaning_steps: [],
  lookup_table_id: null,
  lookup_key_field: null,
  lookup_value_field: null,
  lookup_fallbacks: [],
  formula_expression: null,
  default_result: null,
};

function group(over: Partial<ConditionGroup>): ConditionGroup {
  return {
    id: over.id || 'g1',
    priority: over.priority ?? 1,
    logic: over.logic || 'AND',
    rows: over.rows || [],
    result_type: over.result_type || 'constant',
    result_value: over.result_value,
  };
}

describe('formatValue / formatConditionRow', () => {
  it('截断长数组', () => {
    expect(formatValue([1, 2, 3, 4, 5, 6])).toBe('[1, 2, 3, 4, 5, 6]');
    expect(formatValue([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 8)).toBe('[1, 2, 3…');
  });
  it('null → null', () => {
    expect(formatValue(null)).toBe('null');
    expect(formatValue(undefined)).toBe('null');
  });
  it('is_null 条件行不输出值', () => {
    expect(formatConditionRow({ id: 'r', field: 'foo', operator: 'is_null', value: null })).toBe(
      'foo 为空',
    );
  });
  it('未选字段时占位', () => {
    expect(formatConditionRow({ id: 'r', field: '', operator: 'eq', value: 'x' })).toContain(
      '(未选择字段)',
    );
  });
});

describe('buildGraph — mapping', () => {
  it('3 个条件组：节点/边数量与分支标签', () => {
    const cfg: RuleConfig = {
      ...EMPTY_CONFIG,
      default_result: '其他',
      conditions: [
        group({ id: 'a', priority: 1, rows: [{ id: 'r1', field: 'f', operator: 'eq', value: '1' }] }),
        group({ id: 'b', priority: 2, logic: 'OR', rows: [{ id: 'r2', field: 'f', operator: 'in', value: ['930000', '840000'] }] }),
        group({ id: 'c', priority: 3, rows: [{ id: 'r3', field: 'f', operator: 'is_null', value: null }] }),
      ],
    };
    const { nodes, edges } = buildGraph({ ruleType: 'mapping', fieldName: 'prod_class', config: cfg, dependsOn: [] });
    // 1 input + 3 condition + 3 offramp + 1 default = 8
    expect(nodes).toHaveLength(8);
    const labels = edges.map((e) => e.label).filter(Boolean);
    expect(labels.filter((l) => l === '是')).toHaveLength(3);
    expect(labels.filter((l) => l === '否')).toHaveLength(3);
    // offramp 边走 right→left
    const yesEdge = edges.find((e) => e.source === 'g-a' && e.target === 'gr-a');
    expect(yesEdge?.sourceHandle).toBe('right');
    expect(yesEdge?.targetHandle).toBe('left');
  });

  it('优先级乱序 → 按 priority 升序排列主干', () => {
    const cfg: RuleConfig = {
      ...EMPTY_CONFIG,
      default_result: null,
      conditions: [
        group({ id: 'lo', priority: 9, rows: [{ id: 'r', field: 'f', operator: 'eq', value: 'x' }] }),
        group({ id: 'hi', priority: 1, rows: [{ id: 'r', field: 'f', operator: 'eq', value: 'y' }] }),
      ],
    };
    const { edges } = buildGraph({ ruleType: 'mapping', fieldName: 'f', config: cfg, dependsOn: [] });
    // input 应先连到 hi（priority 1）
    expect(edges.some((e) => e.source === 'in' && e.target === 'g-hi')).toBe(true);
    // 否 落到 lo（priority 9）
    expect(edges.some((e) => e.source === 'g-hi' && e.target === 'g-lo' && e.label === '否')).toBe(true);
  });

  it('空条件 → 空', () => {
    const { nodes, edges } = buildGraph({ ruleType: 'mapping', fieldName: 'f', config: { ...EMPTY_CONFIG }, dependsOn: [] });
    expect(nodes).toHaveLength(0);
    expect(edges).toHaveLength(0);
  });

  it('default=keep_original → 默认节点显示保持原值', () => {
    const cfg: RuleConfig = {
      ...EMPTY_CONFIG,
      default_result: 'keep_original',
      conditions: [group({ id: 'a', priority: 1, rows: [{ id: 'r', field: 'f', operator: 'eq', value: '1' }] })],
    };
    const { nodes } = buildGraph({ ruleType: 'mapping', fieldName: 'f', config: cfg, dependsOn: [] });
    const def = nodes.find((n) => n.id === 'def');
    expect((def?.data as { subtitle?: string }).subtitle).toBe('保持原值');
  });
});

describe('buildGraph — cleaning', () => {
  it('4 步顺序流水线', () => {
    const cfg: RuleConfig = {
      ...EMPTY_CONFIG,
      cleaning_steps: [
        { id: 's1', action: 'fill_null', params: { fill_value: '972400' } },
        { id: 's2', action: 'replace_string', params: { old: 'a', new: 'b' } },
        { id: 's3', action: 'trim', params: {} },
        { id: 's4', action: 'case_convert', params: { mode: 'upper' } },
      ],
    };
    const { nodes, edges } = buildGraph({ ruleType: 'cleaning', fieldName: 'company', config: cfg, dependsOn: [] });
    expect(nodes.map((n) => n.id)).toEqual(['in', 's-s1', 's-s2', 's-s3', 's-s4', 'out']);
    // 链式：in→s1→s2→s3→s4→out
    const chain = edges.map((e) => `${e.source}->${e.target}`);
    expect(chain).toEqual(['in->s-s1', 's-s1->s-s2', 's-s2->s-s3', 's-s3->s-s4', 's-s4->out']);
  });

  it('空步骤 → 空', () => {
    const { nodes } = buildGraph({ ruleType: 'cleaning', fieldName: 'f', config: { ...EMPTY_CONFIG }, dependsOn: [] });
    expect(nodes).toHaveLength(0);
  });
});

describe('buildGraph — lookup', () => {
  it('表 + 2 兜底 → 命中/未命中分支与兜底链', () => {
    const cfg: RuleConfig = {
      ...EMPTY_CONFIG,
      lookup_table_id: 'lt1',
      lookup_key_field: 'card_name',
      lookup_value_field: 'seg',
      lookup_fallbacks: [
        { id: 'fb1', condition_field: 'prod_class', condition_operator: 'eq', condition_value: '集团体检', fallback_value: 'P10011' },
        { id: 'fb2', condition_field: 'prod_class', condition_operator: 'eq', condition_value: '团体体检', fallback_value: 'P10012' },
      ],
    };
    const tablesById = new Map([['lt1', { name: '卡映射表' }]]);
    const { nodes, edges } = buildGraph({ ruleType: 'lookup', fieldName: 'seg', config: cfg, dependsOn: [], tablesById });
    const ids = nodes.map((n) => n.id);
    expect(ids).toContain('in');
    expect(ids).toContain('table');
    expect(ids).toContain('hit');
    expect(ids).toContain('f-fb1');
    expect(ids).toContain('f-fb2');
    expect(ids).toContain('null');
    expect(edges.some((e) => e.source === 'table' && e.target === 'hit' && e.label === '命中')).toBe(true);
    expect(edges.some((e) => e.source === 'table' && e.target === 'f-fb1' && e.label === '未命中')).toBe(true);
    expect(edges.some((e) => e.source === 'f-fb2' && e.target === 'null' && e.label === '否')).toBe(true);
  });

  it('未配置字典表 → 占位节点', () => {
    const cfg: RuleConfig = { ...EMPTY_CONFIG, lookup_table_id: null };
    const { nodes, edges } = buildGraph({ ruleType: 'lookup', fieldName: 'f', config: cfg, dependsOn: [] });
    const tableNode = nodes.find((n) => n.id === 'table');
    expect((tableNode?.data as { title?: string }).title).toBe('未配置字典表');
    expect(edges).toHaveLength(1); // 仅 in→table
  });
});

describe('buildGraph — computed', () => {
  it('2 依赖 + 公式 → 输入汇聚到公式再到输出', () => {
    const cfg: RuleConfig = { ...EMPTY_CONFIG, formula_expression: 'a + b' };
    const { nodes, edges } = buildGraph({ ruleType: 'computed', fieldName: 'out', config: cfg, dependsOn: ['a', 'b'] });
    const ids = nodes.map((n) => n.id);
    expect(ids).toEqual(['dep-0', 'dep-1', 'formula', 'out']);
    expect(edges.some((e) => e.source === 'dep-0' && e.target === 'formula')).toBe(true);
    expect(edges.some((e) => e.source === 'dep-1' && e.target === 'formula')).toBe(true);
    expect(edges.some((e) => e.source === 'formula' && e.target === 'out')).toBe(true);
  });

  it('依赖 >4 → 折叠为单输入节点', () => {
    const cfg: RuleConfig = { ...EMPTY_CONFIG, formula_expression: 'x' };
    const { nodes } = buildGraph({ ruleType: 'computed', fieldName: 'o', config: cfg, dependsOn: ['a', 'b', 'c', 'd', 'e', 'f'] });
    const ids = nodes.map((n) => n.id);
    expect(ids).toEqual(['deps', 'formula', 'out']);
    const deps = nodes.find((n) => n.id === 'deps');
    expect((deps?.data as { title?: string }).title).toBe('输入字段 (6)');
  });

  it('无公式 → 空', () => {
    const { nodes } = buildGraph({ ruleType: 'computed', fieldName: 'o', config: { ...EMPTY_CONFIG }, dependsOn: ['a'] });
    expect(nodes).toHaveLength(0);
  });
});
