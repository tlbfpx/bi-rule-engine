import { Button, Select, Input, Space, Tooltip, Typography } from 'antd';
import {
  DeleteOutlined, PlusOutlined, HolderOutlined,
} from '@ant-design/icons';
import { useRuleEditorStore } from '../../stores/ruleStore';
import OperatorSelect from '../../components/OperatorSelect';
import FieldSelect from '../../components/FieldSelect';
import type { ConditionGroup, OperatorType } from '../../types';
import { LOGIC_OPTIONS, RESULT_TYPE_OPTIONS } from '../../utils/ruleLabels';

interface Props {
  group: ConditionGroup;
  index: number;
}

export default function ConditionGroupCard({ group }: Props) {
  const { updateConditionGroup, removeConditionGroup, addConditionRow, removeConditionRow, updateConditionRow } =
    useRuleEditorStore();

  const handleAddRow = () => addConditionRow(group.id);
  const handleRemoveRow = (rowId: string) => removeConditionRow(group.id, rowId);

  const needsValueInput = (op: OperatorType) =>
    !['is_null', 'is_not_null'].includes(op);

  return (
    <div className="condition-group-card">
      {/* Header */}
      <div className="condition-group-header">
        <Space>
          <HolderOutlined style={{ cursor: 'grab', color: '#999' }} />
          <Typography.Text strong>
            条件组 #{group.priority}
          </Typography.Text>
          <Select
            value={group.logic}
            onChange={(v) => updateConditionGroup(group.id, { logic: v })}
            options={LOGIC_OPTIONS}
            size="small"
            style={{ width: 140 }}
          />
        </Space>
        <Space>
          <Tooltip title="删除条件组">
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => removeConditionGroup(group.id)}
            />
          </Tooltip>
        </Space>
      </div>

      {/* Condition Rows */}
      <div>
        {group.rows.map((row, rowIdx) => (
          <div key={row.id} className="condition-row">
            <Typography.Text type="secondary" style={{ width: 40, flexShrink: 0 }}>
              {rowIdx === 0 ? '当' : group.logic}
            </Typography.Text>
            <FieldSelect
              value={row.field}
              onChange={(v) => updateConditionRow(group.id, row.id, { field: v })}
              placeholder="字段名"
              style={{ width: 180 }}
            />
            <OperatorSelect
              value={row.operator}
              onChange={(v) => updateConditionRow(group.id, row.id, { operator: v })}
              style={{ width: 150 }}
            />
            {needsValueInput(row.operator) && (
              <Input
                value={String(row.value ?? '')}
                onChange={(e) => updateConditionRow(group.id, row.id, { value: e.target.value })}
                placeholder={
                  row.operator === 'in' ? '用逗号分隔多个值' :
                  row.operator === 'between' ? '用逗号分隔起止值' : '输入值'
                }
                style={{ flex: 1 }}
              />
            )}
            <Button
              size="small"
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleRemoveRow(row.id)}
              disabled={group.rows.length <= 1}
            />
          </div>
        ))}
        <div style={{ padding: '8px 16px' }}>
          <Button size="small" type="dashed" icon={<PlusOutlined />} onClick={handleAddRow} block>
            添加条件行
          </Button>
        </div>
      </div>

      {/* Result */}
      <div style={{ padding: '8px 16px', borderTop: '1px solid #f0f0f0', background: '#fafafa', borderRadius: '0 0 8px 8px' }}>
        <Space>
          <Typography.Text type="secondary">则结果为：</Typography.Text>
          <Select
            value={group.result_type}
            onChange={(v) => updateConditionGroup(group.id, { result_type: v })}
            options={RESULT_TYPE_OPTIONS}
            size="small"
            style={{ width: 120 }}
          />
          {group.result_type === 'constant' && (
            <Input
              value={String(group.result_value ?? '')}
              onChange={(e) => updateConditionGroup(group.id, { result_value: e.target.value })}
              placeholder="结果值"
              size="small"
              style={{ width: 160 }}
            />
          )}
          {group.result_type === 'field_value' && (
            <FieldSelect
              value={String(group.result_value ?? '')}
              onChange={(v) => updateConditionGroup(group.id, { result_value: v })}
              placeholder="选择字段"
              style={{ width: 180 }}
            />
          )}
        </Space>
      </div>
    </div>
  );
}
