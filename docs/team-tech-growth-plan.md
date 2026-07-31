# BI 规则引擎 — 团队技术提升方案

> 基于全量代码审查，提炼真实案例，制定分阶段技术成长计划
>
> 制定日期: 2026-07-29 | 审查范围: 前后端 16 个关键文件 | 发现问题: 35 项

---

## 一、代码审查发现总览

### 1.1 问题分布

| 严重度 | 后端 | 前端 | 合计 | 典型问题 |
|--------|------|------|------|---------|
| 严重 | 7 | 1 | 8 | SQL 注入、密码未编码、事件循环阻塞、弱密钥派生、全局 store 订阅 |
| 高 | 5 | 5 | 10 | N+1 查询、异常吞没、错误处理不统一、ErrorBoundary 设计缺陷 |
| 中 | 14 | 6 | 20 | 性能隐患、类型安全、事务管理、状态管理设计 |
| 低 | 9 | 2 | 11 | 代码风格、一致性、命名规范 |

### 1.2 技术能力短板画像

| 能力维度 | 当前水平 | 目标水平 | 差距分析 |
|---------|---------|---------|---------|
| **安全意识** | 初级 | 中级 | SQL 注入风险未识别、密码处理不规范、eval 沙箱理解不足 |
| **异步编程** | 初级 | 中级 | 事件循环阻塞、ORM 对象跨线程使用、并发 trace_id 覆盖 |
| **错误处理** | 初级 | 中级 | 异常静默吞没、错误处理策略不统一、缺乏组件级错误状态 |
| **性能优化** | 初级 | 中级 | N+1 查询、全量 store 订阅、list 全量物化、map_elements 滥用 |
| **类型安全** | 中级 | 中高级 | any 滥用、非空断言、ORM 动态属性、缺失类型标注 |
| **React 最佳实践** | 中级 | 高级 | selector 未使用、key 使用 index、useEffect 依赖缺失 |
| **架构设计** | 中级 | 高级 | 错误边界层级缺失、密钥迁移机制缺失、连接池管理 |

---

## 二、十大高危问题详解（教学案例）

以下每个案例都来自项目真实代码，可直接用于团队 Code Review 培训和技术分享会。

### 案例 1：SQL 注入 — 表名未经验证直接拼接

**文件**: `backend/app/engine/etl_runner.py` 第 128 行、161 行
**严重度**: 严重

```python
# 问题代码
create_sql = f"CREATE TABLE `{target.table_name}` ({', '.join(columns)})"
cur.execute(f"TRUNCATE TABLE `{target.table_name}`")
```

**问题分析**:
注释声称"表名已通过 `_safe_identifier` 在调用方验证"，但追溯完整调用链，**没有任何地方**对 `target.table_name` 调用了 `_safe_identifier`。如果用户在管理界面输入恶意的表名（如 `` users`; DROP TABLE `rules ``），反引号包裹无法防御这种注入。

**正确做法**:
```python
import re

def _safe_identifier(name: str) -> str:
    """验证 SQL 标识符，只允许字母、数字、下划线"""
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
        raise ValueError(f"非法标识符: {name}")
    return name

# 使用前必须验证
safe_name = _safe_identifier(target.table_name)
create_sql = f"CREATE TABLE `{safe_name}` ({', '.join(columns)})"
```

**教学要点**:
- 永远不要信任用户输入，即使有 UI 层校验
- 字符串拼接 SQL 时，标识符也需要验证
- 注释声称的安全保证必须有代码佐证

---

### 案例 2：数据库密码未 URL 编码

**文件**: `backend/app/engine/etl_runner.py` 第 68-72 行
**严重度**: 严重

```python
# 问题代码
connection_uri = (
    f"mysql+pymysql://{data_source.db_username}:{data_source.db_password}"
    f"@{data_source.db_host}:{data_source.db_port}/{data_source.db_name}"
    f"?charset=utf8mb4"
)
```

