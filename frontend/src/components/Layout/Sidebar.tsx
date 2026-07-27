import { Layout, Menu, Typography } from 'antd';
import {
  BookOutlined,
  ExperimentOutlined,
  DatabaseOutlined,
  TableOutlined,
  ScheduleOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAppStore } from '../../stores/appStore';

const { Sider } = Layout;

const menuItems = [
  { key: '/rule-sets', icon: <AppstoreOutlined />, label: '业务线管理' },
  { key: '/lookup-tables', icon: <BookOutlined />, label: '映射表管理' },
  { key: '/data-sources', icon: <DatabaseOutlined />, label: '数据源管理' },
  { key: '/target-tables', icon: <TableOutlined />, label: '目标表管理' },
  { key: '/etl-jobs', icon: <ScheduleOutlined />, label: 'ETL 调度任务' },
  { key: '/tasks', icon: <ExperimentOutlined />, label: '任务中心' },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const collapsed = useAppStore((s) => s.sidebarCollapsed);

  const selectedKey = '/' + location.pathname.split('/')[1];

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={() => useAppStore.getState().toggleSidebar()}
      theme="dark"
      width={200}
      style={{ minHeight: '100vh' }}
    >
      <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography.Title level={4} style={{ color: '#fff', margin: 0, whiteSpace: 'nowrap' }}>
          {collapsed ? 'BI' : 'BI 规则引擎'}
        </Typography.Title>
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[selectedKey]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
      />
    </Sider>
  );
}
