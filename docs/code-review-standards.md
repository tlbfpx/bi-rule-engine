# BI 规则引擎 — 代码审查标准与流程

> 版本: 1.0 | 制定日期: 2026-07-29 | 适用范围: 全体前端 (React/TypeScript) 与后端 (Python/FastAPI) 代码

---

## 一、审查原则

1. **对事不对人** — 审查的是代码，不是写代码的人。评论针对代码行为，不评价个人能力
2. **证据驱动** — 每条意见附带"为什么"，避免"我觉得不好"式的主观判断
3. **分级聚焦** — 阻塞项必须修复才能合并；建议项应尽量修复；细节项可讨论后决定
4. **安全第一** — 任何安全相关问题（注入、XSS、敏感信息泄露）一律为阻塞项
5. **教学导向** — 审查是知识传递的机会，发现好代码要表扬，发现可改进的写法要解释原因
6. **及时响应** — PR 提交后 4 小时内开始审查，24 小时内完成（紧急热修除外）

---

## 二、严重程度分级

### 🔴 Blocker（阻塞项 — 必须修复才能合并）

| 类别 | 说明 |
|------|------|
| **安全漏洞** | SQL 注入、XSS、eval() 未沙箱化、敏感信息硬编码、未授权访问 |
| **数据风险** | 数据丢失/损坏、事务未提交、并发写入冲突、缺少幂等性保障 |
| **逻辑错误** | 核心功能不工作、API 契约变更未向后兼容、条件判断错误 |
| **崩溃风险** | 空指针/KeyError 未处理、异步异常未捕获、资源泄漏（连接/文件未关闭）|
| **缺失关键测试** | 核心业务逻辑路径无测试覆盖 |

### 🟡 Suggestion（建议项 — 应修复，可讨论替代方案）

| 类别 | 说明 |
|------|------|
| **输入校验缺失** | API 参数未校验范围/格式、前端表单未校验 |
| **命名/可读性** | 变量名含义模糊、函数过长（>80 行）、嵌套层级过深（>3 层）|
| **性能隐患** | N+1 查询、大列表未分页、不必要的全量渲染、React 缺少 key/memo |
| **重复代码** | 超过 20 行的重复逻辑应抽取为函数或组件 |
| **错误处理不足** | 只捕获不处理（`except: pass`）、未给用户友好提示 |
| **类型安全** | 滥用 `any`/`Optional`、后端缺少类型注解 |

### 💭 Nit（细节项 — 可选，不阻塞合并）

| 类别 | 说明 |
|------|------|
| **风格一致性** | 命名风格不统一、import 顺序、注释格式 |
| **文档补充** | 公共函数缺少 docstring/JSDoc、复杂逻辑缺少注释 |
| **替代方案** | "也可以考虑用 X 方式实现" 级别的建议 |
| **微小优化** | 可合并的变量声明、可简化的条件表达式 |

---

## 三、前端代码审查标准 (React + TypeScript)

### 3.1 安全性

```
🔴 检查项
├── dangerouslySetInnerHTML 是否经过 XSS 消毒？
├── 用户输入是否直接拼接到 URL / 模板字符串中？
├── API 请求是否携带鉴权 token？
├── 敏感信息（密码、token）是否出现在前端日志或 state 中？
└── 第三方依赖是否执行 npm audit 检查？
```

### 3.2 React 最佳实践

```
🟡 检查项
├── 列表渲染是否使用稳定的 key（非数组索引）？
├── useEffect 依赖数组是否完整？是否有不必要的依赖？
├── 组件是否合理拆分？（单个组件 < 300 行为佳）
├── 状态是否放在合适的层级？（能用局部 state 就不用全局 store）
├── 是否存在 prop drilling 超过 3 层的情况？
├── useMemo/useCallback 是否用于昂贵计算/频繁渲染场景？
└── 自定义 Hook 是否以 use 开头并遵循 Rules of Hooks？
```

### 3.3 TypeScript 类型安全

```
🟡 检查项
├── 是否避免使用 any？（用 unknown + 类型守卫替代）
├── API 响应是否定义了 TypeScript 接口/类型？
├── 是否存在 @ts-ignore / @ts-noindex？（需注释原因）
├── 联合类型是否使用了可辨识联合（discriminated union）？
└── 公共工具函数是否有明确的类型签名？
```

### 3.4 数据请求与状态管理

```
🟡 检查项
├── React Query 的 queryKey 是否合理设计？（包含所有动态参数）
├── mutation 后是否 invalidate 相关 queryKey？
├── 加载/错误状态是否正确处理？（Skeleton / ErrorBoundary / message）
├── Zustand store 是否避免存储派生数据？（派生数据用 selector 计算）
├── 异步操作是否有 loading 状态反馈？
└── 表单提交是否 try/catch 校验异常？（已知问题：RuleSetManager、DataSources）
```

