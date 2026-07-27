import { test, expect } from '@playwright/test';
import { setupApiMocks } from './mocks';

test.describe('数据源管理 CRUD', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('查看数据源列表', async ({ page }) => {
    await page.goto('/#/data-sources');

    // 等待表格加载
    await expect(page.getByText('订单源库')).toBeVisible();
    await expect(page.getByText('orders_db')).toBeVisible();
    await expect(page.getByText('192.168.1.100')).toBeVisible();

    // 验证抽取方式渲染
    await expect(page.getByText('表名').first()).toBeVisible();

    // 验证状态 Tag
    await expect(page.locator('.ant-tag-success').first()).toBeVisible();

    // 验证分页信息
    await expect(page.getByText(/共 1 个数据源/)).toBeVisible();
  });

  test('新建数据源 - 打开 Drawer 并验证表单字段', async ({ page }) => {
    await page.goto('/#/data-sources');

    await expect(page.getByText('订单源库')).toBeVisible();

    // 点击新建
    await page.getByRole('button', { name: '新建数据源' }).click();

    // Drawer 出现
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('新建数据源').nth(1)).toBeVisible();

    // 验证表单字段
    await expect(page.getByText('数据源名称')).toBeVisible();
    await expect(page.getByText('主机')).toBeVisible();
    await expect(page.getByText('端口')).toBeVisible();
    await expect(page.getByText('数据库')).toBeVisible();
    await expect(page.getByText('用户名')).toBeVisible();
    await expect(page.getByText('密码')).toBeVisible();
    await expect(page.getByText('抽取方式')).toBeVisible();

    // 默认模式为表名抽取，显示"源表名"
    await expect(page.getByText('源表名')).toBeVisible();

    // 切换到自定义 SQL 模式
    await page.locator('.ant-select-selector').last().click();
    await page.getByText('自定义 SQL').click();
    await expect(page.getByText('抽取 SQL')).toBeVisible();
  });

  test('编辑数据源 - 预填数据', async ({ page }) => {
    await page.goto('/#/data-sources');

    await expect(page.getByText('订单源库')).toBeVisible();

    // 点击编辑按钮
    const firstRow = page.locator('tr').nth(1);
    await firstRow.getByRole('img', { name: 'edit' }).click();

    // Drawer 出现
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('编辑数据源')).toBeVisible();

    // 验证预填数据
    await expect(page.getByPlaceholder('例如：订单源库')).toHaveValue('订单源库');
  });

  test('测试连接功能', async ({ page }) => {
    await page.goto('/#/data-sources');

    await expect(page.getByText('订单源库')).toBeVisible();

    // 打开新建 Drawer
    await page.getByRole('button', { name: '新建数据源' }).click();
    await expect(page.getByRole('dialog')).toBeVisible();

    // 填写连接信息
    await page.getByPlaceholder('例如：订单源库').fill('测试连接');
    await page.getByPlaceholder('localhost').fill('192.168.1.100');
    await page.locator('input').filter({ hasText: '' }).nth(1).fill('3306');
    await page.locator('.ant-drawer input').filter({ hasText: '' }).nth(2).fill('test_db');
    await page.locator('.ant-drawer input').nth(3).fill('root');
    await page.locator('input[type="password"]').fill('password');

    // 点击测试连接按钮
    await page.getByRole('button', { name: '测试连接' }).click();

    // 等待成功提示
    await expect(page.getByText('连接成功')).toBeVisible({ timeout: 5000 });
  });

  test('删除数据源', async ({ page }) => {
    await page.goto('/#/data-sources');

    await expect(page.getByText('订单源库')).toBeVisible();

    // 点击删除按钮
    const firstRow = page.locator('tr').nth(1);
    await firstRow.getByRole('button', { name: '删除' }).click();

    // 确认弹窗
    await expect(page.getByText('确认删除')).toBeVisible();
    await expect(page.getByText(/确定删除数据源 "订单源库" 吗？/)).toBeVisible();

    // 点击确定
    await page.locator('.ant-modal-confirm').getByRole('button', { name: '确 定' }).click();
  });

  test('数据源列表分页信息正确', async ({ page }) => {
    await page.goto('/#/data-sources');

    await expect(page.getByText(/共 1 个数据源/)).toBeVisible();
  });
});
