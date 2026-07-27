import { useState } from 'react';
import { Card, Tabs } from 'antd';
import TaskList from './TaskList';
import UploadPanel from './UploadPanel';
import ETLJobRuns from '../ETLJobRuns';

export default function TaskCenter() {
  const [activeTab, setActiveTab] = useState('etl-runs');

  return (
    <Card>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'etl-runs',
            label: 'ETL 执行历史',
            children: <ETLJobRuns embedded />,
          },
          {
            key: 'upload',
            label: '上传执行',
            children: <UploadPanel />,
          },
          {
            key: 'history',
            label: '上传任务历史',
            children: <TaskList />,
          },
        ]}
      />
    </Card>
  );
}
