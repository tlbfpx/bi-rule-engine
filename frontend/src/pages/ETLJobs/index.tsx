import { useState } from 'react';
import {
  Card, Table, Button, Space, Tag, Switch, Modal, Form, Input, Select,
  InputNumber, Drawer, Typography, App, Row, Col, Dropdown, Tooltip,
} from 'antd';
import type { MenuProps } from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined,
  HistoryOutlined, MoreOutlined,
} from '@ant-design/icons';
import { useETLJobs, useDeleteETLJob, useCreateETLJob, useUpdateETLJob, useRunETLJob, useToggleETLJob } from '../../hooks/useETLJobs';
import { useAllDataSources } from '../../hooks/useDataSources';
import { useAllTargetTables } from '../../hooks/useTargetTables';
import { useAllRuleSets } from '../../hooks/useRuleSets';
import type { ETLJob, ETLJobCreatePayload } from '../../types';
import ETLJobRunList from '../ETLJobRuns';

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  pending: { color: 'default', label: '等待中' },
  running: { color: 'processing', label: '运行中' },
  completed: { color: 'success', label: '成功' },
  failed: { color: 'error', label: '失败' },
};

export default function ETLJobs() {
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const { data, isLoading } = useETLJobs({ page, page_size: pageSize });
  const deleteJob = useDeleteETLJob();
  const runJob = useRunETLJob();
  const toggleJob = useToggleETLJob();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<ETLJob | null>(null);
  const [runHistoryJobId, setRunHistoryJobId] = useState<string | null>(null);

  const handleDelete = (record: ETLJob) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定删除 ETL 任务 "${record.job_name}" 吗？`,
      onOk: () => deleteJob.mutate(record.id),
    });
  };

  const columns = [
    {
      title: '任务名称', dataIndex: 'job_name', key: 'job_name', width: 180, ellipsis: true,
      render: (name: string, record: ETLJob) => (
        <Space direction="vertical" size={0}>
          <span style={{ fontWeight: 500 }}>{name}</span>
          {record.description && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }} ellipsis>
              {record.description}
            </Typography.Text>
          )}
        </Space>
      ),
    },
    {
      title: '数据源',
      dataIndex: ['data_source', 'name'],
      key: 'data_source',
      width: 120,
      ellipsis: true,
      render: (_: unknown, record: ETLJob) => (
        <Tooltip title={record.data_source?.name}>
          <span>{record.data_source?.name || '-'}</span>
        </Tooltip>
      ),
    },
    {
      title: '目标表',
      dataIndex: ['target_table', 'name'],
      key: 'target_table',
      width: 120,
      ellipsis: true,
      render: (_: unknown, record: ETLJob) => (
        <Tooltip title={record.target_table?.name}>
          <span>{record.target_table?.name || '-'}</span>
        </Tooltip>
      ),
    },
    {
      title: 'Cron', dataIndex: 'cron_expression', key: 'cron_expression', width: 120,
      render: (cron: string) => <code style={{ fontSize: 12 }}>{cron}</code>,
    },
    {
      title: '规则集',
      dataIndex: 'rule_set_id',
      key: 'rule_set_id',
      width: 100,
      render: (id: string | null) => id ? <Tag>{id.slice(0, 8)}</Tag> : <Typography.Text type="secondary">-</Typography.Text>,
    },
    {
      title: '上次运行',
      dataIndex: 'last_run_status',
      key: 'last_run_status',
      width: 90,
      render: (s: string | null, record: ETLJob) => {
        if (!s) return <Typography.Text type="secondary">-</Typography.Text>;
        const cfg = STATUS_TAG[s] || { color: 'default', label: s };
        return (
          <Tooltip title={record.last_run_at ? new Date(record.last_run_at).toLocaleString() : ''}>
            <Tag color={cfg.color}>{cfg.label}</Tag>
          </Tooltip>
        );
      },
    },
    {
      title: '启用',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 60,
      align: 'center' as const,
      render: (v: boolean, record: ETLJob) => (
        <Switch
          checked={v}
          size="small"
          onChange={(checked) => toggleJob.mutate({ id: record.id, enabled: checked })}
        />
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      fixed: 'right' as const,
      render: (_: unknown, record: ETLJob) => {
        const menuItems: MenuProps['items'] = [
          {
            key: 'run',
            icon: <PlayCircleOutlined />,
            label: '立即执行',
            onClick: () => runJob.mutate(record.id),
          },
          {
            key: 'history',
            icon: <HistoryOutlined />,
            label: '执行历史',
            onClick: () => setRunHistoryJobId(record.id),
          },
          { type: 'divider' },
          {
            key: 'edit',
            icon: <EditOutlined />,
            label: '编辑',
            onClick: () => { setEditing(record); setDrawerOpen(true); },
          },
          {
            key: 'delete',
            icon: <DeleteOutlined />,
            label: '删除',
            danger: true,
            onClick: () => handleDelete(record),
          },
        ];
        return (
          <Dropdown menu={{ items: menuItems }} trigger={['click']} placement="bottomRight">
            <Button icon={<MoreOutlined />} size="small" />
          </Dropdown>
        );
      },
    },
  ];

  return (
    <Card
      title="ETL 调度任务"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); setDrawerOpen(true); }}>
          新建任务
        </Button>
      }
      styles={{ body: { padding: '16px 24px' } }}
    >
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data?.items || []}
        loading={isLoading}
        scroll={{ x: 'max-content' }}
        pagination={{
          current: page,
          pageSize,
          total: data?.total || 0,
          onChange: setPage,
          showTotal: (t) => `共 ${t} 个任务`,
          showSizeChanger: false,
        }}
        size="middle"
        locale={{ emptyText: '暂无 ETL 调度任务，点击右上角「新建任务」创建' }}
      />
      <ETLJobDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        initial={editing}
      />
      <Modal
        title="执行历史"
        open={!!runHistoryJobId}
        onCancel={() => setRunHistoryJobId(null)}
        width={1100}
        footer={null}
        destroyOnClose
      >
        {runHistoryJobId && <ETLJobRunList jobId={runHistoryJobId} />}
      </Modal>
    </Card>
  );
}

function ETLJobDrawer({ open, onClose, initial }: { open: boolean; onClose: () => void; initial: ETLJob | null }) {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const createJob = useCreateETLJob();
  const updateJob = useUpdateETLJob();
  const { data: dsData } = useAllDataSources();
  const { data: ttData } = useAllTargetTables();
  const { data: rsData } = useAllRuleSets();

  const isEdit = !!initial;

  const dataSourceOptions = dsData?.items.map((d) => ({ value: d.id, label: d.name, disabled: !d.enabled })) || [];
  const targetTableOptions = ttData?.items.map((t) => ({ value: t.id, label: `${t.name} (${t.table_name})`, disabled: !t.enabled })) || [];
  const ruleSetOptions = rsData?.items.map((rs) => ({ value: rs.id, label: rs.name })) || [];

  const handleSubmit = async () => {
    const values = await form.validateFields().catch(() => null);
    if (!values) return; // 校验未通过，表单已显示字段错误
    if (isEdit) {
      updateJob.mutate({ id: initial!.id, data: values }, {
        onSuccess: () => { message.success('更新成功'); onClose(); },
      });
    } else {
      createJob.mutate(values as ETLJobCreatePayload, {
        onSuccess: () => { message.success('创建成功'); onClose(); },
      });
    }
  };

  return (
    <Drawer
      title={isEdit ? '编辑 ETL 任务' : '新建 ETL 任务'}
      width={560}
      open={open}
      onClose={onClose}
      destroyOnClose
      footer={
        <Space style={{ float: 'right' }}>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" onClick={handleSubmit} loading={createJob.isPending || updateJob.isPending}>
            保存
          </Button>
        </Space>
      }
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={initial || { enabled: true, timezone: 'Asia/Shanghai', error_retry_count: 0, timeout_seconds: 3600 }}
      >
        <Form.Item name="job_name" label="任务名称" rules={[{ required: true, message: '请输入任务名称' }]}>
          <Input placeholder="例如：每日订单清洗" />
        </Form.Item>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="data_source_id" label="数据源" rules={[{ required: true, message: '请选择数据源' }]}>
              <Select options={dataSourceOptions} placeholder="选择数据源" showSearch optionFilterProp="label" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="target_table_id" label="目标表" rules={[{ required: true, message: '请选择目标表' }]}>
              <Select options={targetTableOptions} placeholder="选择目标表" showSearch optionFilterProp="label" />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={14}>
            <Form.Item name="cron_expression" label="Cron 表达式" rules={[{ required: true, message: '请输入 Cron 表达式' }]}>
              <Input placeholder="0 2 * * *" />
            </Form.Item>
          </Col>
          <Col span={10}>
            <Form.Item name="timezone" label="时区" rules={[{ required: true }]}>
              <Input placeholder="Asia/Shanghai" />
            </Form.Item>
          </Col>
        </Row>
        <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginTop: -12, marginBottom: 16 }}>
          Cron 格式：分 时 日 月 周。例如 <code>0 2 * * *</code> 表示每天凌晨 2 点。
        </Typography.Paragraph>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="error_retry_count" label="失败重试次数">
              <InputNumber min={0} max={10} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="timeout_seconds" label="超时时间（秒）">
              <InputNumber min={60} max={86400} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item name="rule_set_id" label="关联规则集">
          <Select options={ruleSetOptions} placeholder="选择规则集（可选）" allowClear showSearch optionFilterProp="label" />
        </Form.Item>
        <Form.Item name="enabled" label="启用调度" valuePropName="checked">
          <Switch checkedChildren="启用" unCheckedChildren="停用" />
        </Form.Item>
        <Form.Item name="description" label="描述">
          <Input.TextArea rows={3} placeholder="任务说明（可选）" maxLength={500} showCount />
        </Form.Item>
      </Form>
    </Drawer>
  );
}
