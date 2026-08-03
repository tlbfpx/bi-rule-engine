import { useMemo, useState } from 'react';
import { Card, Typography, Spin, Empty, Tag, Space, Select } from 'antd';
import {
  ReactFlow, Background, Controls, MiniMap,
  Handle, Position,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useRules } from '../../hooks/useRules';
import { useAllRuleSets } from '../../hooks/useRuleSets';

// 自定义节点
function RuleNode({ data }: NodeProps) {
  const d = data as unknown as { label: string; fieldName: string; ruleType: string; enabled: boolean };
  const typeColors: Record<string, string> = {
    mapping: '#1677ff',
    cleaning: '#52c41a',
    lookup: '#fa8c16',
    computed: '#722ed1',
  };
  const typeLabels: Record<string, string> = {
    mapping: '映射',
    cleaning: '清洗',
    lookup: '查找',
    computed: '计算',
  };

  return (
    <div
      style={{
        padding: '10px 16px',
        borderRadius: 8,
        border: `2px solid ${d.enabled ? (typeColors[d.ruleType] || '#1677ff') : '#d9d9d9'}`,
        background: '#fff',
        minWidth: 160,
        opacity: d.enabled ? 1 : 0.5,
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <Tag color={typeColors[d.ruleType]} style={{ margin: 0 }}>
          {typeLabels[d.ruleType] || d.ruleType}
        </Tag>
        <Typography.Text strong style={{ fontSize: 13 }}>{d.label}</Typography.Text>
      </div>
      <Typography.Text code style={{ fontSize: 11 }}>{d.fieldName}</Typography.Text>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

const nodeTypes = { ruleNode: RuleNode };

interface DependencyDAGProps {
  ruleSetId?: string;
}

export default function DependencyDAG({ ruleSetId }: DependencyDAGProps = {}) {
  const [internalRuleSetId, setInternalRuleSetId] = useState<string | undefined>(ruleSetId);
  const effectiveRuleSetId = ruleSetId ?? internalRuleSetId;
  const { data: ruleSetsData } = useAllRuleSets();
  const ruleSets = ruleSetsData?.items || [];
  const selectedRuleSet = ruleSets.find((rs) => rs.id === effectiveRuleSetId);
  const { data, isLoading } = useRules({ page_size: 100, rule_set_id: effectiveRuleSetId });

  const rules = data?.items || [];

  const { nodes, edges } = useMemo(() => {
    if (rules.length === 0) return { nodes: [], edges: [] };

    // 拓扑排序分层（只考虑规则之间的依赖，依赖源字段的规则视为 level 0）
    const ruleFieldNames = new Set(rules.map((r) => r.field_name));
    const inDegree = new Map<string, number>();
    const dependents = new Map<string, string[]>();

    for (const r of rules) {
      inDegree.set(r.field_name, 0);
    }

    for (const r of rules) {
      const deps = Array.isArray(r.depends_on) ? r.depends_on : [];
      const ruleDeps = deps.filter((dep) => ruleFieldNames.has(dep));
      inDegree.set(r.field_name, ruleDeps.length);
      for (const dep of ruleDeps) {
        if (!dependents.has(dep)) dependents.set(dep, []);
        dependents.get(dep)!.push(r.field_name);
      }
    }

    // Kahn 算法分层
    const queue: string[] = [];
    const level = new Map<string, number>();
    for (const [field, deg] of inDegree) {
      if (deg === 0) {
        queue.push(field);
        level.set(field, 0);
      }
    }

    while (queue.length > 0) {
      const curr = queue.shift()!;
      const currLevel = level.get(curr)!;
      for (const next of dependents.get(curr) || []) {
        const newDeg = (inDegree.get(next) || 1) - 1;
        inDegree.set(next, newDeg);
        if (newDeg === 0) {
          queue.push(next);
          level.set(next, currLevel + 1);
        }
      }
    }

    // 未分层节点
    for (const [field] of inDegree) {
      if (!level.has(field)) level.set(field, 99);
    }

    // 构建节点和边
    const nodeList = rules.map((r) => {
      const lvl = level.get(r.field_name) ?? 0;
      const sameLevel = rules.filter((rr) => (level.get(rr.field_name) ?? 0) === lvl);
      const idxInLevel = sameLevel.findIndex((rr) => rr.field_name === r.field_name);
      return {
        id: r.field_name,
        type: 'ruleNode' as const,
        position: {
          x: idxInLevel * 200 + 50,
          y: lvl * 120 + 30,
        },
        data: {
          label: r.field_label || r.field_name,
          fieldName: r.field_name,
          ruleType: r.rule_type,
          enabled: r.enabled,
        },
      };
    });

    const edgeList = [];
    for (const r of rules) {
      const deps = Array.isArray(r.depends_on) ? r.depends_on : [];
      const ruleDeps = deps.filter((dep) => ruleFieldNames.has(dep));
      for (const dep of ruleDeps) {
        edgeList.push({
          id: `${dep}->${r.field_name}`,
          source: dep,
          target: r.field_name,
          animated: true,
          style: { stroke: '#bbb' },
        });
      }
    }

    return { nodes: nodeList, edges: edgeList };
  }, [rules]);

  if (isLoading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  if (!effectiveRuleSetId) {
    return (
      <Card title="依赖视图">
        <Empty description="请选择业务线" style={{ marginTop: 100 }} />
      </Card>
    );
  }

  if (rules.length === 0) return <Empty description="暂无规则数据" style={{ marginTop: 100 }} />;

  return (
    <Card
      title={
        <Space>
          <span>{selectedRuleSet?.name || ''} 业务线 - 依赖视图</span>
          <Space size="small">
            <Tag color="green">已启用</Tag>
            <Tag color="default">已停用</Tag>
          </Space>
        </Space>
      }
      extra={
        !ruleSetId && (
          <Select
            value={effectiveRuleSetId}
            onChange={(val) => setInternalRuleSetId(val)}
            options={ruleSets.map((rs) => ({ value: rs.id, label: rs.name }))}
            placeholder="选择业务线"
            style={{ width: 200 }}
            allowClear={false}
          />
        )
      }
    >
      <div className="dag-container">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          attributionPosition="bottom-right"
        >
          <Background />
          <Controls />
          <MiniMap
            nodeColor={(n) => {
              const nd = n.data as { enabled?: boolean; ruleType?: string } | undefined;
              if (!nd?.enabled) return '#d9d9d9';
              const colors: Record<string, string> = { mapping: '#1677ff', cleaning: '#52c41a', lookup: '#fa8c16', computed: '#722ed1' };
              return colors[nd?.ruleType || ''] || '#1677ff';
            }}
          />
        </ReactFlow>
      </div>
    </Card>
  );
}