### 3.5 性能

```
🟡 检查项
├── 是否存在不必要的全量 re-render？（检查 React DevTools Profiler）
├── 大数据表格是否使用虚拟滚动？
├── 图片/组件是否按需加载？（React.lazy / dynamic import）
├── ECharts/Monaco 等重型组件是否延迟初始化？
└── useMemo/useCallback 是否过度使用？（简单值不需要 memoize）
```

### 3.6 测试

```
🔴/🟡 检查项
├── 🔴 核心业务逻辑（规则编辑、ETL 调度）是否有单元测试？
├── 🟡 新增 API hook 是否有对应的测试？
├── 🟡 关键交互流程是否有 E2E 测试覆盖？
├── 🟡 测试是否模拟了错误场景？（网络失败、空数据、权限不足）
└── 💭 测试命名是否清晰描述了被测行为？
```

---

## 四、后端代码审查标准 (Python + FastAPI)

### 4.1 安全性

```
🔴 检查项
├── SQL 查询是否使用参数化？（禁止字符串拼接 SQL）
├── eval() / exec() 是否有沙箱限制？（公式引擎需审查 __builtins__ 限制）
├── 密码/密钥是否加密存储？（crypto.py 的 AES 加密是否正确使用）
├── API 端点是否有权限校验？（deps.py 依赖注入是否覆盖所有路由）
├── 用户输入是否经过 Pydantic schema 校验？
├── 文件上传是否校验类型/大小限制？
└── 日志是否泄露敏感信息？（密码、token、SQL 参数值）
```

### 4.2 数据库操作

```
🔴/🟡 检查项
├── 🔴 写操作是否在事务中？是否处理了回滚？
├── 🟡 是否存在 N+1 查询？（关联查询应用 selectinload/joinedload）
├── 🟡 查询是否添加了 LIMIT？（防止全表扫描返回大量数据）
├── 🟡 ORM 模型变更是否生成了 Alembic 迁移脚本？
├── 🟡 动态属性注入（如 r.rule_set_name = ...）是否有类型标注？
└── 💭 查询是否使用了合适的索引？
```

### 4.3 异步与并发

```
🔴/🟡 检查项
├── 🔴 async 函数中是否误用了同步阻塞操作？（如 requests.get、time.sleep）
├── 🔴 异步异常是否被正确捕获和传播？
├── 🟡 是否避免在 async 函数中直接使用 asyncio.run()？
├── 🟡 共享状态是否考虑了并发安全？（APScheduler 任务并发执行）
├── 🟡 Redis 操作是否有超时和重试机制？
└── 🟡 WebSocket 连接是否处理了断开重连？
```

### 4.4 错误处理

```
🟡 检查项
├── 是否避免 bare except / except Exception 不记录日志？
├── API 错误是否返回结构化的错误响应？（error_code + message）
├── 业务异常是否使用自定义异常类而非返回 None？
├── 关键操作是否有 try/finally 确保资源释放？
└── 日志是否包含 trace_id 以便追踪？
```

### 4.5 性能

```
🟡 检查项
├── Polars DataFrame 操作是否避免不必要的 collect()？
├── 大数据量 ETL 是否有分批处理 / 内存控制？
├── 缓存策略是否合理？（TTL、缓存失效、缓存穿透防护）
├── 是否存在循环中创建数据库连接的情况？
└── 重量级计算是否可以移到后台任务？
```

### 4.6 代码组织与风格

```
🟡/💭 检查项
├── 🟡 路由函数是否只做参数校验和调用 service？（业务逻辑应在 service 层）
├── 🟡 函数长度是否合理？（< 80 行为佳，核心引擎可放宽）
├── 🟡 是否有重复的 CRUD 模式可以抽取为基类或工具函数？
├── 💭 docstring 风格是否统一？（建议统一使用 Google 风格）
├── 💭 import 是否按标准库/第三方/本地分组排序？
└── 💭 模块级常量是否使用 UPPER_SNAKE_CASE？
```

### 4.7 测试

```
🔴/🟡 检查项
├── 🔴 核心引擎（parser、executor、dependency、formula_engine）是否有完整测试？
├── 🟡 API 端点是否有集成测试？（使用 httpx.AsyncClient）
├── 🟡 测试是否使用 pytest 框架？（当前后端测试为原生脚本，需迁移）
├── 🟡 测试是否覆盖了异常路径？（空数据、非法输入、权限不足）
├── 🟡 测试是否有 fixtures 管理测试数据？
└── 💭 测试是否可在隔离环境运行？（不依赖外部服务）
```

