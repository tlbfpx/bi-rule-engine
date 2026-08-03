import { Button, Select, Input, Space, Typography, Empty } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext, verticalListSortingStrategy, useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useRuleEditorStore } from '../../stores/ruleStore';
import ConditionGroupCard from './ConditionGroup';
import type { ConditionGroup } from '../../types';

function SortableGroup({ group, ruleSetFields }: { group: ConditionGroup; ruleSetFields?: string[] }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: group.id });
  const style = { transform: CSS.Transform.toString(transform), transition };
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <ConditionGroupCard group={group} ruleSetFields={ruleSetFields} />
    </div>
  );
}

interface ConditionBuilderProps {
  ruleSetFields?: string[];
}

export default function ConditionBuilder({ ruleSetFields }: ConditionBuilderProps) {
  const { config, addConditionGroup, reorderConditionGroups, setDefaultResult } = useRuleEditorStore();

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const groups = config.conditions;
    const oldIdx = groups.findIndex((g) => g.id === active.id);
    const newIdx = groups.findIndex((g) => g.id === over.id);
    if (oldIdx !== -1 && newIdx !== -1) {
      reorderConditionGroups(oldIdx, newIdx);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          从上到下匹配，命中即停止
        </Typography.Text>
      </div>

      {config.conditions.length === 0 ? (
        <Empty description="暂无条件组" style={{ padding: '24px 0' }} />
      ) : (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={config.conditions.map((g) => g.id)} strategy={verticalListSortingStrategy}>
            {config.conditions.map((group) => (
              <SortableGroup key={group.id} group={group} ruleSetFields={ruleSetFields} />
            ))}
          </SortableContext>
        </DndContext>
      )}

      <Button
        type="dashed"
        icon={<PlusOutlined />}
        onClick={addConditionGroup}
        block
        style={{ marginTop: 8 }}
      >
        添加条件组
      </Button>

      {/* 默认结果 */}
      <div style={{ marginTop: 16, padding: '12px 16px', background: '#fff7e6', borderRadius: 8, border: '1px solid #ffd591' }}>
        <Space>
          <Typography.Text>所有条件都不匹配时：</Typography.Text>
          <Select
            value={typeof config.default_result === 'string' && ['keep_original', ''].includes(config.default_result as string) ? 'keep_original' : 'custom'}
            onChange={(v) => {
              if (v === 'keep_original') setDefaultResult('keep_original');
              else setDefaultResult(null);
            }}
            options={[
              { value: 'keep_original', label: '保持原值' },
              { value: 'custom', label: '指定默认值' },
            ]}
            size="small"
            style={{ width: 130 }}
          />
          {typeof config.default_result !== 'string' || config.default_result !== 'keep_original' ? (
            <Input
              value={config.default_result ? String(config.default_result) : ''}
              onChange={(e) => setDefaultResult(e.target.value)}
              placeholder="默认值"
              size="small"
              style={{ width: 160 }}
            />
          ) : null}
        </Space>
      </div>
    </div>
  );
}
