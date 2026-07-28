import { useState } from 'react';
import {
  Card, Row, Col, Button, Modal, Form, Input, Space,
  Popconfirm, App, Spin, Empty, Statistic,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import {
  useRuleSets, useCreateRuleSet,
  useUpdateRuleSet, useDeleteRuleSet,
} from '../../hooks/useRuleSets';
import type { RuleSet } from '../../types';

const PRESET_COLORS = [
  '#1677ff', '#52c41a', '#fa8c16', '#eb2f96',
  '#722ed1', '#13c2c2', '#f5222d', '#faad14',
];

export default function RuleSetManager() {
  const navigate = useNavigate();
  const { data, isLoading } = useRuleSets();
  const createRuleSet = useCreateRuleSet();
  const updateRuleSet = useUpdateRuleSet();
  const deleteRuleSet = useDeleteRuleSet();
  const { message } = App.useApp();

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<RuleSet | null>(null);
  const [form] = Form.useForm();
  const [selectedColor, setSelectedColor] = useState(PRESET_COLORS[0]);

  const ruleSets: RuleSet[] = data?.items ?? [];

  const openCreateModal = () => {
    setEditing(null);
    form.resetFields();
    setSelectedColor(PRESET_COLORS[0]);
    form.setFieldsValue({ color: PRESET_COLORS[0] });
    setModalOpen(true);
  };

  const openEditModal = (rs: RuleSet) => {
    setEditing(rs);
    form.setFieldsValue(rs);
    setSelectedColor(rs.color);
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    form.resetFields();
    setEditing(null);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields().catch(() => null);
    if (!values) return; // 校验未通过，表单已显示字段错误
    const payload = { ...values, color: selectedColor };
    if (editing) {
      await updateRuleSet.mutateAsync({ id: editing.id, data: payload });
      message.success('更新成功');
    } else {
      await createRuleSet.mutateAsync(payload);
      message.success('创建成功');
    }
    closeModal();
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0 }}>业务线管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
          新建业务线
        </Button>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 120 }}>
          <Spin size="large" />
        </div>
      ) : ruleSets.length === 0 ? (
        <Empty description="暂无业务线，请新建" style={{ padding: 120 }} />
      ) : (
        <Row gutter={[16, 16]}>
          {ruleSets.map((rs) => (
            <Col key={rs.id} xs={24} sm={12} md={8} lg={6}>
              <Card
                hoverable
                style={{ borderTop: `4px solid ${rs.color}` }}
                onClick={() => navigate(`/rule-sets/${rs.id}`)}
                actions={[
                  <EditOutlined
                    key="edit"
                    onClick={(e) => {
                      e.stopPropagation();
                      openEditModal(rs);
                    }}
                  />,
                  <Popconfirm
                    key="delete"
                    title="确定删除？"
                    onConfirm={(e) => {
                      e?.stopPropagation();
                      deleteRuleSet.mutate(rs.id, {
                        onSuccess: () => message.success('删除成功'),
                      });
                    }}
                    onCancel={(e) => e?.stopPropagation()}
                  >
                    <DeleteOutlined
                      onClick={(e) => e.stopPropagation()}
                    />
                  </Popconfirm>,
                ]}
              >
                <Card.Meta
                  title={<span style={{ fontSize: 16 }}>{rs.name}</span>}
                  description={
                    <div>
                      <div style={{ marginBottom: 12, color: '#666', minHeight: 40 }}>
                        {rs.description || '暂无描述'}
                      </div>
                      <Statistic title="规则数量" value={rs.rule_count ?? 0} valueStyle={{ fontSize: 24 }} />
                    </div>
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}

      <Modal
        title={editing ? '编辑业务线' : '新建业务线'}
        open={modalOpen}
        onCancel={closeModal}
        onOk={handleSubmit}
        confirmLoading={createRuleSet.isPending || updateRuleSet.isPending}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入业务线名称' }]}
          >
            <Input placeholder="请输入业务线名称" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>

          <Form.Item label="颜色">
            <Space wrap>
              {PRESET_COLORS.map((c) => (
                <div
                  key={c}
                  onClick={() => {
                    setSelectedColor(c);
                    form.setFieldsValue({ color: c });
                  }}
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 6,
                    backgroundColor: c,
                    cursor: 'pointer',
                    border: selectedColor === c ? '3px solid #000' : '3px solid #e0e0e0',
                    transition: 'border 0.2s, transform 0.15s',
                    transform: selectedColor === c ? 'scale(1.15)' : 'scale(1)',
                  }}
                />
              ))}
            </Space>
          </Form.Item>

          <Form.Item name="color" hidden>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