**问题分析**:
如果数据库密码包含 `@`、`:`、`/`、`#` 等 URL 特殊字符（企业环境很常见，如 `P@ssw0rd!`），连接 URI 会被错误解析。密码中的 `@` 会被误认为是用户名/密码与主机名的分隔符。

**正确做法**:
```python
from urllib.parse import quote_plus

connection_uri = (
    f"mysql+pymysql://{quote_plus(data_source.db_username)}:"
    f"{quote_plus(data_source.db_password)}"
    f"@{data_source.db_host}:{data_source.db_port}/{data_source.db_name}"
    f"?charset=utf8mb4"
)
```

**教学要点**:
- URL 中传递凭据时必须编码
- `quote_plus` 处理所有 URL 保留字符
- 连接池 Engine 应缓存复用，不要每次创建

---

### 案例 3：异步函数中调用同步阻塞操作

**文件**: `backend/app/services/execution_service.py` 第 35-36 行
**严重度**: 严重

```python
# 问题代码
async def execute_dataframe(db: AsyncSession, df: pl.DataFrame, source_name: str) -> dict:
    ...
    executor = RuleExecutor(rule_configs, lookup_tables)
    result_df, stats = executor.execute(df)  # 同步 CPU 密集操作！
```

**问题分析**:
`executor.execute(df)` 是纯同步的 CPU 密集操作（polars DataFrame 转换），但直接在 `async def` 函数中调用。asyncio 是单线程事件循环，同步操作会阻塞整个循环，导致所有其他请求被挂起。对比 `etl_runner.py` 第 321 行正确使用了 `asyncio.to_thread()`。

**正确做法**:
```python
async def execute_dataframe(db: AsyncSession, df: pl.DataFrame, source_name: str) -> dict:
    ...
    executor = RuleExecutor(rule_configs, lookup_tables)
    # 将同步 CPU 密集操作放到线程池
    result_df, stats = await asyncio.to_thread(executor.execute, df)
```

**教学要点**:
- `async def` 不等于自动并发，同步代码仍会阻塞
- CPU 密集操作用 `asyncio.to_thread()` 卸载到线程池
- I/O 密集操作用真正的 async 库（如 `httpx` 替代 `requests`）

---

### 案例 4：弱密钥派生 — 用 \x00 填充短密钥

**文件**: `backend/app/utils/crypto.py` 第 10-15 行
**严重度**: 严重

```python
# 问题代码
def _get_key() -> bytes:
    key = settings.ENCRYPTION_KEY.encode("utf-8")
    if len(key) < 32:
        return key.ljust(32, b"\x00")  # 用 \x00 填充！
    return key[:32]
```

**问题分析**:
如果原始密钥是 8 字节，密钥的后 24 字节都是已知的 `\x00`，有效密钥空间从 256 位降至 64 位。AES-256-GCM 的安全性被严重削弱。

**正确做法**:
```python
import hashlib

def _get_key() -> bytes:
    """使用 SHA256 派生固定长度密钥"""
    return hashlib.sha256(settings.ENCRYPTION_KEY.encode("utf-8")).digest()
```

**教学要点**:
- 密钥不能简单填充，应使用 KDF（密钥派生函数）
- SHA256 是最低要求，生产环境应考虑 PBKDF2 或 Argon2
- 存量数据需要密钥迁移计划

---

### 案例 5：异常静默吞没 — 错误统计失真

**文件**: `backend/app/engine/executor.py` 第 345-353 行
**严重度**: 高

```python
# 问题代码
try:
    result = evaluate_formula(df, formula)
    df = df.with_columns(result.alias(target))
except Exception as e:
    logger.error(f"公式计算失败 [{rule.field_name}]: {e}")
    df = df.with_columns(pl.lit(None).alias(target))

self.stats.record(rule.field_name, matched=len(df), defaulted=0, errors=0)
#                                                                      ^^^^^^^^
# 明明出错了，errors 却记 0！
```

**问题分析**:
公式计算失败时整列被设为 `None`，但 `stats.record` 记录 `errors=0`。运维和监控无法感知错误发生。用户以为规则执行成功了，实际数据全是空值。

