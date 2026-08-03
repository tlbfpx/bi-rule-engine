import { useState, useMemo, useCallback } from 'react';
import { Modal, Button, Table, Input, Space, Typography, Tag, Statistic, Row, Col, App } from 'antd';
import { PlusOutlined, DeleteOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { useTestRule, useRule } from '../../hooks/useRules';
import type { RuleConfig, CleaningStep } from '../../types';

interface Props {
  ruleId: string;
  open: boolean;
  onClose: () => void;
}

/**
 * 从规则配置中提取所有输入字段名（去重、排序）
 */
function extractInputFields(config: RuleConfig, fieldName: string, ruleType: string): string[] {
  const fields = new Set<string>();

  // 条件映射：从 conditions[].rows[].field 提取
  for (const cg of config.conditions || []) {
    for (const row of cg.rows || []) {
      if (row.field) fields.add(row.field);
    }
  }

  // 数据清洗：目标列本身 + cleaning_steps 中的 source_field
  if (ruleType === 'cleaning') {
    fields.add(fieldName);  // cleaning 规则操作的是自身列
    for (const step of config.cleaning_steps || []) {
      const s = step as CleaningStep;
      const sf = (s.params?.source_field as string) || (step as unknown as Record<string, unknown>).source_field;
      if (typeof sf === 'string' && sf) fields.add(sf);
    }
  }

  // 字典查���：lookup_key_field
  if (config.lookup_key_field) {
    fields.add(config.lookup_key_field);
  }

  // 公式计算：目标列 + 从 formula_expression 中提取标识符
  if (ruleType === 'computed' && config.formula_expression) {
    fields.add(fieldName);  // 公式计算结果列也是输入上下文的一部分
    const matches = config.formula_expression.matchAll(/\b([a-zA-Z_][a-zA-Z0-9_]*)\b/g);
    const formulaFields = new Set<string>();
    const keywords = new Set([
      'IF', 'AND', 'OR', 'NOT', 'IS', 'NULL', 'TRUE', 'FALSE',
      'COALESCE', 'ROUND', 'SPLIT', 'CONTAINS', 'ABS', 'UPPER', 'LOWER',
      'LEN', 'LEFT', 'RIGHT', 'MID', 'TRIM', 'CONCAT', 'REPLACE',
      'INT', 'FLOAT', 'STR', 'SUM', 'MIN', 'MAX', 'AVG', 'COUNT',
    ]);
    for (const m of matches) {
      const name = m[1];
      if (!keywords.has(name.toUpperCase()) && name.length > 1) {
        formulaFields.add(name);
      }
    }
    for (const f of formulaFields) {
      fields.add(f);
    }
  }

  // 如果没有提取到任何字段，返回目标列名本身
  if (fields.size === 0) {
    return [fieldName || 'value'];
  }

  return Array.from(fields).sort();
}

export default function RuleTestModal({ ruleId, open, onClose }: Props) {
  const { message } = App.useApp();
  const testRule = useTestRule();
  const { data: rule } = useRule(open ? ruleId : null);

  // 动态提取输入字段
  const inputFields = useMemo(() => {
    if (!rule?.config) return ['field1', 'field2'];
    return extractInputFields(rule.config, rule.field_name, rule.rule_type);
  }, [rule?.config, rule?.field_name, rule?.rule_type]);

  // 用实际字段名初始化空行
  const makeEmptyRow = (): Record<string, unknown> => {
    const row: Record<string, unknown> = {};
    for (const f of inputFields) row[f] = '';
    return row;
  };

  const [testRows, setTestRows] = useState<Record<string, unknown>[]>([makeEmptyRow()]);
  const [result, setResult] = useState<{
    results: { row_index: number; input_data: Record<string, unknown>; output_value: unknown; status: string }[];
    summary: { total: number; matched: number; defaulted: number; errors: number };
  } | null>(null);

  // 打开/关闭弹窗时重置状态
  const handleClose = () => {
    setResult(null);
    setTestRows([makeEmptyRow()]);
    onClose();
  };

  const handleAddRow = () => {
    setTestRows([...testRows, makeEmptyRow()]);
  };

  const handleRemoveRow = useCallback((idx: number) => {
    setTestRows((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const handleCellChange = useCallback((rowIdx: number, field: string, value: string) => {
    setTestRows((prev) => {
      const updated = [...prev];
      updated[rowIdx] = { ...updated[rowIdx], [field]: value };
      return updated;
    });
  }, []);

  const handleRunTest = async () => {
    if (testRows.length === 0) {
      message.warning('请添加测试数据');
      return;
    }
    // 检查是否有空字段名
    if (inputFields.length === 0) {
      message.warning('无法解析规则的输入字段');
      return;
    }
    try {
      const res = await testRule.mutateAsync({ id: ruleId, data: { test_rows: testRows } });
      setResult(res);
    } catch {
      // 错误已在拦截器处理
    }
  };

  // 动态生成输入列
  const inputColumns = useMemo(() => {
    const cols: Array<{
      title: string;
      dataIndex?: string;
      width?: number;
      render?: (_: unknown, record: Record<string, unknown>, idx: number) => React.ReactNode;
    }> = [
      { title: '#', width: 50, render: (_: unknown, __: unknown, idx: number) => idx + 1 },
    ];

    for (const field of inputFields) {
      cols.push({
        title: field,
        dataIndex: field,
        render: (_: unknown, record: Record<string, unknown>, idx: number) => (
          <Input
            size="small"
            value={String(record[field] ?? '')}
            onChange={(e) => handleCellChange(idx, field, e.target.value)}
            bordered={false}
            style={{ padding: 0 }}
          />
        ),
      });
    }

    cols.push({
      title: '',
      width: 50,
      render: (_: unknown, __: unknown, idx: number) => (
        <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => handleRemoveRow(idx)} />
      ),
    });

    return cols;
  }, [inputFields, handleCellChange, handleRemoveRow]);

  const resultColumns = [
    { title: '#', width: 50, render: (_: unknown, __: unknown, idx: number) => idx + 1 },
    ...inputFields.map((field) => ({
      title: field,
      dataIndex: field,
      render: (_: unknown, record: Record<string, unknown>) => {
        const inputData = record.input_data as Record<string, unknown> | undefined;
        return String(inputData?.[field] ?? '-');
      },
    })),
    {
      title: '输出值',
      dataIndex: 'output_value',
      render: (v: unknown) => String(v ?? '-'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (s: string) => {
        const colorMap: Record<string, string> = { matched: 'green', defaulted: 'orange', error: 'red' };
        const labelMap: Record<string, string> = { matched: '命中', defaulted: '默认值', error: '错误' };
        return <Tag color={colorMap[s] || 'default'}>{labelMap[s] || s}</Tag>;
      },
    },
  ];

  return (
    <Modal
      title={`规则测试 — ${rule?.field_name || ruleId}`}
      open={open}
      onCancel={handleClose}
      width={Math.max(900, 200 + inputFields.length * 160)}
      footer={null}
      destroyOnHidden
    >
      <div style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 12, justifyContent: 'space-between', width: '100%' }}>
          <Space>
            <Typography.Text strong>测试数据</Typography.Text>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              （输入字段：{inputFields.join('、')}）
            </Typography.Text>
          </Space>
          <Space>
            <Button size="small" icon={<PlusOutlined />} onClick={handleAddRow}>
              添加行
            </Button>
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={handleRunTest}
              loading={testRule.isPending}
            >
              执行测试
            </Button>
          </Space>
        </Space>
        <Table
          rowKey={(_, idx) => String(idx)}
          columns={inputColumns}
          dataSource={testRows}
          pagination={false}
          size="small"
          bordered
          scroll={{ x: 'max-content' }}
        />
      </div>

      {result && (
        <div>
          <Typography.Text strong style={{ display: 'block', marginBottom: 12 }}>测试结果</Typography.Text>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Statistic title="总行数" value={result.summary.total} />
            </Col>
            <Col span={6}>
              <Statistic title="命中" value={result.summary.matched} styles={{ content: { color: '#52c41a' } }} />
            </Col>
            <Col span={6}>
              <Statistic title="默认值" value={result.summary.defaulted} styles={{ content: { color: '#faad14' } }} />
            </Col>
            <Col span={6}>
              <Statistic title="错误" value={result.summary.errors} styles={{ content: { color: '#ff4d4f' } }} />
            </Col>
          </Row>
          <Table
            rowKey={(_, idx) => String(idx)}
            columns={resultColumns}
            dataSource={result.results}
            pagination={false}
            size="small"
            bordered
            scroll={{ x: 'max-content' }}
          />
        </div>
      )}
    </Modal>
  );
}
