# 上线前工作路线图

> 2026-07-30 · 在五轮代码审查 + 三大工程能力补全后，评估上线前剩余工作

## 当前完成度

| 维度 | 状态 | 说明 |
|------|------|------|
| 代码质量 | ✅ 完成 | 5 轮审查，94 个问题修复 |
| 单元测试 | ✅ 完成 | pytest 47/47, vitest 139/139 |
| 认证安全 | ✅ 完成 | JWT + bcrypt + 路由守卫 |
| ETL 正确性 | ✅ 完成 | 11 行真实数据验证 |
| 生产部署架构 | ❌ 缺失 | 前端无 Dockerfile, 无 nginx, compose 是 dev 配置 |
| CI/CD 流水线 | ❌ 缺失 | 无 .github/workflows |
| 可观测性 | ❌ 缺失 | 无 metrics, 无告警, 无日志收集 |
| 性能验证 | ❌ 缺失 | 仅 11 行数据 |
| 数据安全 | ❌ 缺失 | 无备份策略 |

**生产就绪度: ~60%**

---

## P0 — 安全与配置（上线前必做）

### 已有的防护（代码已实现）

`config.py` 已有生产环境断言：
```python
# config.py:125-132
if self.ENVIRONMENT == "production" and self.ENCRYPTION_KEY == "change-me-32-bytes-key-here!!":
    raise RuntimeError("生产环境必须设置 ENCRYPTION_KEY")
if self.ENVIRONMENT == "production" and "change-me" in self.JWT_SECRET_KEY:
    raise RuntimeError("生产环境必须设置 JWT_SECRET_KEY")
```

### 需要做的事

1. **生产 .env 文件**: 设置 `ENVIRONMENT=production`，生成随机 JWT_SECRET_KEY 和 ENCRYPTION_KEY
2. **改默认密码**: `main.py` lifespan 自动创建 admin/admin123，上线后必须立刻改密码
3. **CORS 收窄**: `config.py:14` 当前允许 localhost:5173 和 localhost:3000，生产改为实际域名
4. **数据库密码**: docker-compose.yml 中 MYSQL_ROOT_PASSWORD 和 MYSQL_PASSWORD 使用默认值

---

## P1 — 容器化与部署架构

### 当前问题

| 问题 | 文件 | 说明 |
|------|------|------|
| 前端无 Dockerfile | - | 仅 `backend/Dockerfile` 存在 |
| compose 是 dev 配置 | `docker-compose.yml:39` | api 用 `--reload`，生产需移除 |
| 无 nginx 反代 | - | 前端静态资源和 API 需统一端口 |
| api 无 healthcheck | `docker-compose.yml:37-54` | mysql/redis 有 healthcheck，api 没有 |
| MinIO 存储未挂载 | `docker-compose.yml:54` | `STORAGE_DIR=/workspace/bi-rule-engine/storage` 未映射到 MinIO |
| 前端 build 产物无服务 | - | Vite build 后需要 nginx/serve 托管 |

### 需要创建

1. `frontend/Dockerfile` — 多阶段构建（node build → nginx serve）
2. `frontend/nginx.conf` — SPA fallback + API 反代到 api:8000
3. `docker-compose.prod.yml` — 生产编排（去掉 --reload，加 healthcheck，加 nginx）
4. `.env.production.template` — 生产环境变量模板

---

## P2 — CI/CD 流水线

### 当前状态

项目中 **完全没有 CI 配置**：无 `.github/workflows/`，无 `.gitlab-ci.yml`。

五轮代码审查修复的 94 个问题、47+139 个测试，全部只在本地手动运行。任何一次提交都可能引入回归。

### 建议流水线

```yaml
# .github/workflows/ci.yml
on: [push, pull_request]
jobs:
  backend:
    - lint: ruff check
    - type: mypy app/
    - test: pytest --tb=short
  frontend:
    - lint: oxlint
    - type: tsc --noEmit
    - test: vitest run
    - build: vite build
  docker:
    - docker build ./backend
    - docker build ./frontend
```

---

## P3 — 可观测性与运维

### 已有基础

- ✅ Loguru 结构化日志 + 日志轮转（access/error/app 三通道）
- ✅ trace_id 全链路追踪
- ✅ `/api/health` 健康检查端点（检查 DB 连接）
- ✅ 前端错误上报到后端（`/api/v1/logs/frontend-error`）
- ✅ SecurityHeadersMiddleware 安全响应头

### 缺失项

1. **无 Prometheus metrics**: ETL 执行耗时、成功率、并发数不可观测
2. **无日志收集**: 日志写在容器内 `/tmp`，容器销毁即丢失
3. **无告警**: ETL 失败/超时只写日志，无企业微信/钉钉/邮件通知
4. **无 readiness 区分**: `/api/health` 不区分 liveness/readiness
5. **无 Grafana 面板**: 无可视化运维视图

---

## P4 — 性能验证与数据安全

### 性能

- ETL 引擎仅验证 11 行数据
- `config.py` 中 `MAX_QUERY_ROWS=2000000`，`ETL_BATCH_SIZE=10000`
- Polars 内存占用在大数据量下未验证
- 并发 ETL 任务（`SCHEDULER_MAX_INSTANCES=3`）的资源竞争未测试

### 数据安全

- MySQL: docker-compose 有 `mysql_data` 卷，但无备份脚本
- Redis: `redis:7-alpine` 镜像默认无持久化配置
- Alembic 迁移: 需确认 `alembic upgrade head` 在生产环境的执行流程
- 存储目录: `storage/` 下有业务数据文件（CSV/XLSX），需定期备份
