import { test, expect } from '@playwright/test';
import { setupApiMocks } from './mocks';

test.describe('应用导航与页面加载', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('应用加载后默认跳转到业务线管理页面', async ({ page }) => {
    await page.goto('/');

    // HashRouter 路由，URL 应该包含 #/rule-sets
    await expect(page).toHaveURL(/#\/rule-sets/);

    // 页面标题可见
    await expect(page.getByRole('heading', { name: '业务线管理' })).toBeVisible();
  });

  test('侧边栏显示所有菜单项', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByText('业务线管理')).toBeVisible();
    await expect(page.getByText('映射表管理')).toBeVisible();
    await expect(page.getByText('数据源管理')).toBeVisible();
    await expect(page.getByText('目标表管理')).toBeVisible();
    await expect(page.getByText('ETL 调度任务')).toBeVisible();
    await expect(page.getByText('任务中心')).toBeVisible();
  });

  test('点击侧边栏菜单项可以导航到对应页面', async ({ page }) => {
    await page.goto('/');

    // 导航到数据源管理
    await page.getByRole('menuitem', { name: '数据源管理' }).click();
    await expect(page).toHaveURL(/#\/data-sources/);
    await expect(page.getByText('订单源库')).toBeVisible();

    // 导航到目标表管理
    await page.getByRole('menuitem', { name: '目标表管理' }).click();
    await expect(page).toHaveURL(/#\/target-tables/);

    // 导航到 ETL 调度任务
    await page.getByRole('menuitem', { name: 'ETL 调度任务' }).click();
    await expect(page).toHaveURL(/#\/etl-jobs/);
    await expect(page.getByText('订单ETL')).toBeVisible();

    // 导航到任务中心
    await page.getByRole('menuitem', { name: '任务中心' }).click();
    await expect(page).toHaveURL(/#\/tasks/);

    // 导航回业务线管理
    await page.getByRole('menuitem', { name: '业务线管理' }).click();
    await expect(page).toHaveURL(/#\/rule-sets/);
  });

  test('侧边栏可以折叠/展开', async ({ page }) => {
    await page.goto('/');

    // 初始状态：展开，显示"BI 规则引擎"
    await expect(page.getByText('BI 规则引擎')).toBeVisible();

    // 点击折叠触发器
    const sider = page.locator('.ant-layout-sider');
    const trigger = sider.locator('.ant-layout-sider-trigger');
    await trigger.click();

    // 折叠后：显示"BI"
    await expect(page.getByText('BI', { exact: true })).toBeVisible();
  });

  test('未知路由自动重定向到业务线管理', async ({ page }) => {
    await page.goto('/#/nonexistent-page');
    await expect(page).toHaveURL(/#\/rule-sets/);
  });

  test('页面标题包含"BI 规则引擎"', async ({ page }) => {
    await page.goto('/');
    const siderTitle = page.locator('.ant-typography').first();
    await expect(siderTitle).toContainText('BI 规则引擎');
  });
});
