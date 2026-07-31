/**
 * E2E 测试共享 Mock 数据和 API 路由拦截器
 */

export const mockRuleSets = {
  items: [
    {
      id: 'rs_1',
      name: '销售业务线',
      description: '销售数据规则集',
      color: '#1677ff',
      sort_order: 1,
      enabled: true,
      rule_count: 12,
      created_at: '2024-01-01T00:00:00',
      updated_at: '2024-01-01T00:00:00',
    },
    {
      id: 'rs_2',
      name: '财务业务线',
      description: '财务数据规则集',
      color: '#52c41a',
      sort_order: 2,
      enabled: true,
      rule_count: 8,
      created_at: '2024-01-02T00:00:00',
      updated_at: '2024-01-02T00:00:00',
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
};

export const mockDataSources = {
  items: [
    {
      id: 'ds_1',
      name: '订单源库',
      description: '订单数据',
      enabled: true,
      db_host: '192.168.1.100',
      db_port: 3306,
      db_name: 'orders_db',
      db_username: 'reader',
      extract_mode: 'table',
      extract_sql: null,
      extract_table: 'orders',
      incremental_column: 'create_time',
      incremental_value: '2024-01-01',
      created_at: '2024-01-01T00:00:00',
      updated_at: '2024-01-01T00:00:00',
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
};

export const mockTargetTables = {
  items: [
    {
      id: 'tt_1',
      name: '订单目标表',
      description: '订单数据目标表',
      enabled: true,
      db_host: '192.168.1.200',
      db_port: 3306,
      db_name: 'bi_warehouse',
      db_username: 'writer',
      table_name: 'dwd_orders',
      write_mode: 'upsert',
      upsert_keys: ['order_id'],
      auto_create_table: false,
      created_at: '2024-01-01T00:00:00',
      updated_at: '2024-01-01T00:00:00',
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
};

export const mockETLJobs = {
  items: [
    {
      id: 'etl_1',
      job_name: '订单ETL',
      description: '订单数据ETL任务',
      enabled: true,
      data_source_id: 'ds_1',
      target_table_id: 'tt_1',
      rule_set_id: null,
      cron_expression: '0 2 * * *',
      timezone: 'Asia/Shanghai',
      error_retry_count: 3,
      timeout_seconds: 3600,
      last_run_at: '2024-01-15T02:00:00',
      last_run_status: 'completed',
      last_run_error: null,
      created_at: '2024-01-01T00:00:00',
      updated_at: '2024-01-15T02:00:00',
      data_source: mockDataSources.items[0],
      target_table: mockTargetTables.items[0],
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
};

export const mockLookupTables = {
  items: [
    {
      id: 'lt_1',
      name: '税率映射表',
      description: '公司段到税率映射',
      source_type: 'manual',
      columns: { key_col: 'company_segment', value_col: 'rate' },
      data: { '930000': '0', '972400': '0.06' },
      created_at: '2024-01-01T00:00:00',
      updated_at: '2024-01-01T00:00:00',
    },
    {
      id: 'lt_2',
      name: '产品段值映射',
      description: '产品分类到段值',
      source_type: 'manual',
      columns: { key_col: 'product', value_col: 'segment' },
      data: { '团体体检': 'P10012', '集团体检': 'P10011' },
      created_at: '2024-01-02T00:00:00',
      updated_at: '2024-01-02T00:00:00',
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
};

export const mockRules = {
  items: [
    {
      id: 'rule_1',
      rule_set_id: 'rs_1',
      field_name: 'rate_2',
      field_label: '适用税率',
      rule_type: 'mapping',
      priority: 2,
      enabled: true,
      config: {
        conditions: [
          { id: 'cg_001', priority: 1, logic: 'AND', rows: [{ id: 'cr_001', field: 'company_segment_code', operator: 'in', value: ['930000', '840000'] }], result_type: 'constant', result_value: 0 },
        ],
        default_result: 0.06,
      },
      depends_on: ['company_segment_code'],
      description: '公司段值930000/840000为0',
      created_at: '2024-01-01T00:00:00',
      updated_at: '2024-01-01T00:00:00',
    },
    {
      id: 'rule_2',
      rule_set_id: 'rs_1',
      field_name: 'gmt_effect_end',
      field_label: '结算账户名称',
      rule_type: 'cleaning',
      priority: 1,
      enabled: true,
      config: { cleaning_steps: [{ action: 'fill_null', source_field: 'partner_name' }] },
      depends_on: [],
      description: '空值填充',
      created_at: '2024-01-01T00:00:00',
      updated_at: '2024-01-01T00:00:00',
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
};

/**
 * 设置 API 路由拦截 - 拦截所有 /api/v1 请求并返回 mock 数据
 */
export async function setupApiMocks(page: import('@playwright/test').Page) {
  // ── 认证 mock ──
  // 预设 localStorage 中的 auth token（绕过登录页）
  await page.addInitScript(() => {
    const authData = {
      state: {
        token: 'mock-jwt-token',
        username: 'admin',
        role: 'admin',
        displayName: '管理员',
        isAuthenticated: true,
      },
      version: 0,
    };
    localStorage.setItem('auth-store', JSON.stringify(authData));
  });

  // 认证 API
  await page.route('**/api/v1/auth/login', (route) => {
    if (route.request().method() === 'POST') {
      route.fulfill({
        json: {
          access_token: 'mock-jwt-token',
          token_type: 'bearer',
          expires_in: 86400,
          username: 'admin',
          role: 'admin',
          display_name: '管理员',
        },
      });
    }
  });

  await page.route('**/api/v1/auth/me', (route) => {
    route.fulfill({
      json: {
        id: 'u1',
        username: 'admin',
        role: 'admin',
        display_name: '管理员',
        enabled: true,
      },
    });
  });

  // 规则集
  await page.route('**/api/v1/rule-sets', (route) => {
    if (route.request().method() === 'GET') {
      route.fulfill({ json: mockRuleSets });
    } else if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON();
      route.fulfill({
        json: {
          id: 'rs_new',
          name: body?.name || '新业务线',
          description: body?.description || null,
          color: body?.color || '#1677ff',
          sort_order: 99,
          enabled: true,
          rule_count: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      });
    }
  });

  await page.route('**/api/v1/rule-sets/all', (route) => {
    route.fulfill({ json: { items: mockRuleSets.items } });
  });

  await page.route('**/api/v1/rule-sets/*', (route) => {
    const url = route.request().url();
    const id = url.split('/').pop();

    if (route.request().method() === 'DELETE') {
      route.fulfill({ json: { id } });
    } else if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON();
      route.fulfill({
        json: {
          id,
          name: body?.name || '更新后',
          description: body?.description,
          color: body?.color || '#1677ff',
          sort_order: 1,
          enabled: true,
          rule_count: 0,
          created_at: '2024-01-01T00:00:00',
          updated_at: new Date().toISOString(),
        },
      });
    } else {
      const rs = mockRuleSets.items.find((r) => r.id === id);
      route.fulfill({ json: rs || mockRuleSets.items[0] });
    }
  });

  // 数据源
  await page.route('**/api/v1/data-sources', (route) => {
    if (route.request().method() === 'GET') {
      route.fulfill({ json: mockDataSources });
    } else {
      route.fulfill({
        json: {
          id: 'ds_new',
          name: '新数据源',
          description: '',
          enabled: true,
          db_host: 'localhost',
          db_port: 3306,
          db_name: 'new_db',
          db_username: 'root',
          extract_mode: 'table',
          extract_sql: null,
          extract_table: 'new_table',
          incremental_column: null,
          incremental_value: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      });
    }
  });

  await page.route('**/api/v1/data-sources/all', (route) => {
    route.fulfill({
      json: {
        items: mockDataSources.items.map((d) => ({
          id: d.id,
          name: d.name,
          enabled: d.enabled,
        })),
      },
    });
  });

  await page.route('**/api/v1/data-sources/*', (route) => {
    if (route.request().method() === 'DELETE') {
      route.fulfill({ json: {} });
    } else if (route.request().method() === 'PUT') {
      route.fulfill({ json: mockDataSources.items[0] });
    } else {
      route.fulfill({ json: mockDataSources.items[0] });
    }
  });

  await page.route('**/api/v1/data-sources/test-connection', (route) => {
    route.fulfill({ json: { ok: true } });
  });

  // 目标表
  await page.route('**/api/v1/target-tables', (route) => {
    route.fulfill({ json: mockTargetTables });
  });

  await page.route('**/api/v1/target-tables/all', (route) => {
    route.fulfill({
      json: {
        items: mockTargetTables.items.map((t) => ({
          id: t.id,
          name: t.name,
          enabled: t.enabled,
        })),
      },
    });
  });

  await page.route('**/api/v1/target-tables/*', (route) => {
    if (route.request().method() === 'DELETE') {
      route.fulfill({ json: {} });
    } else {
      route.fulfill({ json: mockTargetTables.items[0] });
    }
  });

  // ETL 调度任务
  await page.route('**/api/v1/etl-jobs', (route) => {
    route.fulfill({ json: mockETLJobs });
  });

  await page.route('**/api/v1/etl-jobs/*', (route) => {
    if (route.request().method() === 'DELETE') {
      route.fulfill({ json: {} });
    } else {
      route.fulfill({ json: mockETLJobs.items[0] });
    }
  });

  // ETL 执行历史
  await page.route('**/api/v1/etl-jobs/runs**', (route) => {
    route.fulfill({
      json: {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
      },
    });
  });

  // 规则
  await page.route('**/api/v1/rules**', (route) => {
    route.fulfill({ json: mockRules });
  });

  // 字典表
  await page.route('**/api/v1/lookup-tables**', (route) => {
    if (route.request().method() === 'GET') {
      route.fulfill({ json: mockLookupTables });
    } else {
      route.fulfill({
        json: {
          id: 'lt_new',
          name: '新映射表',
          description: '',
          source_type: 'manual',
          columns: { key_col: 'key', value_col: 'value' },
          data: {},
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      });
    }
  });

  // 任务
  await page.route('**/api/v1/tasks**', (route) => {
    route.fulfill({
      json: {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
      },
    });
  });

  // 错误上报
  await page.route('**/api/v1/logs/frontend-error', (route) => {
    route.fulfill({ json: { ok: true } });
  });
}
