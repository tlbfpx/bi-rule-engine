/**
 * 纯函数：把规则配置 → ReactFlow 的 { nodes, edges }。
 * 每种规则类型一个 builder，语义对齐后端 app/engine/executor.py。
 */
import type { Node, Edge } from '@xyflow/react';
import { MarkerType } from '@xyflow/react';
import type {
  RuleType,
  RuleConfig,
  ConditionGroup,
} from '../../../types';
import {
  RESULT_TYPE_LABEL,
  DEFAULT_KEEP_ORIGINAL,
} from '../../../utils/ruleLabels';
import { formatConditionRow, formatCleaningParams, formatValue } from './format';
import { MAIN_X, OFFRAMP_X, OUTPUT_X, Y_STEP } from './layout';

/** 节点角色（决定着色） */
export type FlowRole = 'input' | 'condition' | 'process' | 'result';
export type FlowTone = 'default' | 'warning' | 'success' | 'danger';

/** 自定义节点 data 负载（nodes.tsx 消费） */
export interface FlowNodeData {
  role: FlowRole;
  ruleType: RuleType;
  title: string;
  subtitle?: string;
  subtitleMono?: boolean;
  badge?: string;
  badgeColor?: string; // antd Tag color name or hex
  lines?: string[];
  tone?: FlowTone;
  tip?: string;
}

export interface BuildGraphInput {
  ruleType: RuleType;
  fieldName: string;
  config: RuleConfig;
  dependsOn: string[];
  /** lookup 表 id → 表对象（含 name），用于显示人类可读表名 */
  tablesById?: Map<string, { name?: string }>;
}

const EMPTY = { nodes: [] as Node[], edges: [] as Edge[] };

function mkNode(
  id: string,
  role: FlowRole,
  ruleType: RuleType,
  fields: Omit<FlowNodeData, 'role' | 'ruleType'>,
  pos: { x: number; y: number },
): Node {
  return {
    id,
    type: 'flowNode',
    position: pos,
    data: { role, ruleType, ...fields } as unknown as Record<string, unknown>,
  };
}

function mkEdge(
  source: string,
  target: string,
  label?: string,
  animated = false,
  handles?: { source?: string; target?: string },
): Edge {
  return {
    id: `${source}->${target}`,
    source,
    target,
    label,
    animated,
    markerEnd: { type: MarkerType.ArrowClosed },
    sourceHandle: handles?.source,
    targetHandle: handles?.target,
  };
}

/** 稳定排序：按 priority 升序，相等保持原序 */
function sortByPriority<T extends { priority: number }>(arr: T[]): T[] {
  return arr
    .map((item, idx) => ({ item, idx }))
    .sort((a, b) => a.item.priority - b.item.priority || a.idx - b.idx)
    .map((x) => x.item);
}

// ── 结果文案 ──
function resultSubtitle(g: ConditionGroup): string {
  if (g.result_type === 'constant') return `→ 结果: 固定值 ${formatValue(g.result_value)}`;
  if (g.result_type === 'field_value') return `→ 结果: 取字段 ${g.result_value || '?'}`;
  return `→ 结果: ${RESULT_TYPE_LABEL.keep_original}`;
}
function resultOfframpTitle(g: ConditionGroup): string {
  if (g.result_type === 'constant') return formatValue(g.result_value, 18);
  if (g.result_type === 'field_value') return `[${g.result_value || '?'}]`;
  return '保持原值';
}
function defaultLabel(defaultResult: unknown): string {
  if (defaultResult === DEFAULT_KEEP_ORIGINAL) return '保持原值';
  if (defaultResult === null || defaultResult === undefined || defaultResult === '')
    return 'null';
  return formatValue(defaultResult);
}

