import { useState } from 'react';
import {
  Card, Table, Tag, Typography, Modal, Descriptions,
} from 'antd';
import dayjs from 'dayjs';
import { useETLJobRuns, useETLJobRun, useAllETLJobRuns } from '../../hooks/useETLJobs';
import type { ETLJobRun, TaskStatus } from '../../types';

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  pending: { color: 'default', label: '等待中' },
  running: { color: 'processing', label: '运行中' },
  completed: { color: 'success', label: '成功' },
  failed: { color: 'error', label: '失败' },
};

export default function ETLJobRunList({ jobId, embedded = false }: { jobId?: string; embedded?: boolean }) {
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  // 根据 jobId 决定查全量还是单 job 的 runs，避免同时发两个请求
  const jobRuns = useETLJobRuns(jobId || null, { page, page_size: pageSize });
  const allRuns = useAllETLJobRuns({ page, page_size: pageSize }, !jobId);
  const { data, isLoading } = jobId ? jobRuns : allRuns;
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const columns = [
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: TaskStatus) => {
        const cfg = STATUS_TAG[s] || { color: 'default', label: s };
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    { title: '输入行数', dataIndex: 'input_rows', key: 'input_rows', width: 110, render: (v: number | null) => v?.toLocaleString() || '-' },
    { title: '输出行数', dataIndex: 'output_rows', key: 'output_rows', width: 110, render: (v: number | null) => v?.toLocaleString() || '-' },
    { title: '错误行数', dataIndex: 'error_rows', key: 'error_rows', width: 100, render: (v: number) => v.toLocaleString() },
    { title: '耗时', dataIndex: 'duration_ms', key: 'duration_ms', width: 100, render: (v: number | null) => (v != null ? `${(v / 1000).toFixed(2)}s` : '-') },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 160,
      render: (t: string | null) => t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: unknown, record: ETLJobRun) => (
        <Typography.Link onClick={() => setSelectedRunId(record.id)}>详情</Typography.Link>
      ),
    },
  ];

  const content = (
    <>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data?.items || []}
        loading={isLoading}
        pagination={{
          current: page,
          pageSize,
          total: data?.total || 0,
          onChange: setPage,
          showTotal: (t) => `共 ${t} 次执行`,
        }}
        size="middle"
      />
      <RunDetailModal runId={selectedRunId} onClose={() => setSelectedRunId(null)} />
    </>
  );

  if (embedded) return content;
  return <Card title="执行历史">{content}</Card>;
}

function RunDetailModal({ runId, onClose }: { runId: string | null; onClose: () => void }) {
  const { data: run } = useETLJobRun(runId);

  return (
    <Modal
      title="执行详情"
      open={!!runId}
      onCancel={onClose}
      width={800}
      footer={null}
    >
      {run && (
        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label="状态">
            <Tag color={STATUS_TAG[run.status]?.color || 'default'}>{STATUS_TAG[run.status]?.label || run.status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="任务">{run.etl_job?.job_name || run.etl_job_id}</Descriptions.Item>
          <Descriptions.Item label="输入行数">{run.input_rows?.toLocaleString() || '-'}</Descriptions.Item>
          <Descriptions.Item label="输出行数">{run.output_rows?.toLocaleString() || '-'}</Descriptions.Item>
          <Descriptions.Item label="错误行数">{run.error_rows.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="耗时">{run.duration_ms != null ? `${(run.duration_ms / 1000).toFixed(2)}s` : '-'}</Descriptions.Item>
          <Descriptions.Item label="开始时间">{run.started_at ? dayjs(run.started_at).format('YYYY-MM-DD HH:mm:ss') : '-'}</Descriptions.Item>
          <Descriptions.Item label="结束时间">{run.completed_at ? dayjs(run.completed_at).format('YYYY-MM-DD HH:mm:ss') : '-'}</Descriptions.Item>
        </Descriptions>
      )}
      {run?.executed_sql && (
        <div style={{ marginTop: 16 }}>
          <Typography.Text strong>执行 SQL：</Typography.Text>
          <pre style={{ fontSize: 12, maxHeight: 200, overflow: 'auto', background: '#f5f5f5', padding: 12 }}>{run.executed_sql}</pre>
        </div>
      )}
      {run?.error_log && Object.keys(run.error_log).length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Typography.Text strong type="danger">错误日志：</Typography.Text>
          <pre style={{ fontSize: 12, maxHeight: 200, overflow: 'auto', background: '#fff2f0', padding: 12 }}>
            {JSON.stringify(run.error_log, null, 2)}
          </pre>
        </div>
      )}
      {run?.stats && Object.keys(run.stats).length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Typography.Text strong>规则执行统计：</Typography.Text>
          <pre style={{ fontSize: 12, maxHeight: 200, overflow: 'auto', background: '#f6ffed', padding: 12 }}>
            {JSON.stringify(run.stats, null, 2)}
          </pre>
        </div>
      )}
    </Modal>
  );
}
