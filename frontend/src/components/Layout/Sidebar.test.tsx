import { describe, it, expect, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../test/utils';
import Sidebar from './Sidebar';
import { useAppStore } from '../../stores/appStore';

describe('Sidebar 侧边栏', () => {
  beforeEach(() => {
    useAppStore.setState({ sidebarCollapsed: false });
  });

  it('渲染标题"BI 规则引擎"', () => {
    renderWithProviders(<Sidebar />);
    expect(screen.getByText('BI 规则引擎')).toBeInTheDocument();
  });

  it('渲染所有菜单项', () => {
    renderWithProviders(<Sidebar />);
    expect(screen.getByText('业务线管理')).toBeInTheDocument();
    expect(screen.getByText('映射表管理')).toBeInTheDocument();
    expect(screen.getByText('数据源管理')).toBeInTheDocument();
    expect(screen.getByText('目标表管理')).toBeInTheDocument();
    expect(screen.getByText('ETL 调度任务')).toBeInTheDocument();
    expect(screen.getByText('任务中心')).toBeInTheDocument();
  });

  it('点击菜单项触发路由导航', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Sidebar />, { initialEntries: ['/rule-sets'] });

    await user.click(screen.getByText('数据源管理'));
    // Ant Design 选中菜单项会添加 ant-menu-item-selected class
    const menuItem = screen.getByText('数据源管理').closest('li');
    expect(menuItem?.className).toContain('ant-menu-item-selected');
  });

  it('根据当前路径高亮对应菜单项', () => {
    renderWithProviders(<Sidebar />, { initialEntries: ['/data-sources'] });
    const menuItem = screen.getByText('数据源管理').closest('li');
    expect(menuItem?.className).toContain('ant-menu-item-selected');
  });

  it('折叠时标题显示"BI"', () => {
    useAppStore.setState({ sidebarCollapsed: true });
    renderWithProviders(<Sidebar />);
    expect(screen.getByText('BI')).toBeInTheDocument();
  });
});
