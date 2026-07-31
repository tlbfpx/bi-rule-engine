import { Layout, Menu, Typography, Button, Space } from 'antd';
import {
  BookOutlined,
  ExperimentOutlined,
  DatabaseOutlined,
  TableOutlined,
  ScheduleOutlined,
  AppstoreOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAppStore } from '../../stores/appStore';
import { useAuthStore } from '../../stores/authStore';

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
  const username = useAuthStore((s) => s.username);
  const logout = useAuthStore((s) => s.logout);

  const selectedKey = '/' + location.pathname.split('/')[1];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={(isCollapsed) => useAppStore.getState().setSidebarCollapsed(isCollapsed)}
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
      {!collapsed && (
        <div
          style={{
            position: 'absolute',
            bottom: 56,
            left: 0,
            right: 0,
            padding: '0 16px',
          }}
        >
          <Space direction="vertical" style={{ width: '100%' }} size={4}>
            <Typography.Text style={{ color: '#aaa', fontSize: 12, display: 'block', textAlign: 'center' }}>
              {username || '未知用户'}
            </Typography.Text>
            <Button
              icon={<LogoutOutlined />}
              size="small"
              block
              onClick={handleLogout}
              style={{ fontSize: 12 }}
            >
              退出登录
            </Button>
          </Space>
        </div>
      )}
    </Sider>
  );
}
