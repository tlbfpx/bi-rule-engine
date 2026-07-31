import { test, expect } from '@playwright/test';
import { setupApiMocks, mockRuleSets, mockRules } from './mocks';

test.describe('业务线详情页', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('查看业务线详情 - 规则配置 Tab', async ({ page }) => {
    await page.goto('/#/rule-sets/rs_1');

    // 业务线名称
    await expect(page.getByText('销售业务线')).toBeVisible();

    // 默认在"规则配置" Tab
    await expect(page.getByRole('tab', { name: '规则配置' })).toHaveAttribute('aria-selected', 'true');

    // 规则列表内容
    await expect(page.getByText('rate_2')).toBeVisible();
  });

  test('切换到依赖视图 Tab', async ({ page }) => {
    await page.goto('/#/rule-sets/rs_1');

    await expect(page.getByText('销售业务线')).toBeVisible();

    // 切换到依赖视图
    await page.getByRole('tab', { name: '依赖视图' }).click();
    await expect(page.getByRole('tab', { name: '依赖视图' })).toHaveAttribute('aria-selected', 'true');

    // ReactFlow 容器应该可见（规则列表有规则，DAG 应该渲染）
    // 可能显示规则节点或空状态提示
    const flowContainer = page.locator('.react-flow');
    const emptyText = page.getByText(/暂无|无依赖/);
    // 二选一：有 DAG 渲染或空提示
    await expect(flowContainer.or(emptyText)).toBeVisible({ timeout: 5000 });
  });
});
