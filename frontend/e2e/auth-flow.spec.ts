import { test, expect } from '@playwright/test';
import { setupApiMocks } from './mocks';

test.describe('认证流程', () => {
  test('未登录时重定向到登录页', async ({ page }) => {
    // 清除 localStorage 中的认证信息
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();

    // 应该跳转到登录页
    await expect(page).toHaveURL(/#\/login/);
    await expect(page.getByText('BI 规则引擎')).toBeVisible();
    await expect(page.getByPlaceholder('用户名')).toBeVisible();
    await expect(page.getByPlaceholder('密码')).toBeVisible();
  });

  test('登录页面有默认账号提示', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();

    await expect(page.getByText('admin / admin123')).toBeVisible();
  });

  test('登录表单字段验证', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();

    // 空表单提交
    await page.getByRole('button', { name: /登 录|登录/ }).click();

    // 应该显示必填校验
    await expect(page.getByText('请输入用户名')).toBeVisible();
  });

  test('已登录状态下可以访问主页', async ({ page }) => {
    // setupApiMocks 会预设 localStorage auth token
    await setupApiMocks(page);

    await page.goto('/');
    await page.waitForTimeout(2000);

    // 应该在规则集页面
    await expect(page).toHaveURL(/#\/rule-sets/, { timeout: 5000 });
    await expect(page.getByRole('heading', { name: '业务线管理' })).toBeVisible();
  });
});
