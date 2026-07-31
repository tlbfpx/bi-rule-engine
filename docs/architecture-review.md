# BI 规则引擎 — 架构审视报告

> 2026-07-30 · 面向"探讨阶段"的架构合理性、扩展性、可用性评估

---

## 一、现状总结

当前系统是典型的**单进程单体架构**：

```
Nginx? → FastAPI (1 进程)
                ├── REST API (CRUD + 认证)
                ├── APScheduler (内存 jobstore)
                ├── ETL 引擎 (asyncio 线程池)
                └── WebSocket (内存连接表)
         → MySQL (单库) + Redis (单节点) + MinIO
```

**一句话评价**：代码层面写得很扎实（五轮审查 94 个问题已修），但架构层面存在**三个结构性瓶颈**——无法水平扩展、重型任务与 API 争抢资源、调度状态全内存。

---

## 二、核心瓶颈分析

### 瓶颈 1：ETL 与 API 共进程 — 资源争抢

| 维度 | 现状 | 影响 |
|------|------|------|
| 执行方式 | `asyncio.to_thread()` 丢到默认线程池 | 线程池上限（~几十个），大量并发 ETL 会耗尽 |
| 内存 | polars 全量 `read_database` | 大表（百万行）直接 OOM |
| 连接 | 每次 ETL 临时创建+销毁 engine | 连接开销大，无复用 |
| 隔离 | ETL 和 API 共享 CPU/内存 | 一个大 ETL 跑起来，API 响应变慢 |

**根因**：ETL 引擎嵌入 API 进程，没有独立 Worker。

### 瓶颈 2：调度器内存态 — 无法多实例

| 维度 | 现状 | 影响 |
|------|------|------|
| JobStore | `MemoryJobStore`（默认，未配置） | 进程重启丢失所有调度状态 |
| 多实例 | 两个 API 实例 = 同一任务执行两次 | 无法水平扩展 |
| 恢复 | `load_jobs()` 从 DB 重新加载 | 只恢复 job 定义，不恢复运行态 |
| misfire | `coalesce=True, grace_time=3600` | 超过 1h 的错过任务静默丢弃 |

**根因**：调度器没有持久化 jobstore，没有分布式锁。

### 瓶颈 3：WebSocket 内存态 — 跨实例失效

| 维度 | 现状 | 影响 |
|------|------|------|
| 连接管理 | `ConnectionManager` 内存 dict | 进程重启全部断开 |
| 跨实例 | 用户连实例 A，ETL 在实例 B 跑 | 进度推不到用户 |
| 前端 | React Query 2s 轮询兜底 | 没用 WS 的实时性 |

**根因**：WS 进度推送没有走消息总线（Redis pub/sub）。

---

## 三、架构演进路线

### 第一阶段：任务队列分离（投入小，收益大）

**目标**：把 ETL 执行从 API 进程剥离，API 只负责接收请求 + 入队。

```
FastAPI → Redis Queue (arq/celery) → ETL Worker (独立进程)
```

**改动点**：
- 新增 `worker.py` 独立入口，消费 ETL 任务
- API 层 `run_etl_job` 改为 `enqueue_etl_job`
- Worker 内复用现有 `engine/etl_runner.py`（代码不用大改）
- WS 进度改为 Worker 写 Redis channel，API 订阅转发

**收益**：
- API 不再被重型 ETL 阻塞
- Worker 可独立扩缩容（Docker `scale=3`）
- Worker 崩溃不影响 API

**技术选型建议**：
- **轻量**：arq（asyncio + Redis，无额外组件）
- **重量**：Celery（成熟生态，但需 RabbitMQ）

### 第二阶段：分布式调度（中等投入）

**目标**：调度器从内存 jobstore 迁移到 Redis/DB jobstore。

```python
jobstores = {
    'default': RedisJobStore(jobs_key='apscheduler.jobs', 
                              run_times_key='apscheduler.run_times')
}
coalesce = True
max_instances = 1  # 全局唯一，分布式锁保证
```

**改动点**：
- `scheduler.py` 配置 `RedisJobStore`
- `max_instances=1` + 分布式锁，确保同一 job 同一时刻只有一个实例执行
- misfire 策略调优

**收益**：
- 多 API 实例不会重复执行
- 调度状态持久化，重启不丢

### 第三阶段：大数据量治理（按需）

**目标**：解决 polars 全量加载的 OOM 风险。

**方案**：分批读取 + 分批转换 + 批量写入。

```python
# 当前
df = pl.read_database(sql, engine)  # 全量
result = executor.execute(df)       # 全量
write_to_target(result)             # 全量

# 改造后
for batch in batched_read(sql, engine, batch_size=10000):
    result = executor.execute(batch)
    write_to_target(result, append=True)
```

**关键约束**：
- 清洗步骤中的 `fill_null` 跨行引用（如填充默认值）需要在 batch 内处理
- 查找表（lookup）需要全量预加载到内存（通常不大）
- 依赖排序在首批时确定，后续 batch 复用

---

## 四、前端架构评估

前端架构整体成熟度不错，不需要大改：

| 维度 | 评价 | 建议 |
|------|------|------|
| 状态管理 | ✅ Zustand(UI态) + React Query(服务端态) 分层正确 | ruleStore 引入 immer |
| API 层 | ✅ 统一拦截器 + traceId | 加请求重试 + AbortController |
| 路由分割 | ✅ lazy + Suspense | 加骨架屏 |
| 实时数据 | ⚠️ 2s 轮询（无 WS） | 跟随后端 WS 改造，加自动重连 |
| 组件耦合 | ⚠️ 中等（280-315行/页面） | CRUD 三页抽泛型组件 |

前端**不需要单独做架构改造**，跟随后端 WS 改造同步升级即可。

---

## 五、推荐演进优先级

| 阶段 | 内容 | 投入 | 收益 |
|------|------|------|------|
| **1** | ETL Worker 分离 + Redis Queue | 2-3 天 | API 不阻塞，可独立扩容 |
| **2** | 调度器 Redis jobstore + 分布式锁 | 1 天 | 多实例部署不重复 |
| **3** | WS 经 Redis pub/sub 跨实例 | 1 天 | 进度推送可靠 |
| **4** | 大数据量分批处理 | 2-3 天 | 不 OOM |
| **5** | MySQL 读写分离 + 备份 | 1 天 | DB 层可用性 |
| **6** | Prometheus metrics + 告警 | 1 天 | 可观测 |

**阶段 1-3 是核心**，做完后系统就从"单体"升级为"可扩展分层架构"。阶段 4-6 可以上线后按需推进。
