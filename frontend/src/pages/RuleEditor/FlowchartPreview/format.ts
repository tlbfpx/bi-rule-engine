/**
 * 流程图节点文案格式化纯函数。
 */
import type { ConditionRow, CleaningStep } from '../../../types';
import {
  OPERATOR_LABEL,
  CLEANING_ACTION_LABEL,
  NO_VALUE_OPERATORS,
} from '../../../utils/ruleLabels';

/** 单值/数组/对象值的可读化与截断。 */
export function formatValue(value: unknown, maxLen = 24): string {
  if (value === null || value === undefined) return 'null';
  if (Array.isArray(value)) {
    const s = `[${value.map((v) => formatScalar(v)).join(', ')}]`;
    return truncate(s, maxLen);
  }
  if (typeof value === 'object') {
    return truncate(JSON.stringify(value), maxLen);
  }
  return truncate(formatScalar(value), maxLen);
}

function formatScalar(v: unknown): string {
  if (v === null || v === undefined) return 'null';
  return String(v);
}

function truncate(s: string, maxLen: number): string {
  return s.length > maxLen ? `${s.slice(0, maxLen)}…` : s;
}

/** 一行条件 → "字段 运算符 值"（is_null/is_not_null 无值）。 */
export function formatConditionRow(row: ConditionRow, maxLen = 28): string {
  const field = row.field?.trim() || '(未选择字段)';
  const opLabel = OPERATOR_LABEL[row.operator] || row.operator;
  if (NO_VALUE_OPERATORS.has(row.operator)) return `${field} ${opLabel}`;
  return `${field} ${opLabel} ${formatValue(row.value, maxLen)}`;
}

/** 逻辑连接词（用于多行条件之间的连接显示）。 */
export function joinLogicWord(logic: 'AND' | 'OR'): string {
  return logic === 'AND' ? '且' : '或';
}

/** 清洗步骤 → 副标题（参数摘要）。 */
export function formatCleaningParams(step: CleaningStep): string {
  const p = step.params || {};
  switch (step.action) {
    case 'fill_null':
      return `填充值: ${formatValue(p.fill_value)}`;
    case 'replace_string':
      return `${formatValue(p.old)} → ${formatValue(p.new)}`;
    case 'regex_extract':
      return `pattern: ${formatValue(p.pattern, 40)}`;
    case 'trim':
      return '(无参数)';
    case 'case_convert':
      return `模式: ${p.mode === 'lower' ? '转小写' : '转大写'}`;
    default:
      return CLEANING_ACTION_LABEL[step.action] || step.action;
  }
}
