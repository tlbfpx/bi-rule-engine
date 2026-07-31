import type { ConditionGroup, ConditionRow, OperatorType } from '../types';

function matchRow(row: Record<string, unknown>, cond: ConditionRow): boolean {
  const raw = row[cond.field];
  const fieldVal = raw === null || raw === undefined ? null : String(raw);
  const condVal = cond.value === null || cond.value === undefined ? '' : String(cond.value);

  const op = cond.operator as OperatorType;

  switch (op) {
    case 'is_null':
      return fieldVal === null || fieldVal === '';
    case 'is_not_null':
      return fieldVal !== null && fieldVal !== '';
    case 'eq':
      return fieldVal === condVal;
    case 'neq':
      return fieldVal !== condVal;
    case 'contains':
      return fieldVal !== null && fieldVal.includes(condVal);
    case 'not_contains':
      return fieldVal === null || !fieldVal.includes(condVal);
    case 'starts_with':
      return fieldVal !== null && fieldVal.startsWith(condVal);
    case 'ends_with':
      return fieldVal !== null && fieldVal.endsWith(condVal);
    case 'in': {
      if (fieldVal === null) return false;
      const values = condVal.split(',').map((s) => s.trim());
      return values.includes(fieldVal);
    }
    case 'gt':
      return fieldVal !== null && Number(fieldVal) > Number(condVal);
    case 'gte':
      return fieldVal !== null && Number(fieldVal) >= Number(condVal);
    case 'lt':
      return fieldVal !== null && Number(fieldVal) < Number(condVal);
    case 'lte':
      return fieldVal !== null && Number(fieldVal) <= Number(condVal);
    case 'between': {
      if (fieldVal === null) return false;
      const [low, high] = condVal.split(',').map((s) => Number(s.trim()));
      const num = Number(fieldVal);
      return !isNaN(num) && num >= low && num <= high;
    }
    case 'matches':
      // 正则匹配：在前端预览中跳过（避免复杂正则引发异常）
      return false;
    default:
      return false;
  }
}

export function countMatches(
  group: ConditionGroup,
  previewRows: Record<string, unknown>[],
): number {
  if (!previewRows.length) return 0;
  if (!group.rows.length) return 0;
  // 过滤掉空字段的条件行（用户还没填完的）
  const validRows = group.rows.filter((r) => r.field);

  if (!validRows.length) return 0;

  const total = previewRows.length;
  let matches = 0;

  for (const row of previewRows) {
    if (group.logic === 'AND') {
      if (validRows.every((cond) => matchRow(row, cond))) {
        matches++;
      }
    } else {
      if (validRows.some((cond) => matchRow(row, cond))) {
        matches++;
      }
    }
  }

  return matches;
}

export function formatMatchCount(matched: number, previewRows: number, totalRows: number): string {
  if (!previewRows) return '';
  const pct = previewRows > 0 ? Math.round((matched / previewRows) * 100) : 0;
  const estimated = totalRows > 0 ? Math.round((matched / previewRows) * totalRows) : 0;
  if (!matched) return '0 行匹配';
  if (totalRows <= previewRows) return `${matched} 行匹配 (${pct}%)`;
  return `${estimated.toLocaleString()} 行匹配 (约 ${pct}%)`;
}
