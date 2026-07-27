import { test, expect } from '@playwright/test';
import { setupApiMocks, mockRuleSets } from './mocks';

test.describe('业务线管理（RuleSet）CRUD 全流程', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test('查看业务线列表', async ({ page }) => {
    await page.goto('/#/rule-sets');

    // 等待数据加载
    await expect(page.getByText('销售业务线')).toBeVisible();
    await expect(page.getByText('财务业务线')).toBeVisible();

    // 验证规则数量显示
    await expect(page.getByText('12')).toBeVisible();
    await expect(page.getByText('8')).toBeVisible();
  });

  test('新建业务线', async ({ page }) => {
    await page.goto('/#/rule-sets');

    await expect(page.getByText('销售业务线')).toBeVisible();

    // 点击新建按钮
    await page.getByRole('button', { name: '新建业务线' }).click();

    // 模态框出现
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('新建业务线').nth(1)).toBeVisible();

    // 填写表单
    await page.getByPlaceholder('请输入业务线名称').fill('测试新业务线');
    await page.getByPlaceholder('请输入描述').fill('E2E 测试创建的业务线');

    // 选择颜色（点击第二个颜色）
    const colorPicker = page.locator('.ant-space .ant-space-item').nth(1);
    await colorPicker.click();

    // 点击确定
    await page.getByRole('dialog').getByRole('button', { name: '确 定' }).click();

    // 模态框关闭
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 5000 });
  });

  test('编辑业务线', async ({ page }) => {
    await page.goto('/#/rule-sets');

    await expect(page.getByText('销售业务线')).toBeVisible();

    // 点击编辑按钮（第一个卡片的编辑图标）
    const firstCard = page.locator('.ant-card').first();
    await firstCard.getByRole('img', { name: 'edit' }).click();

    // 编辑模态框出现
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('编辑业务线')).toBeVisible();

    // 验证预填数据
    const nameInput = page.getByPlaceholder('请输入业务线名称');
    await expect(nameInput).toHaveValue('销售业务线');

    // 修改名称
    await nameInput.fill('销售业务线-已修改');

    // 点击确定
    await page.getByRole('dialog').getByRole('button', { name: '确 定' }).click();

    // 模态框关闭
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 5000 });
  });

  test('删除业务线', async ({ page }) => {
    await page.goto('/#/rule-sets');

    await expect(page.getByText('销售业务线')).toBeVisible();

    // 点击删除按钮（第一个卡片的删除图标）
    const firstCard = page.locator('.ant-card').first();
    await firstCard.getByRole('img', { name: 'delete' }).click();

    // 确认弹窗出现
    await expect(page.getByText('确定删除？')).toBeVisible();

    // 点击确定
    await page.locator('.ant-popover').getByRole('button', { name: '确 定' }).click();

    // 确认弹窗消失
    await expect(page.getByText('确定删除？')).not.toBeVisible({ timeout: 5000 });
  });

  test('点击业务线卡片跳转到详情页', async ({ page }) => {
    await page.goto('/#/rule-sets');

    await expect(page.getByText('销售业务线')).toBeVisible();

    // 点击第一个卡片
    await page.locator('.ant-card').first().click();

    // 跳转到详情页
    await expect(page).toHaveURL(/#\/rule-sets\/rs_1/);
  });
});
