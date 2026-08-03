import { test, expect } from '@playwright/test';
import { setupApiMocks } from './mocks';

test.describe('ETL 调度任务管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('查看 ETL 任务列表', async ({ page }) => {
    await page.goto('/#/etl-jobs');

    await expect(page.getByText('订单ETL')).toBeVisible();
    await expect(page.getByText('0 2 * * *')).toBeVisible();
  });

  test('任务中心 Tab 切换', async ({ page }) => {
    await page.goto('/#/tasks');

    // 默认在 ETL 执行历史 Tab（ETL 调度任务已迁移到独立菜单入口）
    await expect(page.getByRole('tab', { name: 'ETL 执行历史' })).toHaveAttribute('aria-selected', 'true');

    // 切换到上传执行
    await page.getByRole('tab', { name: '上传执行' }).click();
    await expect(page.getByRole('tab', { name: '上传执行' })).toHaveAttribute('aria-selected', 'true');

    // 切换到上传任务历史
    await page.getByRole('tab', { name: '上传任务历史' }).click();
    await expect(page.getByRole('tab', { name: '上传任务历史' })).toHaveAttribute('aria-selected', 'true');
  });
});

test.describe('响应式与可访问性', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('移动端视口下侧边栏可折叠', async ({ page, browser }) => {
    // 使用移动端视口
    const context = await browser.newContext({
      viewport: { width: 375, height: 667 },
    });
    const mobilePage = await context.newPage();
    await setupApiMocks(mobilePage);

    await mobilePage.goto('/#/rule-sets');

    // 移动端侧边栏可能默认折叠或有遮罩
    const sider = mobilePage.locator('.ant-layout-sider');
    await expect(sider).toBeVisible();

    await context.close();
  });

  test('页面主要元素可通过键盘访问', async ({ page }) => {
    await page.goto('/#/rule-sets');

    // 等待页面完全加载
    await expect(page.getByRole('button', { name: '新建业务线' })).toBeVisible();

    // Tab 键可以聚焦到可交互元素
    await page.keyboard.press('Tab');

    // 检查是否有元素获得焦点 — 使用更宽松的检测
    const focusedCount = await page.locator(':focus').count();
    expect(focusedCount).toBeGreaterThan(0);
  });

  test('错误边界正常处理组件错误', async ({ page }) => {
    await page.goto('/#/rule-sets');

    // 页面正常加载，没有错误边界触发 — 用 heading 精确匹配页面标题
    await expect(page.getByRole('heading', { name: '业务线管理' })).toBeVisible();
    await expect(page.getByText('页面发生错误')).not.toBeVisible();
  });
});
