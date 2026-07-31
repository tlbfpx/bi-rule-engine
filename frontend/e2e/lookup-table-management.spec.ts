import { test, expect } from '@playwright/test';
import { setupApiMocks } from './mocks';

test.describe('映射表管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('查看映射表列表', async ({ page }) => {
    await page.goto('/#/lookup-tables');

    await expect(page.getByText('税率映射表')).toBeVisible();
    await expect(page.getByText('产品段值映射')).toBeVisible();
  });

  test('搜索映射表', async ({ page }) => {
    await page.goto('/#/lookup-tables');

    await expect(page.getByText('税率映射表')).toBeVisible();

    // 搜索 "税率"
    await page.getByPlaceholder('搜索映射表').fill('税率');
    // 搜索结果应该仍然显示税率映射表
    await expect(page.getByText('税率映射表')).toBeVisible();
  });

  test('点击编辑按钮打开抽屉', async ({ page }) => {
    await page.goto('/#/lookup-tables');

    await expect(page.getByText('税率映射表')).toBeVisible();

    // 点击编辑按钮
    const firstRow = page.locator('tr').nth(1);
    await firstRow.getByRole('img', { name: 'edit' }).click();

    // Drawer 出现
    await expect(page.getByRole('dialog')).toBeVisible();
  });

  test('点击删除按钮弹出确认', async ({ page }) => {
    await page.goto('/#/lookup-tables');

    await expect(page.getByText('税率映射表')).toBeVisible();

    // 点击删除
    const firstRow = page.locator('tr').nth(1);
    await firstRow.getByRole('img', { name: 'delete' }).click();

    // 确认弹窗
    await expect(page.getByText(/确定删除/)).toBeVisible({ timeout: 5000 });
  });

  test('新建映射表按钮可见', async ({ page }) => {
    await page.goto('/#/lookup-tables');

    await expect(page.getByText('税率映射表')).toBeVisible();
    // 新建按钮（上传方式，可能是一个下拉或按钮）
    await expect(page.getByText('上传').first()).toBeVisible();
  });
});
