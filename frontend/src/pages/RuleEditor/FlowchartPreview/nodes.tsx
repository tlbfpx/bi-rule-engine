/**
 * 流程图自定义节点。按 data.role 着色，含 4 个 Handle：
 * target: top / left ；source: bottom / right。纵向链走 bottom→top，分支走 right→left。
 */
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Tag, Typography } from 'antd';
import { RULE_TYPE_HEX } from '../../../utils/ruleLabels';
import type { FlowNodeData, FlowTone } from './buildGraph';

const TONE: Record<FlowTone, { border: string; bg: string; color: string }> = {
  default: { border: '#d9d9d9', bg: '#fafafa', color: '#595959' },
  success: { border: '#52c41a', bg: '#f6ffed', color: '#389e0d' },
  warning: { border: '#faad14', bg: '#fff7e6', color: '#d48806' },
  danger: { border: '#ff4d4f', bg: '#fff2f0', color: '#cf1322' },
};

function FlowNode({ data }: NodeProps) {
  const d = data as unknown as FlowNodeData;
  const hex = RULE_TYPE_HEX[d.ruleType] || '#1677ff';
  const tone = TONE[d.tone || 'default'];

  let border = `1px solid ${hex}`;
  let background = '#fff';
  if (d.role === 'input') border = `2px solid ${hex}`;
  if (d.role === 'process') {
    border = '1px solid #91caff';
    background = '#f0f7ff';
  }
  if (d.role === 'result') {
    border = `1px solid ${tone.border}`;
    background = tone.bg;
  }

  return (
    <div
      title={d.tip}
      style={{
        padding: '8px 12px',
        borderRadius: 8,
        border,
        background,
        minWidth: 150,
        maxWidth: 240,
        boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
      }}
    >
      <Handle type="target" position={Position.Top} id="top" style={{ opacity: 0 }} />
      <Handle type="target" position={Position.Left} id="left" style={{ opacity: 0 }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: d.lines?.length ? 6 : 0, flexWrap: 'wrap' }}>
        {d.badge && <Tag color={d.badgeColor} style={{ margin: 0, fontSize: 11 }}>{d.badge}</Tag>}
        <Typography.Text strong style={{ fontSize: 13 }}>
          {d.title}
        </Typography.Text>
      </div>

      {d.lines?.map((line, i) => (
        <div key={i} style={{ fontSize: 11, color: '#595959', fontFamily: 'monospace', lineHeight: 1.6, wordBreak: 'break-all' }}>
          {line}
        </div>
      ))}

      {d.subtitle && (
        <div
          style={{
            marginTop: d.lines?.length ? 4 : 4,
            fontSize: 11,
            color: d.role === 'result' ? tone.color : '#8c8c8c',
            fontFamily: d.subtitleMono ? 'monospace' : undefined,
            wordBreak: 'break-all',
          }}
        >
          {d.subtitle}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} id="bottom" style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Right} id="right" style={{ opacity: 0 }} />
    </div>
  );
}

export const nodeTypes = { flowNode: FlowNode };
