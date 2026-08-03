import { useState } from 'react';
import {
  Card, Table, Button, Space, Tag, Modal, Form, Input, Select,
  InputNumber, Drawer, Typography, App, Row, Col, Switch,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ThunderboltOutlined,
} from '@ant-design/icons';
import { useDataSources, useDeleteDataSource, useCreateDataSource, useUpdateDataSource, useTestDataSourceConnection, usePreviewDataSource } from '../../hooks/useDataSources';
import type { DataSource, DataSourceUpdatePayload, ExtractMode, DataSourcePreviewResult } from '../../types';

const EXTRACT_MODE_OPTIONS = [
  { value: 'table', label: '表名抽取' },
  { value: 'sql', label: '自定义 SQL' },
];

export default function DataSources() {
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const { data, isLoading } = useDataSources({ page, page_size: pageSize });
  const deleteDs = useDeleteDataSource();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<DataSource | null>(null);
  const [previewDs, setPreviewDs] = useState<DataSource | null>(null);
  const { modal } = App.useApp();

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name', width: 180, ellipsis: true },
    { title: '数据库', dataIndex: 'db_name', key: 'db_name', width: 140 },
    { title: '主机', dataIndex: 'db_host', key: 'db_host', width: 160 },
    {
      title: '抽取方式',
      dataIndex: 'extract_mode',
      key: 'extract_mode',
      width: 110,
      render: (m: ExtractMode) => (m === 'sql' ? '自定义 SQL' : '表名'),
    },
    {
      title: '增量字段',
      dataIndex: 'incremental_column',
      key: 'incremental_column',
      width: 140,
      render: (v: string | null) => v || '-',
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (v: boolean) => <Tag color={v ? 'success' : 'default'}>{v ? '启用' : '停用'}</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: unknown, record: DataSource) => (
        <Space size="small">
          <Button icon={<ThunderboltOutlined />} size="small" onClick={() => setPreviewDs(record)}>
            预览
          </Button>
          <Button icon={<EditOutlined />} size="small" onClick={() => { setEditing(record); setDrawerOpen(true); }}>
            编辑
          </Button>
          <Button
            icon={<DeleteOutlined />}
            size="small"
            danger
            loading={deleteDs.isPending}
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const handleDelete = (record: DataSource) => {
    modal.confirm({
      title: '确认删除',
      content: `确定删除数据源 "${record.name}" 吗？`,
      onOk: () => deleteDs.mutate(record.id),
    });
  };

  return (
    <Card
      title="数据源管理"
      extra={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => { setEditing(null); setDrawerOpen(true); }}
        >
          新建数据源
        </Button>
      }
    >
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
          showTotal: (t) => `共 ${t} 个数据源`,
        }}
        size="middle"
      />
      <DataSourceDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        initial={editing}
      />
      <PreviewModal dataSource={previewDs} onClose={() => setPreviewDs(null)} />
    </Card>
  );
}

