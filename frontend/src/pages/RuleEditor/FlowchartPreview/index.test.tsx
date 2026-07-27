import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../../../test/utils';
import { useRuleEditorStore } from '../../../stores/ruleStore';
import FlowchartPreview from './index';

// jsdom 无真实 canvas/尺寸，mock 掉 ReactFlow 仅验证组件挂载与 buildGraph 接线
vi.mock('@xyflow/react', () => ({
  ReactFlow: ({ nodes }: { nodes: unknown[] }) =>
    React.createElement('div', { 'data-testid': 'rf-mock' }, `nodes:${nodes.length}`),
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', null, children),
  Background: () => null,
  Controls: () => null,
  MiniMap: () => null,
  useReactFlow: () => ({ fitView: () => {} }),
  MarkerType: { ArrowClosed: 'arrowclosed' },
}));

function seedMapping() {
  useRuleEditorStore.setState({
    ruleType: 'mapping',
    fieldName: 'prod_class',
    dependsOn: [],
    config: {
      conditions: [
        {
          id: 'g1',
          priority: 1,
          logic: 'AND',
          rows: [{ id: 'r1', field: 'f', operator: 'eq', value: '1' }],
          result_type: 'constant',
          result_value: '集团体检',
        },
      ],
      cleaning_steps: [],
      lookup_table_id: null,
      lookup_key_field: null,
      lookup_value_field: null,
      lookup_fallbacks: [],
      formula_expression: null,
      default_result: '其他',
    },
  });
}

describe('FlowchartPreview 组件', () => {
  it('挂载并显示标签，且 mock 反映 buildGraph 节点数', () => {
    seedMapping();
    renderWithProviders(<FlowchartPreview />);
    // 1 条件组 → input + 1 condition + 1 offramp + default = 4 节点
    expect(screen.getByText('nodes:4')).toBeInTheDocument();
    expect(screen.getByText('逻辑流程图（实时）')).toBeInTheDocument();
  });
});