// ───────────────────────── mapping ─────────────────────────
function buildMapping(fieldName: string, config: RuleConfig, ruleType: RuleType) {
  const groups = sortByPriority(config.conditions || []);
  if (groups.length === 0) return EMPTY;
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  nodes.push(
    mkNode('in', 'input', ruleType, { title: `输入: ${fieldName || '目标字段'}` }, { x: MAIN_X, y: 0 }),
  );
  edges.push(mkEdge('in', `g-${groups[0].id}`, undefined, true));

  groups.forEach((g, i) => {
    const y = (i + 1) * Y_STEP;
    nodes.push(
      mkNode(
        `g-${g.id}`,
        'condition',
        ruleType,
        {
          title: `条件组 #${g.priority}`,
          badge: g.logic === 'AND' ? '全部满足' : '任一满足',
          badgeColor: g.logic === 'AND' ? 'blue' : 'orange',
          lines: (g.rows || []).map((r) => formatConditionRow(r)),
          subtitle: resultSubtitle(g),
        },
        { x: MAIN_X, y },
      ),
    );
    // 「是」分支 → 右侧结果终点
    nodes.push(
      mkNode(
        `gr-${g.id}`,
        'result',
        ruleType,
        { title: resultOfframpTitle(g), subtitle: '命中', tone: 'success' },
        { x: OFFRAMP_X, y },
      ),
    );
    edges.push(mkEdge(`g-${g.id}`, `gr-${g.id}`, '是', true, { source: 'right', target: 'left' }));

    if (i < groups.length - 1) {
      edges.push(mkEdge(`g-${g.id}`, `g-${groups[i + 1].id}`, '否'));
    }
  });

  const dy = (groups.length + 1) * Y_STEP;
  nodes.push(
    mkNode(
      'def',
      'result',
      ruleType,
      { title: '默认', subtitle: defaultLabel(config.default_result), tone: 'warning' },
      { x: MAIN_X, y: dy },
    ),
  );
  edges.push(mkEdge(`g-${groups[groups.length - 1].id}`, 'def', '否'));

  return { nodes, edges };
}

// ───────────────────────── cleaning ─────────────────────────
function buildCleaning(fieldName: string, config: RuleConfig, ruleType: RuleType) {
  const steps = config.cleaning_steps || [];
  if (steps.length === 0) return EMPTY;
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  nodes.push(
    mkNode('in', 'input', ruleType, { title: `输入: ${fieldName || '目标字段'}` }, { x: MAIN_X, y: 0 }),
  );
  steps.forEach((s, i) => {
    nodes.push(
      mkNode(
        `s-${s.id}`,
        'process',
        ruleType,
        { title: `步骤 ${i + 1}`, subtitle: formatCleaningParams(s) },
        { x: MAIN_X, y: (i + 1) * Y_STEP },
      ),
    );
  });
  const oy = (steps.length + 1) * Y_STEP;
  nodes.push(
    mkNode('out', 'result', ruleType, { title: `输出: ${fieldName || '目标字段'}`, tone: 'success' }, { x: MAIN_X, y: oy }),
  );

  edges.push(mkEdge('in', `s-${steps[0].id}`, undefined, true));
  for (let i = 0; i < steps.length - 1; i++) {
    edges.push(mkEdge(`s-${steps[i].id}`, `s-${steps[i + 1].id}`, undefined, true));
  }
  edges.push(mkEdge(`s-${steps[steps.length - 1].id}`, 'out', undefined, true));
  return { nodes, edges };
}

