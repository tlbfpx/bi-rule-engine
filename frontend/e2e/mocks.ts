/**
 * E2E 测试共享 Mock 数据和 API 路由拦截器
 *
 * 重要：Playwright page.route 的 glob 模式无法可靠匹配带查询参数的 URL，
 * 因此这里使用单个正则 catch-all 路由，在内部按 path + method 分发。
 */

// ── Mock 数据 ───────────────────────��──────────────────

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

// ── 辅助函数 ────────────────────────────────────────────

const EMPTY_PAGINATED = { items: [], total: 0, page: 1, page_size: 20 };

/**
 * 从完整 URL 中提取 /api/v1 下的路径（不含查询参数）
 */
function apiPath(url: string): string {
  const u = new URL(url);
  return u.pathname.replace('/api/v1', '');
}

/**
 * JSON 响应快捷函数
 */
function json(route: import('@playwright/test').Route, data: unknown) {
  return route.fulfill({ status: 200, contentType: 'application/json', json: data });
}

/**
 * 设置 API 路由拦截 — 拦截所有 /api/v1 请求并返回 mock 数据
 *
 * 使用单个正则 catch-all 路由，在内部按 path + method 分发，
 * 避免 glob 模式无法匹配带查询参数 URL 的问题。
 */
export async function setupApiMocks(page: import('@playwright/test').Page) {
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

  // 单个 catch-all 路由处理所有 /api/v1 请求
  await page.route(/\/api\/v1\//, async (route) => {
    const request = route.request();
    const method = request.method();
    const path = apiPath(request.url());
    const body = () => request.postDataJSON();

    try {
      // ── 认证 ──
      if (path === '/auth/login' && method === 'POST') {
        return json(route, {
          access_token: 'mock-jwt-token',
          token_type: 'bearer',
          expires_in: 86400,
          username: 'admin',
          role: 'admin',
          display_name: '管理员',
        });
      }

      if (path === '/auth/me') {
        return json(route, { id: 'u1', username: 'admin', role: 'admin', display_name: '管理员', enabled: true });
      }

      if (path === '/auth/change-password') {
        return json(route, { ok: true });
      }

      // ── 规则集 ──
      if (path === '/rule-sets') {
        if (method === 'GET') return json(route, mockRuleSets);
        if (method === 'POST') {
          const b = body();
          return json(route, {
            id: 'rs_new', name: b?.name || '新业务线', description: b?.description || null,
            color: b?.color || '#1677ff', sort_order: 99, enabled: true, rule_count: 0,
            created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
          });
        }
      }

      if (path === '/rule-sets/all') {
        return json(route, { items: mockRuleSets.items });
      }

      // /rule-sets/:id
      const rsMatch = path.match(/^\/rule-sets\/(.+)$/);
      if (rsMatch) {
        const id = rsMatch[1];
        if (method === 'DELETE') return json(route, { id });
        if (method === 'PUT') {
          const b = body();
          return json(route, {
            id, name: b?.name || '更新后', description: b?.description,
            color: b?.color || '#1677ff', sort_order: 1, enabled: true, rule_count: 0,
            created_at: '2024-01-01T00:00:00', updated_at: new Date().toISOString(),
          });
        }
        // GET /rule-sets/:id
        const rs = mockRuleSets.items.find((r) => r.id === id);
        return json(route, rs || mockRuleSets.items[0]);
      }

      // ── 数据源 ──
      if (path === '/data-sources') {
        if (method === 'GET') return json(route, mockDataSources);
        return json(route, {
          id: 'ds_new', name: '新数据源', description: '', enabled: true,
          db_host: 'localhost', db_port: 3306, db_name: 'new_db', db_username: 'root',
          extract_mode: 'table', extract_sql: null, extract_table: 'new_table',
          incremental_column: null, incremental_value: null,
          created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
        });
      }

      if (path === '/data-sources/all') {
        return json(route, {
          items: mockDataSources.items.map((d) => ({ id: d.id, name: d.name, enabled: d.enabled })),
        });
      }

      if (path === '/data-sources/test-connection') {
        return json(route, { ok: true });
      }

      // /data-sources/:id 或 /data-sources/:id/preview
      const dsMatch = path.match(/^\/data-sources\/([^/]+)(\/preview)?$/);
      if (dsMatch) {
        if (dsMatch[2] === '/preview') {
          return json(route, { columns: [], rows: [] });
        }
        if (method === 'DELETE') return json(route, {});
        return json(route, mockDataSources.items[0]);
      }

      // ── 目标表 ──
      if (path === '/target-tables') {
        if (method === 'POST') {
          const b = body();
          return json(route, { ...mockTargetTables.items[0], ...b, id: 'tt_new' });
        }
        return json(route, mockTargetTables);
      }

      if (path === '/target-tables/all') {
        return json(route, {
          items: mockTargetTables.items.map((t) => ({ id: t.id, name: t.name, enabled: t.enabled })),
        });
      }

      // /target-tables/:id
      const ttMatch = path.match(/^\/target-tables\/(.+)$/);
      if (ttMatch) {
        const id = ttMatch[1];
        if (method === 'DELETE') return json(route, {});
        if (method === 'PUT') {
          const b = body();
          return json(route, { ...mockTargetTables.items[0], ...b, id });
        }
        return json(route, mockTargetTables.items[0]);
      }

      // ── ETL 任务 ──
      if (path === '/etl-jobs') {
        if (method === 'POST') {
          const b = body();
          return json(route, { ...mockETLJobs.items[0], ...b, id: 'etl_new' });
        }
        return json(route, mockETLJobs);
      }

      // /etl-jobs/:id 或 /etl-jobs/:id/runs 或 /etl-jobs/runs
      const etlMatch = path.match(/^\/etl-jobs\/(.+)$/);
      if (etlMatch) {
        const subPath = etlMatch[1];
        // /etl-jobs/runs (执行历史)
        if (subPath === 'runs' || subPath.startsWith('runs/')) {
          return json(route, EMPTY_PAGINATED);
        }
        // /etl-jobs/:id/runs
        if (subPath.includes('/runs')) {
          return json(route, EMPTY_PAGINATED);
        }
        // /etl-jobs/:id/trigger
        if (subPath.endsWith('/trigger')) {
          return json(route, { id: subPath.split('/')[0], status: 'running' });
        }
        // /etl-jobs/:id
        const id = subPath;
        if (method === 'DELETE') return json(route, {});
        if (method === 'PUT') {
          const b = body();
          return json(route, { ...mockETLJobs.items[0], ...b, id });
        }
        return json(route, mockETLJobs.items[0]);
      }

      // ── 规则 ──
      if (path === '/rules' || path.startsWith('/rules/')) {
        if (method === 'POST') {
          const b = body();
          return json(route, { ...mockRules.items[0], ...b, id: 'rule_new' });
        }
        if (method === 'PUT' && path.startsWith('/rules/')) {
          const id = path.split('/').pop()!;
          const b = body();
          return json(route, { ...mockRules.items[0], ...b, id });
        }
        if (method === 'DELETE' && path.startsWith('/rules/')) {
          return json(route, { ok: true });
        }
        return json(route, mockRules);
      }

      // ── 规则优先级排序 ──
      if (path === '/rules/batch-priority' && method === 'PUT') {
        return json(route, { ok: true });
      }

      // ── 查找表 ──
      if (path === '/lookup-tables') {
        if (method === 'POST') {
          const b = body();
          return json(route, {
            id: 'lt_new', name: b?.name || '新映射表', description: '',
            source_type: 'manual', columns: { key_col: 'key', value_col: 'value' },
            data: {}, created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
          });
        }
        return json(route, mockLookupTables);
      }

      // /lookup-tables/:id 或 /lookup-tables/:id/data
      const ltMatch = path.match(/^\/lookup-tables\/([^/]+)(\/data)?$/);
      if (ltMatch) {
        if (ltMatch[2] === '/data') {
          if (method === 'PUT') return json(route, { ok: true });
          return json(route, { data: mockLookupTables.items[0].data });
        }
        if (method === 'DELETE') return json(route, {});
        if (method === 'PUT') {
          const b = body();
          return json(route, { ...mockLookupTables.items[0], ...b });
        }
        return json(route, mockLookupTables.items[0]);
      }

      // ── 查找表上传 ──
      if (path === '/lookup-tables/upload') {
        return json(route, { id: 'lt_uploaded', columns: { key_col: 'key', value_col: 'value' }, data: {} });
      }

      // ── 任务中心 ──
      if (path === '/tasks' || path.startsWith('/tasks/')) {
        return json(route, EMPTY_PAGINATED);
      }

      // ── 执行任务（上传执行等）──
      if (path === '/execution-tasks' || path.startsWith('/execution-tasks/')) {
        return json(route, EMPTY_PAGINATED);
      }

      // ── 错误上报 ──
      if (path === '/logs/frontend-error') {
        return json(route, { ok: true });
      }

      // ── 健康检查 ──
      if (path === '/health' || path === '/../health') {
        return json(route, { status: 'ok', database: { ok: true }, redis: { ok: true } });
      }

      // ── 未匹配的 API — 返回空分页而非让请求落到 proxy ──
      console.warn(`[MOCK FALLBACK] Unmatched API: ${method} ${path}`);
      return json(route, EMPTY_PAGINATED);
    } catch (e) {
      console.error(`[MOCK ERROR] ${method} ${path}:`, e);
      return json(route, EMPTY_PAGINATED);
    }
  });
}