**正确做法**:
```python
try:
    result = evaluate_formula(df, formula)
    df = df.with_columns(result.alias(target))
    self.stats.record(rule.field_name, matched=len(df), defaulted=0, errors=0)
except Exception as e:
    logger.error(f"公式计算失败 [{rule.field_name}]: {e}")
    df = df.with_columns(pl.lit(None).alias(target))
    self.stats.record(rule.field_name, matched=0, defaulted=0, errors=len(df))
```

**教学要点**:
- catch 异常后要做正确的状态记录
- 错误统计是运维监控的基础，数据要准确
- `except Exception` 后要思考：是否应该继续执行？是否应该通知上游？

---

### 案例 6：N+1 查询 — 批量更新逐条查询

**文件**: `backend/app/api/v1/rules.py` 第 79-86 行
**严重度**: 高

```python
# 问题代码
@router.put("/batch-priority")
async def batch_update_priority(body: BatchPriorityUpdate, db: AsyncSession = Depends(get_db)):
    for item in body.items:
        result = await db.execute(select(Rule).where(Rule.id == item["id"]))
        rule = result.scalar_one_or_none()
        if rule:
            rule.priority = item["priority"]
    await db.flush()
```

**问题分析**:
100 条更新 = 100 次 SELECT 查询。每次数据库往返都有网络延迟，批量操作变成线性增长。

**正确做法**:
```python
@router.put("/batch-priority")
async def batch_update_priority(body: BatchPriorityUpdate, db: AsyncSession = Depends(get_db)):
    ids = [item["id"] for item in body.items]
    result = await db.execute(select(Rule).where(Rule.id.in_(ids)))
    rules = {r.id: r for r in result.scalars().all()}
    for item in body.items:
        if rule := rules.get(item["id"]):
            rule.priority = item["priority"]
    await db.flush()
```

**教学要点**:
- N+1 是最常见的数据库性能反模式
- 批量操作用 `WHERE id IN (...)` 一次查询
- SQLAlchemy 的 `selectinload` 可以自动解决关联查询的 N+1

---

### 案例 7：Zustand 全量订阅 — 每次输入触发全组件重渲染

**文件**: `frontend/src/pages/RuleEditor/index.tsx` 第 12 行
**严重度**: 严重

```typescript
// 问题代码
const store = useRuleEditorStore(); // 订阅整个 store！
```

**问题分析**:
这行代码订阅了 store 的所有字段。用户在条件行输入一个字符（触发 `updateConditionRow`），整个 `RuleEditorDrawer` 组件就会重渲染，包括 `BasicInfoForm`、`ConditionBuilder`、`FlowchartPreview` 等所有子组件。

**正确做法**:
```typescript
// 按需订阅
const open = useRuleEditorStore((s) => s.open);
const fieldName = useRuleEditorStore((s) => s.fieldName);
const config = useRuleEditorStore((s) => s.config);
const updateConditionRow = useRuleEditorStore((s) => s.updateConditionRow);
// actions 可以用 shallow equality 优化
import { useShallow } from 'zustand/react/shallow';
const { addConditionGroup, removeConditionGroup } = useRuleEditorStore(
  useShallow((s) => ({ addConditionGroup: s.addConditionGroup, removeConditionGroup: s.removeConditionGroup }))
);
```

**教学要点**:
- Zustand 的 selector 是性能优化的核心
- 全量订阅等于把全局状态当 local state 用，失去了细粒度更新的优势
- actions 是稳定引用，不需要订阅其变化

---

### 案例 8：错误处理策略不统一

**文件**: 多个前端文件

```typescript
// 模式 A: mutateAsync + try/catch（RuleEditor）
try {
  await createRule.mutateAsync(payload);
  store.resetEditor();
} catch {
  // 错误已在拦截器中处理（空 catch！）
}

// 模式 B: mutate + onSuccess（RuleSetManager）
createRuleSet.mutate(payload, {
  onSuccess: () => message.success('创建成功'),
  // 没有 onError！
});

// 模式 C: mutate + onSuccess + onError（理想模式）
deleteRuleSet.mutate(rs.id, {
  onSuccess: () => message.success('删除成功'),
  onError: (err) => message.error('删除失败，请稍后重试'),
});
```

