import { useState } from 'react';
import {
  Table, Button, Space, Input, Card, Popconfirm, Typography, App, Drawer,
  Form, Tag, Upload, Row, Col, Divider,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, UploadOutlined, MinusCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { useLookupTables, useCreateLookupTable, useUpdateLookupTable, useDeleteLookupTable, useUploadLookupTable } from '../../hooks/useLookupTables';
import type { LookupTable } from '../../types';

const { Search } = Input;

export default function LookupTables() {
  const { message } = App.useApp();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const { data, isLoading } = useLookupTables({ page, page_size: 20, search: search || undefined });

  const createTable = useCreateLookupTable();
  const updateTable = useUpdateLookupTable();
  const deleteTable = useDeleteLookupTable();
  const uploadTable = useUploadLookupTable();

  // 编辑抽屉
  const [editingTable, setEditingTable] = useState<LookupTable | null>(null);
  const [editDrawerOpen, setEditDrawerOpen] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editKeyCol, setEditKeyCol] = useState('');
  const [editValCol, setEditValCol] = useState('');
  // 可编辑的映射条目
  const [editEntries, setEditEntries] = useState<{ key: string; value: string }[]>([]);

  const handleNew = async () => {
    try {
      await createTable.mutateAsync({
        name: '新建映射表',
        source_type: 'manual',
        columns: { key_col: 'key', value_col: 'value' },
        data: {},
      });
      message.success('映射表已创建');
    } catch { /* handled */ }
  };

  const handleEdit = (table: LookupTable) => {
    setEditingTable(table);
    setEditName(table.name);
    setEditDesc(table.description || '');
    setEditKeyCol(table.columns?.key_col || 'key');
    setEditValCol(table.columns?.value_col || 'value');
    // 将 data 字典转换为可编辑的条目列表
    const entries = Object.entries(table.data || {}).map(([k, v]) => ({ key: k, value: String(v) }));
    setEditEntries(entries.length > 0 ? entries : [{ key: '', value: '' }]);
    setEditDrawerOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!editingTable) return;
    try {
      // 将条目列表转回 data 字典
      const data: Record<string, string> = {};
      for (const entry of editEntries) {
        if (entry.key.trim()) {
          data[entry.key.trim()] = entry.value;
        }
      }
      await updateTable.mutateAsync({
        id: editingTable.id,
        data: {
          name: editName,
          description: editDesc,
          columns: { key_col: editKeyCol, value_col: editValCol },
          data,
        },
      });
      message.success('已保存');
      setEditDrawerOpen(false);
    } catch { /* handled */ }
  };

  const addEntry = () => {
    setEditEntries([...editEntries, { key: '', value: '' }]);
  };

  const removeEntry = (idx: number) => {
    if (editEntries.length <= 1) return;
    setEditEntries(editEntries.filter((_, i) => i !== idx));
  };

  const updateEntry = (idx: number, field: 'key' | 'value', val: string) => {
    const updated = [...editEntries];
    updated[idx] = { ...updated[idx], [field]: val };
    setEditEntries(updated);
  };

  const handleUpload = async (file: File) => {
    try {
      await uploadTable.mutateAsync({ name: file.name.replace(/\.(csv|xlsx|xls)$/, ''), file });
      message.success('映射表已上传');
    } catch { /* handled */ }
    return false;
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 200,
      ellipsis: true,
      render: (v: string | null) => v || '-',
    },
    {
      title: '来源',
      dataIndex: 'source_type',
      key: 'source_type',
      width: 80,
      render: (t: string) => (
        <Tag color={t === 'upload' ? 'blue' : 'green'}>{t === 'upload' ? '上传' : '手动'}</Tag>
      ),
    },
    {
      title: '键列/值列',
      key: 'columns',
      width: 180,
      render: (_: unknown, r: LookupTable) => (
        <Typography.Text code>{r.columns?.key_col || '-'} → {r.columns?.value_col || '-'}</Typography.Text>
      ),
    },
    {
      title: '行数',
      dataIndex: 'row_count',
      key: 'row_count',
      width: 80,
      render: (v: number) => v?.toLocaleString() || 0,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 160,
      render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_: unknown, r: LookupTable) => (
        <Space size="small">
          <Button size="small" type="primary" icon={<EditOutlined />} onClick={() => handleEdit(r)}>
            编辑
          </Button>
          <Popconfirm title="确认删除？" onConfirm={() => deleteTable.mutate(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
          <Search
            placeholder="搜索映射表名称"
            allowClear
            style={{ width: 280 }}
            onSearch={setSearch}
            onChange={(e) => !e.target.value && setSearch('')}
          />
          <Space>
            <Upload
              accept=".csv,.xlsx,.xls"
              showUploadList={false}
              beforeUpload={handleUpload}
            >
              <Button icon={<UploadOutlined />}>上传映射表</Button>
            </Upload>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleNew}>
              新建映射表
            </Button>
          </Space>
        </Space>
      </Card>

      <Card>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data?.items || []}
          loading={isLoading}
          pagination={{
            current: page,
            pageSize: 20,
            total: data?.total || 0,
            showTotal: (t) => `共 ${t} 个映射表`,
            onChange: setPage,
          }}
          size="middle"
        />
      </Card>

      {/* 编辑抽屉 */}
      <Drawer
        title="编辑映射表"
        open={editDrawerOpen}
        onClose={() => setEditDrawerOpen(false)}
        width={700}
        extra={
          <Button type="primary" onClick={handleSaveEdit} loading={updateTable.isPending}>
            保存
          </Button>
        }
      >
        <Form layout="vertical">
          <Form.Item label="名称" required>
            <Input value={editName} onChange={(e) => setEditName(e.target.value)} />
          </Form.Item>
          <Form.Item label="描述">
            <Input.TextArea value={editDesc} onChange={(e) => setEditDesc(e.target.value)} rows={2} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="键列名">
                <Input value={editKeyCol} onChange={(e) => setEditKeyCol(e.target.value)} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="值列名">
                <Input value={editValCol} onChange={(e) => setEditValCol(e.target.value)} />
              </Form.Item>
            </Col>
          </Row>
        </Form>

        <Divider style={{ margin: '8px 0' }} />
        <Space style={{ marginBottom: 12, justifyContent: 'space-between', width: '100%' }}>
          <Typography.Text strong>映射条目（{editEntries.length} 条）</Typography.Text>
          <Button size="small" icon={<PlusOutlined />} onClick={addEntry}>
            添加条目
          </Button>
        </Space>

        <div style={{ maxHeight: 400, overflowY: 'auto' }}>
          {editEntries.map((entry, idx) => (
            <Row key={idx} gutter={8} style={{ marginBottom: 8 }} align="middle">
              <Col span={10}>
                <Input
                  size="small"
                  placeholder="键"
                  value={entry.key}
                  onChange={(e) => updateEntry(idx, 'key', e.target.value)}
                />
              </Col>
              <Col span={2} style={{ textAlign: 'center' }}>
                <Typography.Text type="secondary">→</Typography.Text>
              </Col>
              <Col span={10}>
                <Input
                  size="small"
                  placeholder="值"
                  value={entry.value}
                  onChange={(e) => updateEntry(idx, 'value', e.target.value)}
                />
              </Col>
              <Col span={2} style={{ textAlign: 'center' }}>
                <Button
                  size="small"
                  type="text"
                  danger
                  icon={<MinusCircleOutlined />}
                  onClick={() => removeEntry(idx)}
                  disabled={editEntries.length <= 1}
                />
              </Col>
            </Row>
          ))}
        </div>
      </Drawer>
    </div>
  );
}