function DataSourceDrawer({ open, onClose, initial }: { open: boolean; onClose: () => void; initial: DataSource | null }) {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const createDs = useCreateDataSource();
  const updateDs = useUpdateDataSource();
  const testConn = useTestDataSourceConnection();
  const [mode, setMode] = useState<ExtractMode>(initial?.extract_mode || 'table');

  const isEdit = !!initial;

  const handleSubmit = async () => {
    const values = await form.validateFields().catch(() => null);
    if (!values) return; // 校验未通过，表单已显示字段错误
    if (isEdit) {
      updateDs.mutate({ id: initial!.id, data: values as DataSourceUpdatePayload }, {
        onSuccess: () => { message.success('更新成功'); onClose(); },
      });
    } else {
      createDs.mutate(values, {
        onSuccess: () => { message.success('创建成功'); onClose(); },
      });
    }
  };

  const handleTest = async () => {
    const values = await form.validateFields(['db_host', 'db_port', 'db_name', 'db_username', 'db_password']).catch(() => null);
    if (!values) return; // 连接字段未填全
    testConn.mutate(values, {
      onSuccess: () => message.success('连接成功'),
    });
  };

  return (
    <Drawer
      title={isEdit ? '编辑数据源' : '新建数据源'}
      width={560}
      open={open}
      onClose={onClose}
      destroyOnClose
      footer={
        <Space style={{ float: 'right' }}>
          <Button onClick={handleTest} loading={testConn.isPending}>测试连接</Button>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" onClick={handleSubmit} loading={createDs.isPending || updateDs.isPending}>
            保存
          </Button>
        </Space>
      }
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={initial ? { ...initial, db_password: undefined } : { db_port: 3306, enabled: true, extract_mode: 'table' }}
        onValuesChange={(changed) => { if (changed.extract_mode) setMode(changed.extract_mode); }}
      >
        <Form.Item name="name" label="数据源名称" rules={[{ required: true }]}>
          <Input placeholder="例如：订单源库" />
        </Form.Item>
        <Row gutter={16}>
          <Col span={16}>
            <Form.Item name="db_host" label="主机" rules={[{ required: true }]}>
              <Input placeholder="localhost" />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="db_port" label="端口" rules={[{ required: true }]}>
              <InputNumber style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="db_name" label="数据库" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="db_username" label="用户名" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item
          name="db_password"
          label={isEdit ? '密码（留空则不修改）' : '密码'}
          rules={isEdit ? [] : [{ required: true }]}
        >
          <Input.Password />
        </Form.Item>

        <Form.Item name="extract_mode" label="抽取方式" rules={[{ required: true }]}>
          <Select options={EXTRACT_MODE_OPTIONS} />
        </Form.Item>
        {mode === 'sql' ? (
          <Form.Item name="extract_sql" label="抽取 SQL" rules={[{ required: true }]}>
            <Input.TextArea rows={4} placeholder="SELECT * FROM orders WHERE create_time > '2024-01-01'" />
          </Form.Item>
        ) : (
          <Form.Item name="extract_table" label="源表名" rules={[{ required: true }]}>
            <Input placeholder="orders" />
          </Form.Item>
        )}

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="incremental_column" label="增量字段（可选）">
              <Input placeholder="create_time / id" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="incremental_value" label="起始增量值（可选）">
              <Input placeholder="2024-01-01 00:00:00" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="enabled" label="状态" valuePropName="checked">
          <Switch checkedChildren="启用" unCheckedChildren="停用" />
        </Form.Item>
        <Form.Item name="description" label="描述">
          <Input.TextArea rows={2} />
        </Form.Item>
      </Form>
    </Drawer>
  );
}

function PreviewModal({ dataSource, onClose }: { dataSource: DataSource | null; onClose: () => void }) {
  const preview = usePreviewDataSource();
  const [result, setResult] = useState<DataSourcePreviewResult | null>(null);

  const handlePreview = () => {
    if (!dataSource) return;
    preview.mutate({ id: dataSource.id, limit: 20 }, {
      onSuccess: (data) => setResult(data),
    });
  };

  return (
    <Modal
      title={`数据源预览：${dataSource?.name || ''}`}
      open={!!dataSource}
      onCancel={onClose}
      width={900}
      footer={[
        <Button key="preview" type="primary" onClick={handlePreview} loading={preview.isPending}>
          获取预览
        </Button>,
        <Button key="close" onClick={onClose}>关闭</Button>,
      ]}
    >
      {result && (
        <>
          <Typography.Paragraph>
            <Typography.Text strong>预览 SQL：</Typography.Text>
            <pre style={{ fontSize: 12 }}>{result.sql}</pre>
          </Typography.Paragraph>
          <Typography.Paragraph>
            <Typography.Text strong>总行数：</Typography.Text> {result.total_rows}
          </Typography.Paragraph>
          <Table
            size="small"
            scroll={{ x: 'max-content' }}
            columns={result.columns.map((col: string) => ({ title: col, dataIndex: col, key: col, ellipsis: true }))}
            dataSource={result.preview_rows}
            pagination={false}
            rowKey={(_, idx) => String(idx)}
          />
        </>
      )}
    </Modal>
  );
}