**教学要点**:
- 团队需要统一错误处理约定
- 空 catch 块会吞掉所有信息，至少在开发环境记录
- mutation 应始终提供 `onError` 回调
- 拦截器的全局 `message.error` 不能替代组件级错误处理

---

### 案例 9：ErrorBoundary 层级设计缺陷

**文件**: `frontend/src/components/ErrorBoundary.tsx` + `frontend/src/App.tsx`

```typescript
// 问题：全局只有一个 ErrorBoundary 包裹所有路由
<ErrorBoundary>
  <HashRouter>
    <Routes>...</Routes>
  </HashRouter>
</ErrorBoundary>
```

**问题分析**:
任何页面级组件的渲染崩溃都会导致整个应用显示错误页。用户无法通过侧边栏导航到其他页面。路由切换也不会重置错误状态。

**正确做法**:
```typescript
// 每个路由级组件包裹独立的 ErrorBoundary
<HashRouter>
  <AppLayout>
    <ErrorBoundary key={location.pathname}>  {/* key 变化时重建 */}
      <Routes>
        <Route path="/rules" element={<ErrorBoundary><RuleList /></ErrorBoundary>} />
        <Route path="/editor" element={<ErrorBoundary><RuleEditor /></ErrorBoundary>} />
      </Routes>
    </ErrorBoundary>
  </AppLayout>
</HashRouter>
```

**教学要点**:
- 错误边界要分层：全局兜底 + 页面级隔离 + 组件级精细
- `key` 绑定路由可以在路由切换时重置 ErrorBoundary 状态
- "重试"按钮需要配合状态重置，否则会再次崩溃

---

### 案例 10：cron 表达式校验形同虚设

**文件**: `backend/app/api/v1/etl_jobs.py` 第 18-21 行
**严重度**: 严重

```python
# 问题代码
def _is_valid_cron(cron: str) -> bool:
    """简单校验 cron 表达式：5 个字段"""
    parts = cron.strip().split()
    return len(parts) == 5
```

**问题分析**:
`abc def ghi jkl mno` 会通过校验。`99 99 99 99 99`（非法）也会通过。调度器在运行时才会发现表达式无效，但此时任务已经保存到数据库。

**正确做法**:
```python
from croniter import croniter

def _is_valid_cron(cron: str) -> bool:
    """使用 croniter 真正校验 cron 表达式"""
    try:
        croniter.croniter(cron)
        return True
    except (ValueError, KeyError):
        return False
```

**教学要点**:
- 校验函数要真正校验，不能只做表面检查
- 输入校验应在保存前完成，而非运行时发现
- 使用成熟的第三方库替代手写校验

---

## 三、分阶段技术提升路线图

### 第一阶段：安全加固（1-2 周）

**目标**: 消除所有严重安全漏洞，建立安全编码意识

| 序号 | 行动项 | 负责人 | 验收标准 |
|------|--------|--------|---------|
| 1 | 修复 etl_runner.py SQL 注入（target.table_name 验证） | 后端 | _safe_identifier 覆盖所有动态表名/列名 |
| 2 | 修复密码 URL 编码问题 | 后端 | quote_plus 覆盖 username/password |
| 3 | 制定密钥迁移计划（crypto.py 弱密钥） | 后端 | 新数据使用 SHA256 派生，存量数据逐步迁移 |
| 4 | 修复 CORS 配置（禁止默认 `*`） | 后端 | 生产环境白名单 |
| 5 | 错误信息脱敏（client.ts） | 前端 | 生产环境不暴露后端堆栈 |

**培训主题**: Web 安全基础 — SQL 注入、XSS、密钥管理
**形式**: 1 小时技术分享 + 实操修复

---

### 第二阶段：异步编程与性能（2-3 周）

**目标**: 掌握 asyncio 最佳实践，消除性能反模式

