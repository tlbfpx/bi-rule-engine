import { test, expect } from '@playwright/test';
import { setupApiMocks } from './mocks';

test.describe('目标表管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('查看目标表列表', async ({ page }) => {
    await page.goto('/#/target-tables');

    await expect(page.getByText('订单目标表')).toBeVisible();
    await expect(page.getByText('dwd_orders')).toBeVisible();
    await expect(page.getByText('bi_warehouse')).toBeVisible();
  });

  test('验证写入模式列渲染', async ({ page }) => {
    await page.goto('/#/target-tables');

    await expect(page.getByText('更新插入')).toBeVisible();
  });

  test('验证自动建表列渲染', async ({ page }) => {
    await page.goto('/#/target-tables');

    // auto_create_table: false → 显示"否" Tag
    await expect(page.locator('.ant-tag-default').first()).toBeVisible();
  });

  test('新建目标表 - 打开 Drawer', async ({ page }) => {
    await page.goto('/#/target-tables');

    await expect(page.getByText('订单目标表')).toBeVisible();

    await page.getByRole('button', { name: '新建目标表' }).click();
    const drawer = page.getByRole('dialog');
    await expect(drawer).toBeVisible();
    await expect(drawer.getByText('新建目标表')).toBeVisible();

    // 验证表单字段（通过 dialog 内文本匹配）
    await expect(drawer.getByText('配置名称')).toBeVisible();
    await expect(drawer.getByText('主机', { exact: true })).toBeVisible();
    await expect(drawer.getByText('端口', { exact: true })).toBeVisible();
    await expect(drawer.getByText('数据库', { exact: true })).toBeVisible();
    await expect(drawer.getByText('用户名', { exact: true })).toBeVisible();
    await expect(drawer.getByText('密码', { exact: true })).toBeVisible();
    await expect(drawer.getByText('目标表名')).toBeVisible();
    await expect(drawer.getByText('写入模式')).toBeVisible();
  });

  test('编辑目标表 - 预填数据', async ({ page }) => {
    await page.goto('/#/target-tables');

    await expect(page.getByText('订单目标表')).toBeVisible();

    const firstRow = page.locator('tr').nth(1);
    await firstRow.getByRole('img', { name: 'edit' }).click();

    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('编辑目标表')).toBeVisible();
    await expect(page.getByPlaceholder('例如：清洗后订单表')).toHaveValue('订单目标表');
  });

  test('删除目标表 - 确认弹窗', async ({ page }) => {
    await page.goto('/#/target-tables');

    await expect(page.getByText('订单目标表')).toBeVisible();

    const firstRow = page.locator('tr').nth(1);
    await firstRow.getByRole('button', { name: '删除' }).click();

    // 确认弹窗 — Modal.confirm 弹出后等待 primary 确认按钮
    const confirmBtn = page.locator('.ant-modal-confirm-btns button.ant-btn-primary');
    await confirmBtn.waitFor({ state: 'visible', timeout: 10000 });
    await confirmBtn.click();
  });

  test('分页信息正确', async ({ page }) => {
    await page.goto('/#/target-tables');
    await expect(page.getByText(/共 1 个目标表/)).toBeVisible();
  });
});
