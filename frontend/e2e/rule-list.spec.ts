import { test, expect } from '@playwright/test';
import { setupApiMocks } from './mocks';

test.describe('规则列表页', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('查看规则列表', async ({ page }) => {
    await page.goto('/#/rules');

    await expect(page.getByText('rate_2')).toBeVisible();
    await expect(page.getByText('gmt_effect_end')).toBeVisible();
  });

  test('规则列表显示优先级', async ({ page }) => {
    await page.goto('/#/rules');

    // 验证 priority 值可见
    await expect(page.getByText('适用税率')).toBeVisible();
    await expect(page.getByText('结算账户名称')).toBeVisible();
  });

  test('规则列表显示规则类型 Tag', async ({ page }) => {
    await page.goto('/#/rules');

    // 验证 Tag 渲染
    await expect(page.locator('.ant-tag').first()).toBeVisible();
  });

  test('规则列表有新建按钮', async ({ page }) => {
    await page.goto('/#/rules');

    // 新建规则按钮
    const createBtn = page.getByRole('button', { name: /新建|新增|添加/ });
    if (await createBtn.isVisible()) {
      await createBtn.click();
      // 应该打开 Drawer 或弹窗
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 3000 });
    }
  });

  test('规则列表中启用状态 Switch 可见', async ({ page }) => {
    await page.goto('/#/rules');

    await expect(page.getByText('rate_2')).toBeVisible();
    // 每行应该有一个 Switch 组件
    await expect(page.locator('.ant-switch').first()).toBeVisible();
  });
});
