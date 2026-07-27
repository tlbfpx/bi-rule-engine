import { Typography } from 'antd';
import Editor from '@monaco-editor/react';
import { useRuleEditorStore } from '../../stores/ruleStore';

const BUILTIN_FUNCTIONS = [
  'SPLIT(str, delimiter, index)', 'COALESCE(...values)', 'ROUND(num, decimals)',
  'REPLACE(str, old, new)', 'UPPER(str)', 'LOWER(str)', 'CONCAT(...strs)',
  'IF(cond, true_val, false_val)', 'ABS(num)', 'CEIL(num)', 'FLOOR(num)',
  'LENGTH(str)', 'TRIM(str)', 'SUBSTR(str, start, length)',
];

export default function FormulaEditor() {
  const { config, setFormulaExpression } = useRuleEditorStore();

  return (
    <div style={{ display: 'flex', gap: 12 }}>
      {/* 编辑器 */}
      <div style={{ flex: 1 }}>
        <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
          输入计算公式，支持引用其他字段和内置函数
        </Typography.Text>
        <Editor
          height="300px"
          defaultLanguage="plaintext"
          value={config.formula_expression || ''}
          onChange={(v) => setFormulaExpression(v || null)}
          theme="vs-light"
          options={{
            minimap: { enabled: false },
            lineNumbers: 'on',
            fontSize: 14,
            wordWrap: 'on',
            placeholder: '例如: IF(field_a > 100, ROUND(field_a * 0.1, 2), field_a)',
          }}
        />
      </div>

      {/* 函数参考 */}
      <div style={{ width: 240, flexShrink: 0 }}>
        <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>可用函数</Typography.Text>
        <div style={{ background: '#fafafa', borderRadius: 6, padding: 12, maxHeight: 280, overflow: 'auto' }}>
          {BUILTIN_FUNCTIONS.map((fn) => (
            <Typography.Text
              key={fn}
              code
              style={{ display: 'block', marginBottom: 6, fontSize: 12, cursor: 'pointer' }}
              title="点击复制"
            >
              {fn}
            </Typography.Text>
          ))}
        </div>
      </div>
    </div>
  );
}
