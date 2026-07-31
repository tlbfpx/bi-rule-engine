import { test, expect } from '@playwright/test';

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
    // 预设认证信息
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('auth-store', JSON.stringify({
        state: {
          token: 'mock-jwt-token',
          username: 'admin',
          role: 'admin',
          displayName: '管理员',
          isAuthenticated: true,
        },
        version: 0,
      }));
    });

    // Mock API
    await page.route('**/api/v1/rule-sets', (route) => {
      route.fulfill({
        json: {
          items: [{ id: 'rs_1', name: '测试业务线', description: '', color: '#1677ff', sort_order: 1, enabled: true, rule_count: 0, created_at: '2024-01-01', updated_at: '2024-01-01' }],
          total: 1, page: 1, page_size: 20,
        },
      });
    });
    await page.route('**/api/v1/rule-sets/all', (route) => {
      route.fulfill({ json: { items: [] } });
    });
    await page.route('**/api/v1/rules**', (route) => {
      route.fulfill({ json: { items: [], total: 0, page: 1, page_size: 20 } });
    });
    await page.route('**/api/v1/logs/frontend-error', (route) => {
      route.fulfill({ json: { ok: true } });
    });

    await page.reload();

    // 应该在规则集页面
    await expect(page).toHaveURL(/#\/rule-sets/, { timeout: 5000 });
  });
});
