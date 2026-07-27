# BI 规则引擎前端 - 测试系统搭建报告

## 概述

为 BI 规则引擎前端系统搭建了完整的测试体系，从零开始建立了 **Vitest 单元/组件测试** 和 **Playwright E2E 测试** 两层测试架构。

**测试结果：123 个单元/组件测试全部通过，0 失败。**

---

## 测试基础设施

### 技术栈
| 层级 | 工具 | 版本 |
|------|------|------|
| 单元/组件测试 | Vitest + jsdom | 4.1.10 |
| 组件渲染 | @testing-library/react | 16.3.2 |
| 用户交互模拟 | @testing-library/user-event | 14.6.1 |
| DOM 断言 | @testing-library/jest-dom | 7.0.0 |
| E2E 测试 | @playwright/test | 1.61.1 |
| 覆盖率 | @vitest/coverage-v8 | 4.1.10 |
| HTML 报告 | @vitest/ui | 4.1.10 |

### 配置文件
- `vitest.config.ts` — Vitest 配置（jsdom 环境、全局 API、覆盖率）
- `playwright.config.ts` — Playwright 配置（Chromium、自动启动 dev server）
- `src/test/setup.ts` — 测试全局 setup（jest-dom matchers、jsdom polyfill、antd message mock）
- `src/test/utils.tsx` — 测试工具（renderWithProviders 自动包裹 QueryClient/Router/ConfigProvider）

### npm scripts
```json
"test": "vitest run",
"test:watch": "vitest",
"test:coverage": "vitest run --coverage",
"test:e2e": "playwright test",
"test:e2e:ui": "playwright test --ui"
```

---

## 测试文件清单

### 单元测试 — 纯逻辑模块（56 tests）

| 文件 | 测试数 | 覆盖内容 |
|------|--------|----------|
| `src/utils/logger.test.ts` | 11 | traceId 管理（set/get/clear/异常容错）、错误上报 fetch 请求、initLogger |
| `src/stores/appStore.test.ts` | 8 | sidebarCollapsed 初始状态、toggleSidebar 切换、setState/getState |
| `src/stores/ruleStore.test.ts` | 37 | 规则编辑器全量操作：openEditor/closeEditor/resetEditor、条件组 CRUD、条件行 CRUD、清洗步骤 CRUD、查找配置 CRUD、公式/默认值 |

### 组件测试 — UI 交互（21 tests）

| 文件 | 测试数 | 覆盖内容 |
|------|--------|----------|
| `src/components/ErrorBoundary.test.tsx` | 5 | 正常渲染、错误捕获、重试恢复、自定义 fallback、错误信息展示 |
| `src/components/Layout/Sidebar.test.tsx` | 5 | 标题渲染、菜单项完整性、点击导航、路由高亮、折叠状态 |
| `src/pages/RuleSetManager/index.test.tsx` | 10 | 列表渲染、空状态、新建/编辑/删除 CRUD、表单校验、卡片点击跳转 |
| `src/pages/DataSources/index.test.tsx` | 11 | 表格渲染、中文标签/Tag、分页、Drawer 表单、编辑预填、抽取方式联动、删除确认 |

### API 层测试（46 tests）

| 文件 | 测试数 | 覆盖内容 |
|------|--------|----------|
| `src/api/client.test.ts` | 11 | axios 配置、请求拦截器（trace_id 注入）、响应拦截器（trace_id 提取）、错误处理 |
| `src/api/rules.test.ts` | 9 | rulesApi 全方法（list/get/create/update/delete/batchPriority/test） |
| `src/api/ruleSets.test.ts` | 7 | ruleSetsApi 全方法（list/all/get/create/update/delete） |
| `src/api/dataSources.test.ts` | 9 | dataSourcesApi 全方法（list/listAll/get/create/update/delete/testConnection/preview） |

### E2E 测试（Playwright，已编写未运行）

| 文件 | 测试场景 |
|------|----------|
| `e2e/app-navigation.spec.ts` | 应用加载、默认路由、侧边栏菜单、页面导航、折叠/展开、未知路由重定向 |
| `e2e/rule-set-crud.spec.ts` | 业务线列表、新建、编辑、删除、卡片跳转 |
| `e2e/data-source-management.spec.ts` | 数据源列表、新建 Drawer、编辑预填、测试连接、删除 |
| `e2e/etl-and-misc.spec.ts` | ETL 任务列表、任务中心 Tab 切换、响应式、键盘可访问性 |

---

## 发现的问题

### 1. RuleSetManager handleSubmit 未捕获表单校验异常（中）
- **位置**：`src/pages/RuleSetManager/index.tsx` 第 57-68 行
- **现象**：`handleSubmit` 中 `await form.validateFields()` 在校验失败时抛出 rejection，但 Modal 的 `onOk` 回调不会捕获这个 rejection，导致 unhandled promise rejection
- **影响**：用户点击"确定"但表单未填写必填项时，控制台出现未捕获异常
- **建议**：在 `handleSubmit` 中添加 try/catch

---

## 测试金字塔覆盖

```
        /\
       /  \         E2E (Playwright)
      /----\        4 spec files, ~25 scenarios
     /      \
    /--------\      组件测试 (RTL)
   /          \     21 tests
  /------------\
 /              \    单元测试 (Vitest)
/________________\   102 tests
```

- **单元测试**：102 tests（83%）— 纯逻辑模块 + API 层
- **组件测试**：21 tests（17%）— 关键 UI 组件交互
- **E2E 测试**：~25 scenarios — 核心用户旅程（已编写，待实际环境运行）

---

## 下一步建议

1. **运行 E2E 测试**：在本地开发环境中运行 `npm run test:e2e`，需要后端服务运行或使用 API mock
2. **补充覆盖率**：当前因沙箱限制未能生成覆盖率报告，建议在 CI 环境中运行 `npm run test:coverage`
3. **扩展组件测试**：RuleEditor 的复杂表单（条件构建器、公式编辑器、清洗配置）需要更深入的测试
4. **修复 handleSubmit**：为 RuleSetManager 和 DataSources 的提交函数添加 try/catch
5. **视觉回归测试**：考虑添加 Playwright 截图对比，覆盖跨浏览器适配