---

## 五、通用审查标准

### 5.1 Git 提交规范

```
🟡 检查项
├── Commit message 是否遵循 Conventional Commits 格式？
│   └── 格式: <type>(<scope>): <subject>
│       type: feat | fix | docs | style | refactor | test | chore | perf
├── 单个 PR 是否只包含一个逻辑变更？（避免混合多个不相关功能）
├── PR 是否基于最新的 main 分支？（避免合并冲突）
└── 是否删除了调试代码？（console.log、print、注释掉的代码块）
```

### 5.2 文档与配置

```
🟡/💭 检查项
├── 🟡 API 变更是否更新了 OpenAPI schema / 前端类型定义？
├── 🟡 新增环境变量是否更新了 .env.example 和部署文档？
├── 🟡 数据库结构变更是否有对应的迁移脚本？
├── 💭 复杂算法是否有注释说明思路？
└── 💭 README / CLAUDE.md 是否需要同步更新？
```

---

## 六、代码审查流程

### 6.1 角色与职责

| 角色 | 职责 |
|------|------|
| **作者 (Author)** | 自审 → 创建 PR → 填写 PR 模板 → 根据审查意见修改 |
| **审查者 (Reviewer)** | 在规定时间内完成审查 → 使用分级标记评论 → 确认修复后 approve |
| **第三审查者 (Optional)** | 当 PR 涉及核心引擎/安全/数据库迁移时，需要第二位审查者 approve |

### 6.2 PR 提交前自审清单

作者在提交 PR 前，必须完成以下自审：

- [ ] 本地 `npm run lint && npm run build` 通过（前端）
- [ ] 本地 `ruff check . && mypy .` 通过（后端，工具配置后）
- [ ] 本地 `npm run test` 通过（前端）
- [ ] 本地 `pytest` 通过（后端，迁移后）
- [ ] 无 `console.log` / `print` 调试残留
- [ ] 无注释掉的代码块
- [ ] PR 描述完整填写（变更说明、测试方式、影响范围）
- [ ] 截图/录屏（UI 变更必须附）

### 6.3 审查流程步骤

```
步骤 1: 作者创建 PR，分配至少 1 名审查者
  └── 涉及核心引擎/安全/DB 迁移 → 需 2 名审查者

步骤 2: 审查者在 4 小时内开始审查，24 小时内完成
  └── 使用 GitHub PR Review 功能，逐文件审查
  └── 每条意见标注 🔴/🟡/💭 级别
  └── 如有 🔴 阻塞项 → Request Changes
  └── 无阻塞项 → Approve

步骤 3: 作者根据审查意见修改代码，推送新 commit
  └── 对每条意见回复"已修复"或"讨论理由"
  └── 不要 force push（保留审查历史），除非审查者要求 squash

步骤 4: 审查者复审修改，确认所有 🔴 项已解决
  └── 全部解决 → Approve
  └── 仍有阻塞项 → 回到步骤 3

步骤 5: 合并
  └── 审查者或作者点击 Squash Merge
  └── 删除分支（如为 feature 分支）
  └── 合并后确认 CI 通过
```

### 6.4 紧急热修流程

```
hotfix 分支 → 最少 1 名审查者快速审查（可只审查 diff）→ 合并 → 部署
  └── 事后补充完整测试和文档
  └── 记录热修原因和影响范围
```

### 6.5 审查者分配规则

| PR 类型 | 最少审查者 | 特殊要求 |
|---------|-----------|---------|
| 普通功能/Bug 修复 | 1 人 | — |
| 核心引擎变更 (engine/) | 2 人 | 包含引擎模块负责人 |
| 安全相关（认证/加密/权限） | 2 人 | 包含安全审查清单 |
| 数据库迁移 (alembic/) | 2 人 | 验证 up/down 迁移均可执行 |
| 紧急热修 | 1 人 | 事后补充审查 |

---

## 七、自动化工具配置建议

### 7.1 前端（优先配置）

```jsonc
// .prettierrc — 统一代码格式
{
  "semi": true,
  "singleQuote": true,
  "trailingComma": "es5",
  "printWidth": 100,
  "tabWidth": 2
}
```

```jsonc
// .oxlintrc.json — 扩展 lint 规则
{
  "rules": {
    // 已有
    "react/rules-of-hooks": "error",
    "react/only-export-components": "warn",
    // 建议新增
    "react/jsx-key": "error",
    "react/no-array-index-key": "warn",
    "react/no-danger": "warn",
    "typescript/no-explicit-any": "warn",
    "typescript/no-unused-vars": "warn",
    "oxc/no-console": "warn"
  }
}
```

