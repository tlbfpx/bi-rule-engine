import { useState } from 'react';
import { Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useTasks } from '../../hooks/useTasks';
import type { Task, TaskStatus } from '../../types';

const STATUS_TAG: Record<TaskStatus, { color: string; label: string }> = {
  pending: { color: 'default', label: '等待中' },
  running: { color: 'processing', label: '运行中' },
  completed: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
};

export default function TaskList() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useTasks({ page, page_size: 20 });

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'task_name',
      key: 'task_name',
      width: 200,
      ellipsis: true,
    },
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
    {
      title: '输入行数',
      dataIndex: 'input_rows',
      key: 'input_rows',
      width: 100,
      render: (v: number | null) => v?.toLocaleString() || '-',
    },
    {
      title: '输出行数',
      dataIndex: 'output_rows',
      key: 'output_rows',
      width: 100,
      render: (v: number | null) => v?.toLocaleString() || '-',
    },
    {
      title: '耗时',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      width: 100,
      render: (v: number | null) => (v != null ? `${(v / 1000).toFixed(2)}s` : '-'),
    },
    {
      title: '格式',
      dataIndex: 'output_format',
      key: 'output_format',
      width: 80,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm'),
    },
  ];

  return (
    <div>
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data?.items || []}
        loading={isLoading}
        pagination={{
          current: page,
          pageSize: 20,
          total: data?.total || 0,
          showTotal: (t) => `共 ${t} 个任务`,
          onChange: setPage,
        }}
        size="middle"
        expandable={{
          expandedRowRender: (record: Task) => (
            <div style={{ padding: 8 }}>
              {record.stats && Object.keys(record.stats).length > 0 && (
                <div>
                  <Typography.Text strong>字段统计：</Typography.Text>
                  <pre style={{ fontSize: 12, maxHeight: 200, overflow: 'auto' }}>
                    {JSON.stringify(record.stats, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ),
        }}
      />
    </div>
  );
}