// ───────────────────────── lookup ─────────────────────────
function buildLookup(fieldName: string, config: RuleConfig, ruleType: RuleType, tablesById?: Map<string, { name?: string }>) {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  nodes.push(
    mkNode(
      'in',
      'input',
      ruleType,
      { title: `输入: ${fieldName || '目标字段'}`, subtitle: `查找键: ${config.lookup_key_field || '-'}` },
      { x: MAIN_X, y: 0 },
    ),
  );

  // 字典表节点
  const tableId = config.lookup_table_id;
  const tableName = tableId ? tablesById?.get(tableId)?.name : undefined;
  if (!tableId) {
    nodes.push(
      mkNode(
        'table',
        'process',
        ruleType,
        { title: '未配置字典表', subtitle: '请先选择映射表', tone: 'warning' },
        { x: MAIN_X, y: Y_STEP },
      ),
    );
    edges.push(mkEdge('in', 'table', undefined, true));
    return { nodes, edges };
  }

  nodes.push(
    mkNode(
      'table',
      'process',
      ruleType,
      {
        title: '字典表查找',
        subtitle: `${tableName || tableId.slice(0, 8)} · 取值列: ${config.lookup_value_field || '?'}`,
      },
      { x: MAIN_X, y: Y_STEP },
    ),
  );
  edges.push(mkEdge('in', 'table', undefined, true));

  // 命中分支
  nodes.push(
    mkNode(
      'hit',
      'result',
      ruleType,
      { title: '命中', subtitle: `取值: ${config.lookup_value_field || '?'}`, tone: 'success' },
      { x: OUTPUT_X, y: Y_STEP },
    ),
  );
  edges.push(mkEdge('table', 'hit', '命中', true));

  // 兜底链（未命中时按顺序匹配）
  const fallbacks = config.lookup_fallbacks || [];
  if (fallbacks.length === 0) {
    nodes.push(
      mkNode('null', 'result', ruleType, { title: '未命中', subtitle: 'null', tone: 'danger' }, { x: MAIN_X, y: 2 * Y_STEP }),
    );
    edges.push(mkEdge('table', 'null', '未命中'));
    return { nodes, edges };
  }

  fallbacks.forEach((fb, i) => {
    nodes.push(
      mkNode(
        `f-${fb.id}`,
        'condition',
        ruleType,
        {
          title: `兜底 #${i + 1}`,
          lines: [
            `${fb.condition_field || '(未选择)'} 满足条件 → ${formatValue(fb.fallback_value, 16)}`,
          ],
        },
        { x: MAIN_X, y: (i + 2) * Y_STEP },
      ),
    );
    if (i === 0) edges.push(mkEdge('table', `f-${fb.id}`, '未命中'));
    else edges.push(mkEdge(`f-${fallbacks[i - 1].id}`, `f-${fb.id}`, '否'));
  });
  const ny = (fallbacks.length + 2) * Y_STEP;
  nodes.push(
    mkNode('null', 'result', ruleType, { title: '未命中兜底', subtitle: 'null', tone: 'danger' }, { x: MAIN_X, y: ny }),
  );
  edges.push(mkEdge(`f-${fallbacks[fallbacks.length - 1].id}`, 'null', '否'));

  return { nodes, edges };
}

// ───────────────────────── computed ─────────────────────────
function buildComputed(fieldName: string, config: RuleConfig, ruleType: RuleType, dependsOn: string[]) {
  const formula = config.formula_expression;
  if (!formula) return EMPTY;
  const deps = dependsOn || [];
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  const many = deps.length > 4;
  const inputCount = many ? 1 : Math.max(deps.length, 1);
  const midY = ((inputCount - 1) * Y_STEP) / 2;

  if (many) {
    nodes.push(
      mkNode('deps', 'input', ruleType, { title: `输入字段 (${deps.length})`, tip: deps.join(', ') }, { x: MAIN_X, y: 0 }),
    );
    edges.push(mkEdge('deps', 'formula', undefined, false));
  } else if (deps.length === 0) {
    nodes.push(
      mkNode('deps', 'input', ruleType, { title: '(未配置依赖字段)', tone: 'warning' }, { x: MAIN_X, y: 0 }),
    );
    edges.push(mkEdge('deps', 'formula', undefined, false));
  } else {
    deps.forEach((d, i) => {
      nodes.push(mkNode(`dep-${i}`, 'input', ruleType, { title: d }, { x: MAIN_X, y: i * Y_STEP }));
      edges.push(mkEdge(`dep-${i}`, 'formula', undefined, false));
    });
  }

  nodes.push(
    mkNode(
      'formula',
      'process',
      ruleType,
      { title: '公式计算', subtitle: formula, subtitleMono: true, tip: formula },
      { x: OFFRAMP_X, y: midY },
    ),
  );
  nodes.push(
    mkNode('out', 'result', ruleType, { title: `输出: ${fieldName || '目标字段'}`, tone: 'success' }, { x: OUTPUT_X, y: midY }),
  );
  edges.push(mkEdge('formula', 'out', undefined, true));

  return { nodes, edges };
}

// ───────────────────────── 分发 ─────────────────────────
export function buildGraph(input: BuildGraphInput): { nodes: Node[]; edges: Edge[] } {
  const { ruleType, fieldName, config, dependsOn, tablesById } = input;
  switch (ruleType) {
    case 'mapping':
      return buildMapping(fieldName, config, ruleType);
    case 'cleaning':
      return buildCleaning(fieldName, config, ruleType);
    case 'lookup':
      return buildLookup(fieldName, config, ruleType, tablesById);
    case 'computed':
      return buildComputed(fieldName, config, ruleType, dependsOn);
    default:
      return EMPTY;
  }
}