| 序号 | 行动项 | 负责人 | 验收标准 |
|------|--------|--------|---------|
| 1 | 修复 execution_service.py 事件循环阻塞 | 后端 | asyncio.to_thread 包裹 CPU 密集操作 |
| 2 | 修复 N+1 查询（rules.py batch-priority） | 后端 | 改为 WHERE IN 批量查询 |
| 3 | Engine 连接池复用（etl_runner.py） | 后端 | 缓存 Engine 实例，不每次创建 |
| 4 | 修复 Zustand 全量订阅（RuleEditor） | 前端 | 使用 selector 按需订阅 |
| 5 | 修复 map_elements 性能瓶颈（executor.py） | 后端 | lookup 改用 join，避免逐元素回调 |
| 6 | ORM lazy loading 策略优化 | 后端 | selectinload 按需加载，列表不加关联 |

**培训主题**: asyncio 原理与实战 — 事件循环、线程池、非阻塞 I/O
**形式**: 2 小时 Workshop + 性能对比 Demo

---

### 第三阶段：错误处理体系（2 周）

**目标**: 建立统一的错误处理策略，消除异常吞没

| 序号 | 行动项 | 负责人 | 验收标准 |
|------|--------|--------|---------|
| 1 | 统一前端 mutation 错误处理模式 | 前端 | 所有 mutation 提供 onError 回调 |
| 2 | 修复 executor.py 错误统计失真 | 后端 | errors 计数正确反映失败规则数 |
| 3 | 修复 crypto.py 异常静默吞没 | 后端 | 记录解密失败日志和上下文 |
| 4 | 修复 ErrorBoundary 层级设计 | 前端 | 每个路由级组件独立 ErrorBoundary |
| 5 | 修复 RuleEditor 空 catch 块 | 前端 | 开发环境记录错误，组件有错误状态 |
| 6 | 建立前端错误上报标准 | 前端 | ErrorBoundary 上报 componentStack |

**培训主题**: 防御性编程 — 异常处理策略、错误边界、可观测性
**形式**: 案例分析 + 结对编程修复

---

### 第四阶段：代码质量与架构（3-4 周）

**目标**: 提升代码可维护性，建立架构思维

| 序号 | 行动项 | 负责人 | 验收标准 |
|------|--------|--------|---------|
| 1 | 重构 executor.py if-elif 链为策略模式 | 后端 | 操作符字典分派，新增操作符不改主方法 |
| 2 | 消除前端非空断言 `!` | 前端 | 使用类型守卫或显式检查 |
| 3 | 修复 ORM 外键约束缺失 | 后端 | rule_set_id、lookup_table_id 添加 ForeignKey |
| 4 | 修复 ORM 动态属性赋值 | 后端 | 使用 DTO 替代 ORM 对象直接序列化 |
| 5 | cron 校验强化（使用 croniter） | 后端 | 真正校验表达式合法性 |
| 6 | 执行 ruff --fix + format 统一代码风格 | 全员 | 0 lint errors |
| 7 | 后端测试迁移 pytest | 后端 | 所有测试使用 pytest 框架 |

**培训主题**: 设计模式实战 — 策略模式、DTO、SOLID 原则
**形式**: 代码重构 Dojo + 代码评审实战

---

### 第五阶段：持续改进（长期）

| 序号 | 行动项 | 频率 |
|------|--------|------|
| 1 | 代码审查按标准执行，季度复盘 | 每个 PR |
| 2 | 技术分享会（轮流主讲） | 每两周 |
| 3 | CI/CD 流水线覆盖率和门槛提升 | 每月 |
| 4 | 安全扫描（bandit + npm audit） | 每月 |
| 5 | 代码质量指标追踪 | 每月 |

---

## 四、技术培训计划

### 4.1 培训课程设计

