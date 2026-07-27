import { describe, it, expect, beforeEach, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../test/utils';
import RuleSetManager from './index';
import { ruleSetsApi } from '../../api/ruleSets';

// ── Mock API ──
vi.mock('../../api/ruleSets');

const mockRuleSets = [
  {
    id: 'rs_1',
    name: '销售业务线',
    description: '销售数据规则集',
    color: '#1677ff',
    sort_order: 1,
    enabled: true,
    rule_count: 12,
    created_at: '2024-01-01T00:00:00',
    updated_at: '2024-01-01T00:00:00',
  },
  {
    id: 'rs_2',
    name: '财务业务线',
    description: '财务数据规则集',
    color: '#52c41a',
    sort_order: 2,
    enabled: true,
    rule_count: 8,
    created_at: '2024-01-02T00:00:00',
    updated_at: '2024-01-02T00:00:00',
  },
  {
    id: 'rs_3',
    name: '无描述业务线',
    description: null,
    color: '#fa8c16',
    sort_order: 3,
    enabled: false,
    rule_count: 0,
    created_at: '2024-01-03T00:00:00',
    updated_at: '2024-01-03T00:00:00',
  },
];

// 辅助函数：在 dialog 内查找元素
function getDialog() {
  return screen.getByRole('dialog');
}

describe('RuleSetManager 业务线管理页面', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(ruleSetsApi.list).mockResolvedValue({
      items: mockRuleSets,
      total: 3,
      page: 1,
      page_size: 20,
    });
    vi.mocked(ruleSetsApi.create).mockResolvedValue(mockRuleSets[0]);
    vi.mocked(ruleSetsApi.update).mockResolvedValue(mockRuleSets[0]);
    vi.mocked(ruleSetsApi.delete).mockResolvedValue(mockRuleSets[0]);

    // 抑制表单校验失败导致的 unhandled rejection
    // （Ant Design Modal 的 onOk 不捕获异步回调的 rejection）
    window.addEventListener('unhandledrejection', (e) => {
      if (e.reason?.errorFields) e.preventDefault();
    });
  });

  // ============ 加载状态 ============

  it('加载时显示加载指示器', async () => {
    vi.mocked(ruleSetsApi.list).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({
        items: mockRuleSets, total: 3, page: 1, page_size: 20,
      }), 100))
    );
    renderWithProviders(<RuleSetManager />);
    const spinner = document.querySelector('.ant-spin');
    expect(spinner).toBeInTheDocument();
  });

  // ============ 列表渲染 ============

  it('加载后渲染所有业务线卡片', async () => {
    renderWithProviders(<RuleSetManager />);
    await waitFor(() => {
      expect(screen.getByText('销售业务线')).toBeInTheDocument();
    });
    expect(screen.getByText('财务业务线')).toBeInTheDocument();
    expect(screen.getByText('无描述业务线')).toBeInTheDocument();
  });

  it('显示每条业务线的规则数量', async () => {
    renderWithProviders(<RuleSetManager />);
    await waitFor(() => {
      expect(screen.getByText('12')).toBeInTheDocument();
    });
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('description 为 null 时显示"暂无描述"', async () => {
    renderWithProviders(<RuleSetManager />);
    await waitFor(() => {
      expect(screen.getByText('暂无描述')).toBeInTheDocument();
    });
  });

  // ============ 空状态 ============

  it('无数据时显示 Empty 提示', async () => {
    vi.mocked(ruleSetsApi.list).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });
    renderWithProviders(<RuleSetManager />);
    await waitFor(() => {
      expect(screen.getByText('暂无业务线，请新建')).toBeInTheDocument();
    });
  });

  // ============ 创建业务线 ============

  it('点击"新建业务线"按钮打开模态框', async () => {
    const user = userEvent.setup();
    renderWithProviders(<RuleSetManager />);
    await waitFor(() => {
      expect(screen.getByText('销售业务线')).toBeInTheDocument();
    });

    // 用 button role + name 精确匹配按钮（排除 Modal 标题）
    await user.click(screen.getByRole('button', { name: /新建业务线/ }));

    // 等待模态框出现
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('名称')).toBeInTheDocument();
    expect(within(dialog).getByText('描述')).toBeInTheDocument();
  });

  it('填写表单并提交创建业务线', async () => {
    const user = userEvent.setup();
    renderWithProviders(<RuleSetManager />);
    await waitFor(() => {
      expect(screen.getByText('销售业务线')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新建业务线/ }));

    const dialog = await screen.findByRole('dialog');
    const nameInput = within(dialog).getByPlaceholderText('请输入业务线名称');
    await user.type(nameInput, '新业务线');

    const descInput = within(dialog).getByPlaceholderText('请输入描述');
    await user.type(descInput, '测试描述');

    // Ant Design Modal 的确认按钮文本是"确 定"（有空格）
    const okButton = within(dialog).getByRole('button', { name: /确/ });
    await user.click(okButton);

    // React Query useMutation 会给 mutationFn 传额外参数，
    // 所以只检查第一个参数
    await waitFor(() => {
      expect(ruleSetsApi.create).toHaveBeenCalled();
      const callArgs = vi.mocked(ruleSetsApi.create).mock.calls[0];
      expect(callArgs[0]).toMatchObject({
        name: '新业务线',
        description: '测试描述',
      });
    });
  });

  it('名称为空时表单校验不通过', async () => {
    const user = userEvent.setup();
    renderWithProviders(<RuleSetManager />);
    await waitFor(() => {
      expect(screen.getByText('销售业务线')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /新建业务线/ }));

    const dialog = await screen.findByRole('dialog');
    // 直接点击确定（不填写名称）
    const okButton = within(dialog).getByRole('button', { name: /确/ });
    await user.click(okButton);

    await waitFor(() => {
      expect(screen.getByText('请输入业务线名称')).toBeInTheDocument();
    });
    expect(ruleSetsApi.create).not.toHaveBeenCalled();
  });

  // ============ 编辑业务线 ============

  it('点击编辑图标打开编辑模态框并预填数据', async () => {
    const user = userEvent.setup();
    renderWithProviders(<RuleSetManager />);
    await waitFor(() => {
      expect(screen.getByText('销售业务线')).toBeInTheDocument();
    });

    // 点击第一个卡片的编辑按钮
    const editButtons = screen.getAllByRole('img', { name: /edit/i });
    await user.click(editButtons[0]);

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('编辑业务线')).toBeInTheDocument();
    const nameInput = within(dialog).getByPlaceholderText('请输入业务线名称') as HTMLInputElement;
    expect(nameInput.value).toBe('销售业务线');
  });

  // ============ 删除业务线 ============

  it('点击删除图标弹出确认框，确认后调用删除 API', async () => {
    const user = userEvent.setup();
    renderWithProviders(<RuleSetManager />);
    await waitFor(() => {
      expect(screen.getByText('销售业务线')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole('img', { name: /delete/i });
    await user.click(deleteButtons[0]);

    // Popconfirm 渲染为 tooltip 弹层，等待"确定删除？"文本出现
    const confirmText = await screen.findByText('确定删除？');
    expect(confirmText).toBeInTheDocument();

    // 在 Popconfirm 中找到确定按钮
    const popconfirm = confirmText.closest('.ant-popover');
    const okButton = within(popconfirm!).getByRole('button', { name: /确/ });
    await user.click(okButton);

    await waitFor(() => {
      expect(ruleSetsApi.delete).toHaveBeenCalled();
      const callArgs = vi.mocked(ruleSetsApi.delete).mock.calls[0];
      expect(callArgs[0]).toBe('rs_1');
    });
  });
});