### 7.2 后端（优先配置）

```toml
# pyproject.toml — 新增 ruff + mypy 配置
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "SIM", "TCH"]
ignore = ["E501"]  # 行长度由 formatter 管理

[tool.ruff.lint.isort]
known-first-party = ["app"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
ignore_missing_imports = true  # 第三方库缺少 stub 时
```

### 7.3 CI/CD 流水线（建议添加 `.github/workflows/ci.yml`）

```yaml
name: CI
on: [pull_request]

jobs:
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22 }
      - run: cd frontend && npm ci
      - run: cd frontend && npm run lint
      - run: cd frontend && npm run build
      - run: cd frontend && npm run test

  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13" }
      - run: pip install ruff mypy
      - run: cd backend && ruff check .
      - run: cd backend && mypy app/
```

### 7.4 PR 模板（`.github/pull_request_template.md`）

```markdown
## 变更说明

<!-- 简要描述本次变更的内容和目的 -->

## 变更类型

- [ ] 新功能 (feat)
- [ ] Bug 修复 (fix)
- [ ] 重构 (refactor)
- [ ] 性能优化 (perf)
- [ ] 测试 (test)
- [ ] 文档 (docs)
- [ ] 其他 (chore)

## 测试方式

<!-- 描述如何测试本次变更 -->

## 影响范围

<!-- 列出可能受影响的功能模块 -->

## 自审清单

- [ ] 本地 lint + build 通过
- [ ] 本地测试通过
- [ ] 无调试代码残留
- [ ] PR 只包含一个逻辑变更
- [ ] 已更新相关文档/类型定义

## 截图/录屏（UI 变更必填）

<!-- 拖入截图 -->
```

---

## 八、审查评论参考模板

### 指出问题时

```
🔴 **安全: SQL 注入风险**
`backend/app/api/v1/rules.py` 第 42 行: 用户输入直接拼接进 SQL 查询。

**原因:** 攻击者可通过 name 参数注入 `'; DROP TABLE rules; --`。

**建议:**
使用参数化查询:
```python
result = await db.execute(text("SELECT * FROM rules WHERE name = :name"), {"name": name})
```
```

### 提出建议时

```
🟡 **可读性: 函数过长**
`ruleStore.ts` 的 `openEditor` 方法有 85 行，包含多个职责。

**原因:** 单个函数承担过多逻辑会增加维护难度和测试复杂度。

**建议:** 考虑拆分为 `resetEditorState()` + `loadRuleData()` 两个函数。
```

### 表扬好代码时

```
✅ **好的实践: trace_id 传播**
`middleware/logging.py` 中的 trace_id 中间件实现得很干净，贯穿了请求全生命周期，
配合前端的 error 上报机制，排查问题时可以快速定位。赞！
```

---

## 九、常见反模式速查

| 反模式 | 场景 | 正确做法 |
|--------|------|---------|
| `any` 类型 | API 响应直接用 any | 定义 TypeScript interface |
| `eval()` 无沙箱 | 公式引擎解析用户输入 | 限制 `__builtins__` + 白名单函数 |
| 数组 index 做 key | 列表渲染 `key={i}` | 使用唯一业务 ID |
| bare except | `except: pass` | 捕获具体异常 + 记录日志 |
| 同步阻塞 async | `requests.get()` in async 函数 | 使用 `httpx.AsyncClient` |
| 未 invalidate | mutation 后不刷新缓存 | `queryClient.invalidateQueries()` |
| 硬编码密钥 | DB 密码写死在代码中 | 环境变量 + crypto.py 加密 |
| 事务不回滚 | except 中忘记 `await db.rollback()` | try/except/finally 模式 |

---

## 十、审查指标与持续改进

### 建议跟踪的指标

| 指标 | 目标 | 说明 |
|------|------|------|
| PR 审查平均时长 | < 24 小时 | 从提交到合并 |
| 审查覆盖率 | 100% | 所有 PR 至少 1 人审查 |
| 阻塞项平均数量 | < 2 个/PR | 趋势下降说明自审质量提升 |
| 审查通过率 | > 70% 首次通过 | 一次 Request Changes 后合并 |
| 测试覆盖率 | > 70% | 核心模块 > 85% |

### 季度复盘

每季度回顾审查中发现的常见问题模式，更新本标准文档。识别需要补充工具自动化的领域（如新增 lint 规则），逐步减少人工审查中的重复性检查。
