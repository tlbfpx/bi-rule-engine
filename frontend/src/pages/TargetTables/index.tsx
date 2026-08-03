import { useState } from 'react';
import {
  Card, Table, Button, Space, Tag, Modal, Form, Input, Select,
  InputNumber, Drawer, Switch, Row, Col, App,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
} from '@ant-design/icons';
import { useTargetTables, useDeleteTargetTable, useCreateTargetTable, useUpdateTargetTable, useTestTargetTableConnection } from '../../hooks/useTargetTables';
import type { TargetTable, WriteMode } from '../../types';

const WRITE_MODE_OPTIONS = [
  { value: 'append', label: '追加写入' },
  { value: 'truncate_insert', label: '清空后写入' },
  { value: 'upsert', label: '更新插入' },
];

export default function TargetTables() {
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const { data, isLoading } = useTargetTables({ page, page_size: pageSize });
  const deleteTt = useDeleteTargetTable();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<TargetTable | null>(null);
  const { modal } = App.useApp();

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name', width: 180, ellipsis: true },
    { title: '目标表', dataIndex: 'table_name', key: 'table_name', width: 160 },
    { title: '数据库', dataIndex: 'db_name', key: 'db_name', width: 140 },
    {
      title: '写入模式',
      dataIndex: 'write_mode',
      key: 'write_mode',
      width: 130,
      render: (m: WriteMode) => WRITE_MODE_OPTIONS.find((o) => o.value === m)?.label || m,
    },
    {
      title: '自动建表',
      dataIndex: 'auto_create_table',
      key: 'auto_create_table',
      width: 100,
      render: (v: boolean) => <Tag color={v ? 'blue' : 'default'}>{v ? '是' : '否'}</Tag>,
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
      width: 160,
      render: (_: unknown, record: TargetTable) => (
        <Space size="small">
          <Button icon={<EditOutlined />} size="small" onClick={() => { setEditing(record); setDrawerOpen(true); }}>
            编辑
          </Button>
          <Button
            icon={<DeleteOutlined />}
            size="small"
            danger
            loading={deleteTt.isPending}
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const handleDelete = (record: TargetTable) => {
    modal.confirm({
      title: '确认删除',
      content: `确定删除目标表配置 "${record.name}" 吗？`,
      onOk: () => deleteTt.mutate(record.id),
    });
  };

  return (
    <Card
      title="目标表管理"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); setDrawerOpen(true); }}>
          新建目标表
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
          showTotal: (t) => `共 ${t} 个目标表`,
        }}
        size="middle"
      />
      <TargetTableDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        initial={editing}
      />
    </Card>
  );
}

function TargetTableDrawer({ open, onClose, initial }: { open: boolean; onClose: () => void; initial: TargetTable | null }) {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const createTt = useCreateTargetTable();
  const updateTt = useUpdateTargetTable();
  const testConn = useTestTargetTableConnection();
  const [writeMode, setWriteMode] = useState<WriteMode>(initial?.write_mode || 'append');

  const isEdit = !!initial;

  const handleSubmit = async () => {
    const values = await form.validateFields().catch(() => null);
    if (!values) return; // 校验未通过，表单已显示字段错误
    if (isEdit) {
      updateTt.mutate({ id: initial!.id, data: values }, {
        onSuccess: () => { message.success('更新成功'); onClose(); },
      });
    } else {
      createTt.mutate(values, {
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
      title={isEdit ? '编辑目标表' : '新建目标表'}
      size="large"
      open={open}
      onClose={onClose}
      destroyOnHidden
      footer={
        <Space style={{ float: 'right' }}>
          <Button onClick={handleTest} loading={testConn.isPending}>测试连接</Button>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" onClick={handleSubmit} loading={createTt.isPending || updateTt.isPending}>
            保存
          </Button>
        </Space>
      }
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={initial ? { ...initial, db_password: undefined } : { db_port: 3306, enabled: true, write_mode: 'append', auto_create_table: true, upsert_keys: [] }}
        onValuesChange={(changed) => { if (changed.write_mode) setWriteMode(changed.write_mode); }}
      >
        <Form.Item name="name" label="配置名称" rules={[{ required: true }]}>
          <Input placeholder="例如：清洗后订单表" />
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

        <Form.Item name="table_name" label="目标表名" rules={[{ required: true }]}>
          <Input placeholder="orders_cleaned" />
        </Form.Item>

        <Form.Item name="write_mode" label="写入模式" rules={[{ required: true }]}>
          <Select options={WRITE_MODE_OPTIONS} />
        </Form.Item>
        {writeMode === 'upsert' && (
          <Form.Item name="upsert_keys" label="Upsert 主键字段">
            <Select mode="tags" tokenSeparators={[',', ' ']} placeholder="输入字段名，按回车确认" />
          </Form.Item>
        )}

        <Form.Item name="auto_create_table" label="自动建表" valuePropName="checked">
          <Switch checkedChildren="是" unCheckedChildren="否" />
        </Form.Item>
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
