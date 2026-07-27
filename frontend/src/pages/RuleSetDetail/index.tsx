import { useParams } from 'react-router-dom';
import { Tabs, Typography, Spin } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { ruleSetsApi } from '../../api/ruleSets';
import RuleList from '../RuleList';
import DependencyDAG from '../DependencyDAG';

export default function RuleSetDetail() {
  const { id } = useParams<{ id: string }>();

  const { data: ruleSet, isLoading } = useQuery({
    queryKey: ['ruleSets', id],
    queryFn: () => ruleSetsApi.get(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  return (
    <div>
      <Typography.Title level={4} style={{ marginBottom: 16 }}>
        {ruleSet?.name || '加载中...'}
      </Typography.Title>

      <Tabs
        defaultActiveKey="rules"
        items={[
          {
            key: 'rules',
            label: '规则配置',
            children: <RuleList ruleSetId={id} />,
          },
          {
            key: 'dag',
            label: '依赖视图',
            children: <DependencyDAG ruleSetId={id} />,
          },
        ]}
      />
    </div>
  );
}
