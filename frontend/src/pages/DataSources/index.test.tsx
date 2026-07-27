import { describe, it, expect, beforeEach, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../test/utils';
import DataSources from './index';
import { dataSourcesApi } from '../../api/dataSources';

vi.mock('../../api/dataSources');

const mockDataSources = [
  {
    id: 'ds_1',
    name: '订单源库',
    description: '订单数据',
    enabled: true,
    db_host: '192.168.1.100',
    db_port: 3306,
    db_name: 'orders_db',
    db_username: 'reader',
    extract_mode: 'table' as const,
    extract_sql: null,
    extract_table: 'orders',
    incremental_column: 'create_time',
    incremental_value: '2024-01-01',
    created_at: '2024-01-01T00:00:00',
    updated_at: '2024-01-01T00:00:00',
  },
  {
    id: 'ds_2',
    name: '日志库',
    description: null,
    enabled: false,
    db_host: '10.0.0.5',
    db_port: 5432,
    db_name: 'logs_db',
    db_username: 'admin',
    extract_mode: 'sql' as const,
    extract_sql: 'SELECT * FROM logs WHERE level = "ERROR"',
    extract_table: null,
    incremental_column: null,
    incremental_value: null,
    created_at: '2024-01-02T00:00:00',
    updated_at: '2024-01-02T00:00:00',
  },
];

describe('DataSources 数据源管理页面', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(dataSourcesApi.list).mockResolvedValue({
      items: mockDataSources,
      total: 2,
      page: 1,
      page_size: 20,
    });
    vi.mocked(dataSourcesApi.create).mockResolvedValue(mockDataSources[0]);
    vi.mocked(dataSourcesApi.update).mockResolvedValue(mockDataSources[0]);
    vi.mocked(dataSourcesApi.delete).mockResolvedValue({} as never);
    vi.mocked(dataSourcesApi.testConnection).mockResolvedValue({ ok: true });
  });

  // ============ 列表渲染 ============

  it('渲染数据源表格', async () => {
    renderWithProviders(<DataSources />);
    await waitFor(() => {
      expect(screen.getByText('订单源库')).toBeInTheDocument();
    });
    expect(screen.getByText('日志库')).toBeInTheDocument();
  });

  it('显示数据库、主机等列', async () => {
    renderWithProviders(<DataSources />);
    await waitFor(() => {
      expect(screen.getByText('订单源库')).toBeInTheDocument();
    });
    expect(screen.getByText('orders_db')).toBeInTheDocument();
    expect(screen.getByText('192.168.1.100')).toBeInTheDocument();
  });

  it('extract_mode 正确渲染为中文标签', async () => {
    renderWithProviders(<DataSources />);
    await waitFor(() => {
      expect(screen.getByText('表名')).toBeInTheDocument();
    });
    expect(screen.getByText('自定义 SQL')).toBeInTheDocument();
  });

  it('enabled 状态正确渲染为 Tag', async () => {
    renderWithProviders(<DataSources />);
    await waitFor(() => {
      expect(screen.getByText('启用')).toBeInTheDocument();
    });
    expect(screen.getByText('停用')).toBeInTheDocument();
  });

  it('incremental_column 为 null 时显示"-"', async () => {
    renderWithProviders(<DataSources />);
    await waitFor(() => {
      expect(screen.getByText('订单源库')).toBeInTheDocument();
    });
    const cells = screen.getAllByText('-');
    expect(cells.length).toBeGreaterThan(0);
  });

  // ============ 分页 ============

  it('显示总数信息', async () => {
    renderWithProviders(<DataSources />);
    await waitFor(() => {
      expect(screen.getByText(/共 2 个数据源/)).toBeInTheDocument();
    });
  });

  // ============ 新建数据源 ============

  it('点击"新建数据源"按钮打开 Drawer', async () => {
    const user = userEvent.setup();
    renderWithProviders(<DataSources />);
    await waitFor(() => {
      expect(screen.getByText('订单源库')).toBeInTheDocument();
    });

    // 用 button role 精确匹配（排除 Drawer 标题）
    await user.click(screen.getByRole('button', { name: /新建数据源/ }));

    // 等待 Drawer 出现
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('数据源名称')).toBeInTheDocument();
  });

  it('表单包含所有必填字段', async () => {
    const user = userEvent.setup();
    renderWithProviders(<DataSources />);
    await waitFor(() => {
      expect(screen.getByText('订单源库')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新建数据源/ }));

    const dialog = await screen.findByRole('dialog');
    // 在 Drawer 内查找表单项标签
    expect(within(dialog).getByText('数据源名称')).toBeInTheDocument();
    expect(within(dialog).getByText('主机')).toBeInTheDocument();
    expect(within(dialog).getByText('端口')).toBeInTheDocument();
    expect(within(dialog).getByText('数据库')).toBeInTheDocument();
    expect(within(dialog).getByText('用户名')).toBeInTheDocument();
    expect(within(dialog).getByText('密码')).toBeInTheDocument();
    expect(within(dialog).getByText('抽取方式')).toBeInTheDocument();
  });

  // ============ 编辑数据源 ============

  it('点击编辑按钮打开 Drawer 并预填数据', async () => {
    const user = userEvent.setup();
    renderWithProviders(<DataSources />);
    await waitFor(() => {
      expect(screen.getByText('订单源库')).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole('img', { name: /edit/i });
    await user.click(editButtons[0]);

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('编辑数据源')).toBeInTheDocument();

    const nameInput = within(dialog).getByDisplayValue('订单源库') as HTMLInputElement;
    expect(nameInput.value).toBe('订单源库');
  });

  // ============ 抽取方式联动 ============

  it('选择"表名抽取"时显示源表名输入框', async () => {
    const user = userEvent.setup();
    renderWithProviders(<DataSources />);
    await waitFor(() => {
      expect(screen.getByText('订单源库')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新建数据源/ }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('源表名')).toBeInTheDocument();
  });

  // ============ 删除 ============

  it('点击删除按钮弹出确认框', async () => {
    const user = userEvent.setup();
    renderWithProviders(<DataSources />);
    await waitFor(() => {
      expect(screen.getByText('订单源库')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole('img', { name: /delete/i });
    await user.click(deleteButtons[0]);

    // Modal.confirm 也渲染为 dialog
    const confirmDialog = await screen.findByRole('dialog');
    expect(within(confirmDialog).getByText(/确定删除数据源 "订单源库" 吗？/)).toBeInTheDocument();
  });
});
