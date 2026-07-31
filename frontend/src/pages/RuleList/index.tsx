import { useState } from 'react';
import {
  Table, Button, Space, Tag, Switch, Input, Select, Popconfirm,
  Tooltip, Typography, Card,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, CopyOutlined,
  ExperimentOutlined, ArrowUpOutlined, ArrowDownOutlined,
  ApartmentOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { useRules, useDeleteRule, useUpdateRule, useBatchPriority } from '../../hooks/useRules';
import { useAllRuleSets } from '../../hooks/useRuleSets';
import { useRuleEditorStore } from '../../stores/ruleStore';
import type { Rule, RuleType } from '../../types';
import RuleEditorDrawer from '../RuleEditor';
import RuleTestModal from '../RuleTest';
import { RULE_TYPE_TAG, RULE_TYPE_OPTIONS } from '../../utils/ruleLabels';

const { Search } = Input;

// 过滤器比基础选项多一个「全部类型」
const FILTER_TYPE_OPTIONS: { value: RuleType | ''; label: string }[] = [
  { value: '', label: '全部类型' },
  ...RULE_TYPE_OPTIONS,
];

interface RuleListProps {
  ruleSetId?: string;
}

export default function RuleList({ ruleSetId }: RuleListProps = {}) {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchField, setSearchField] = useState('');
  const [filterType, setFilterType] = useState<RuleType | ''>('');
  const [filterEnabled, setFilterEnabled] = useState<boolean | undefined>();
  const [filterRuleSetId, setFilterRuleSetId] = useState<string | undefined>(ruleSetId);

  const { data: ruleSets } = useAllRuleSets();

  const { data, isLoading } = useRules({
    page,
    page_size: pageSize,
    field_name: searchField || undefined,
    rule_type: filterType || undefined,
    enabled: filterEnabled,
    rule_set_id: filterRuleSetId,
  });

  const deleteRule = useDeleteRule();
  const updateRule = useUpdateRule();
  const batchPriority = useBatchPriority();
  const openEditor = useRuleEditorStore((s) => s.openEditor);

  // 测试面板状态
  const [testRuleId, setTestRuleId] = useState<string | null>(null);
  // 跟踪正在更新中的规则 ID，只对对应行显示 loading
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const handleToggle = async (rule: Rule) => {
    setTogglingId(rule.id);
    try {
      await updateRule.mutateAsync({ id: rule.id, data: { enabled: !rule.enabled } });
    } finally {
      setTogglingId(null);
    }
  };

  const handleCopy = (rule: Rule) => {
    openEditor({
      rule_set_id: rule.rule_set_id,
      field_name: `${rule.field_name}_copy`,
      field_label: rule.field_label,
      rule_type: rule.rule_type,
      priority: (data?.items?.length || 0) + 1,
      enabled: false,
      description: rule.description,
      depends_on: rule.depends_on,
      config: rule.config,
    });
  };

  const handleMovePriority = (rule: Rule, direction: 'up' | 'down') => {
    const items = data?.items || [];
    const idx = items.findIndex((r) => r.id === rule.id);
    if (idx === -1) return;
    const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
    if (swapIdx < 0 || swapIdx >= items.length) return;

    const updates = [
      { id: items[idx].id, priority: items[swapIdx].priority },
      { id: items[swapIdx].id, priority: items[idx].priority },
    ];
    batchPriority.mutate(updates);
  };

  const columns = [
    {
      title: '字段名',
      dataIndex: 'field_name',
      key: 'field_name',
      width: 180,
      render: (text: string) => <Typography.Text code>{text}</Typography.Text>,
    },
    {
      title: '字段标签',
      dataIndex: 'field_label',
      key: 'field_label',
      width: 140,
      ellipsis: true,
    },
    {
      title: '规则类型',
      dataIndex: 'rule_type',
      key: 'rule_type',
      width: 110,
      render: (t: RuleType) => {
        const cfg = RULE_TYPE_TAG[t] || { color: 'default', label: t };
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: '业务线',
      dataIndex: 'rule_set_id',
      key: 'rule_set_id',
      width: 120,
      render: (_: unknown, r: Rule) => {
        if (!r.rule_set_id) return '-';
        const rs = ruleSets?.items?.find((s) => s.id === r.rule_set_id);
        return <Tag color={rs?.color}>{r.rule_set_name || rs?.name || r.rule_set_id}</Tag>;
      },
    },
    {
      title: '条件数',
      key: 'condition_count',
      width: 80,
      render: (_: unknown, r: Rule) => r.config?.conditions?.length || 0,
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      sorter: true,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled: boolean, rule: Rule) => (
        <Switch
          size="small"
          checked={enabled}
          onChange={() => handleToggle(rule)}
          loading={togglingId === rule.id}
        />
      ),
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
      width: 240,
      render: (_: unknown, rule: Rule) => (
        <Space size="small">
          <Tooltip title="上移">
            <Button size="small" icon={<ArrowUpOutlined />} onClick={() => handleMovePriority(rule, 'up')} />
          </Tooltip>
          <Tooltip title="下移">
            <Button size="small" icon={<ArrowDownOutlined />} onClick={() => handleMovePriority(rule, 'down')} />
          </Tooltip>
          <Tooltip title="编辑">
            <Button size="small" type="primary" icon={<EditOutlined />} onClick={() => openEditor(rule)} />
          </Tooltip>
          <Tooltip title="测试">
            <Button size="small" icon={<ExperimentOutlined />} onClick={() => setTestRuleId(rule.id)} />
          </Tooltip>
          <Tooltip title="复制">
            <Button size="small" icon={<CopyOutlined />} onClick={() => handleCopy(rule)} />
          </Tooltip>
          <Popconfirm
            title="确认删除此规则？"
            onConfirm={() => deleteRule.mutate(rule.id)}
            okText="删除"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space wrap>
            <Search
              placeholder="搜索字段名"
              allowClear
              style={{ width: 200 }}
              onSearch={setSearchField}
              onChange={(e) => !e.target.value && setSearchField('')}
            />
            <Select
              value={filterType}
              onChange={setFilterType}
              options={FILTER_TYPE_OPTIONS}
              style={{ width: 130 }}
            />
            {!ruleSetId && (
              <Select
                value={filterRuleSetId}
                onChange={setFilterRuleSetId}
                allowClear
                placeholder="全部业务线"
                options={(ruleSets?.items || []).map((s) => ({
                  value: s.id,
                  label: s.name,
                })) || []}
                style={{ width: 150 }}
              />
            )}
            <Select
              value={filterEnabled}
              onChange={setFilterEnabled}
              options={[
                { value: undefined, label: '全部状态' },
                { value: true, label: '已启用' },
                { value: false, label: '已停用' },
              ]}
              style={{ width: 110 }}
            />
          </Space>
          <Space>
            <Button icon={<ApartmentOutlined />} onClick={() => navigate('/dag')}>
              依赖视图
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => openEditor(ruleSetId ? { rule_set_id: ruleSetId } : undefined)}>
              新建规则
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
            pageSize,
            total: data?.total || 0,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条规则`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); },
          }}
          size="middle"
        />
      </Card>

      <RuleEditorDrawer />
      {testRuleId && (
        <RuleTestModal
          ruleId={testRuleId}
          open={!!testRuleId}
          onClose={() => setTestRuleId(null)}
        />
      )}
    </div>
  );
}
