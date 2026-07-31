/**
 * 规则编辑器底部的「逻辑流程图（实时）」面板。
 * 读取 useRuleEditorStore，随编辑即时刷新；只读预览（不可拖拽/连线）。
 */
import { useEffect, useMemo, useRef } from 'react';
import { Collapse, Empty } from 'antd';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useRuleEditorStore } from '../../../stores/ruleStore';
import { useLookupTables } from '../../../hooks/useLookupTables';
import { nodeTypes } from './nodes';
import { buildGraph } from './buildGraph';

function FlowInner() {
  const { fitView } = useReactFlow();
  // 窄选择器：减少无关字段变更导致的重渲染
  const ruleType = useRuleEditorStore((s) => s.ruleType);
  const fieldName = useRuleEditorStore((s) => s.fieldName);
  const config = useRuleEditorStore((s) => s.config);
  const dependsOn = useRuleEditorStore((s) => s.dependsOn);

  // 仅 lookup 类型需要解析表名；其余类型禁用查询，避免每次打开抽屉都发无用请求
  const isLookup = ruleType === 'lookup';
  const { data: tablesData } = useLookupTables({ page_size: 200 }, isLookup);
  const tablesById = useMemo(
    () =>
      new Map(
        (tablesData?.items || []).map((t) => [t.id, { name: t.name }] as const),
      ),
    [tablesData],
  );

  const { nodes, edges } = useMemo(
    () => buildGraph({ ruleType, fieldName, config, dependsOn, tablesById }),
    [ruleType, fieldName, config, dependsOn, tablesById],
  );

  // 仅在规则类型切换（图形状变化）时重新 fitView，避免每次输入都重缩放
  const prevType = useRef(ruleType);
  useEffect(() => {
    if (prevType.current !== ruleType) {
      prevType.current = ruleType;
      const rafId = requestAnimationFrame(() => fitView({ padding: 0.2 }));
      return () => cancelAnimationFrame(rafId);
    }
  }, [ruleType, fitView]);

  if (nodes.length === 0) {
    return <Empty description="暂无可视化内容（请先完成基本配置）" style={{ padding: 32 }} />;
  }

  return (
    <div
      style={{
        height: 380,
        border: '1px solid #e8e8e8',
        borderRadius: 8,
        background: '#fff',
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        attributionPosition="bottom-right"
      >
        <Background />
        <Controls showInteractive={false} />
        <MiniMap pannable zoomable />
      </ReactFlow>
    </div>
  );
}

export default function FlowchartPreview() {
  return (
    <Collapse
      defaultActiveKey={['flow']}
      items={[
        {
          key: 'flow',
          label: '逻辑流程图（实时）',
          children: (
            <ReactFlowProvider>
              <FlowInner />
            </ReactFlowProvider>
          ),
        },
      ]}
    />
  );
}