| 课程 | 时长 | 对象 | 核心内容 |
|------|------|------|---------|
| Web 安全编码基础 | 2h | 全员 | SQL 注入、XSS、密钥管理、OWASP Top 10 |
| asyncio 深入 | 2h | 后端 | 事件循环、线程池、异步 ORM、并发控制 |
| React 性能优化 | 2h | 前端 | 渲染机制、selector、memo、虚拟滚动 |
| 防御性编程 | 1.5h | 全员 | 异常处理策略、错误边界、可观测性 |
| 设计模式实战 | 2h | 全员 | 策略模式、DTO、开闭原则 |
| TypeScript 进阶 | 1.5h | 前端 | 类型守卫、泛型、可辨识联合 |
| SQLAlchemy 2.0 最佳实践 | 1.5h | 后端 | 关系加载策略、事务管理、异步 Session |

### 4.2 结对编程计划

每周安排 2 次结对编程 session，每次 1.5 小时：

| 周次 | 主题 | 结对方式 |
|------|------|---------|
| W1 | 安全修复（SQL 注入 + 密码编码） | 前后端交叉结对 |
| W2 | 异步修复（事件循环 + N+1） | 后端内部结对 |
| W3 | 错误处理统一（mutation 模式 + ErrorBoundary） | 前端内部结对 |
| W4 | 代码重构（策略模式 + selector 优化） | 前后端交叉结对 |

### 4.3 代码评审实战

每个阶段结束时，选取 2-3 个已修复的 PR 作为案例：
1. 展示修复前的代码和问题
2. 讨论修复方案的选择理由
3. 评审修复后的代码是否引入新问题
4. 总结可复用的模式和经验

---

## 五、技术规范速查卡

### 后端速查

| 场景 | 不要写 | 应该写 |
|------|--------|--------|
| 动态表名 | `f"TABLE \`{name}\`"` | `_safe_identifier(name)` 先验证 |
| 密码连接串 | `f"...:{password}@..."` | `quote_plus(password)` |
| async 中的 CPU 操作 | `result = cpu_work()` | `await asyncio.to_thread(cpu_work)` |
| 批量查询 | `for id in ids: select(...)` | `select(...).where(id.in_(ids))` |
| 异常处理 | `except: pass` | `except SpecificError as e: logger.error(...)` |
| 密钥派生 | `key.ljust(32, b'\x00')` | `hashlib.sha256(key).digest()` |
| Engine 创建 | 每次调用 `create_engine()` | 模块级缓存 Engine 实例 |
| ORM 序列化 | `r.rule_set_name = ...` | 返回独立的 DTO dict |

### 前端速查

| 场景 | 不要写 | 应该写 |
|------|--------|--------|
| Zustand 订阅 | `const store = useStore()` | `const x = useStore((s) => s.x)` |
| mutation 错误 | 只有 `onSuccess` | 同时提供 `onError` |
| catch 块 | `catch {}` 空 | `catch (e) { if (DEV) console.error(e) }` |
| 非空断言 | `data!.field` | `if (data) { data.field }` |
| 列表 key | `key={index}` | `key={item.id}` |
| 列定义 | 组件内每次新建 | `useMemo` 或提取为常量 |
| 表单提交 | `await mutateAsync()` 不 catch | `try { await mutateAsync() } catch {}` |
| ErrorBoundary | 全局一个 | 每个路由独立 |

---

## 六、效果衡量

### 量化指标

| 指标 | 基线（当前） | 3 个月目标 | 6 个月目标 |
|------|------------|-----------|-----------|
| 严重 Bug 数（/月） | 未追踪 | < 3 | < 1 |
| PR 审查阻塞项平均数 | 未追踪 | < 2 | < 1 |
| 单元测试覆盖率 | 前端 ~30% | > 60% | > 80% |
| 后端 pytest 覆盖率 | 0% | > 40% | > 70% |
| CI 流水线通过率 | N/A | > 90% | > 95% |
| lint 错误数 | 254（后端）+ 1691（前端） | < 50 | 0 |

### 质性指标

- 团队成员能独立识别和修复 SQL 注入、XSS 等安全问题
- 代码审查中安全相关意见数量下降（说明预防意识提升）
- 新代码不再出现 N+1 查询、全量订阅等已知反模式
- 团队成员能主动使用设计模式优化代码结构
