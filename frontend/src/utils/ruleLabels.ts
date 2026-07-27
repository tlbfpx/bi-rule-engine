/**
 * 规则相关标签 / 颜色单一来源。
 *
 * 历史上这些映射散落在 components/OperatorSelect.tsx、pages/RuleEditor/BasicInfoForm.tsx、
 * CleaningConfig.tsx、ConditionGroup.tsx、pages/RuleList/index.tsx 等多处重复定义。
 * 新代码统一从这里导入；既有调用点的迁移留作后续独立 PR。
 */
import type {
  RuleType,
  OperatorType,
  ConditionGroup,
  CleaningStep,
} from '../types';

/** 规则类型 → antd Tag 颜色 + 中文标签（与 RuleList 的 RULE_TYPE_TAG 一致） */
export const RULE_TYPE_TAG: Record<RuleType, { color: string; label: string }> = {
  mapping: { color: 'blue', label: '条件映射' },
  cleaning: { color: 'green', label: '数据清洗' },
  lookup: { color: 'orange', label: '字典查找' },
  computed: { color: 'purple', label: '公式计算' },
};

/** 规则类型 → 十六进制主色（与 DependencyDAG typeColors 一致） */
export const RULE_TYPE_HEX: Record<RuleType, string> = {
  mapping: '#1677ff',
  cleaning: '#52c41a',
  lookup: '#fa8c16',
  computed: '#722ed1',
};

/** 运算符 → 中文标签（与 components/OperatorSelect.tsx 一致） */
export const OPERATOR_LABEL: Record<OperatorType, string> = {
  eq: '等于 (=)',
  neq: '不等于 (≠)',
  contains: '包含',
  matches: '正则匹配',
  starts_with: '开头是',
  ends_with: '结尾是',
  in: '在列表中',
  between: '在范围内',
  gt: '大于 (>)',
  gte: '大于等于 (≥)',
  lt: '小于 (<)',
  lte: '小于等于 (≤)',
  is_null: '为空',
  is_not_null: '不为空',
};

/** 清洗动作 → 中文标签（与 CleaningConfig ACTION_OPTIONS 一致） */
export const CLEANING_ACTION_LABEL: Record<CleaningStep['action'], string> = {
  fill_null: '空值填充',
  replace_string: '字符串替换',
  regex_extract: '正则提取',
  trim: '去除首尾空格',
  case_convert: '大小写转换',
};

/** 条件组结果类型 → 中文标签（与 ConditionGroup RESULT_TYPE_OPTIONS 一致） */
export const RESULT_TYPE_LABEL: Record<ConditionGroup['result_type'], string> = {
  constant: '固定值',
  field_value: '取字段值',
  keep_original: '保持原值',
};

/** default_result 字符串哨兵：表示保持目标字段原值 */
export const DEFAULT_KEEP_ORIGINAL = 'keep_original';

/** 无需取值的运算符（条件行不渲染 value 输入）。集中定义避免多处重复判断。 */
export const NO_VALUE_OPERATORS: ReadonlySet<OperatorType> = new Set([
  'is_null',
  'is_not_null',
]);
