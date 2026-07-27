# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**BI Rule Engine** — an enterprise data transformation platform. Users define rules (mapping / cleaning / lookup / computed) over MySQL data sources; the engine executes them as Polars pipelines and writes results to target tables. Includes a visual rule editor (React), an ETL scheduler (APScheduler), and a tracing/audit system.

Stack:
- **Backend**: FastAPI + SQLAlchemy 2.0 async + Polars + APScheduler + Loguru
- **Frontend**: React 19 + TypeScript + Vite + Ant Design 6 + Zustand + react-query + @xyflow/react
- **Infra**: MySQL 8 (metadata), Redis (broker), MinIO (optional), Celery (configured but scheduler is APScheduler)

There is no Git repository in this directory — changes are local-only.

---

## Common Commands

### Infrastructure (from repo root)
```bash
docker compose up -d mysql redis minio       # MySQL:3306, Redis:6379, MinIO:9000/9001
```

### Backend (`backend/`)
```bash
pip install -e .[dev]                        # Install with dev deps
alembic upgrade head                         # Apply migrations
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload   # Dev server
# Celery worker (alternative executor)
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
# Smoke tests
PYTHONPATH=. python tests/test_rules.py
python tests/test_formula_engine.py
python scripts/test_all_rules.py             # Rule-by-rule HTTP test
bash start.sh                                # All-in-one bootstrap
```
API docs: `http://localhost:8000/docs` — health: `/api/health`.

### Frontend (`frontend/`)
```bash
npm run dev                                   # Vite at :5173, proxies /api → :8000
npm run build                                 # tsc -b && vite build
npm run lint                                  # oxlint
npm run test                                  # Vitest one-shot (unit + component)
npm run test:watch                            # Vitest watch
npm run test:coverage                         # v8 coverage → ./coverage
npm run test:e2e                              # Playwright (auto-starts dev server)
npm run test:e2e:ui                           # Playwright UI mode
```

### A single test
- Frontend unit: `npx vitest run src/stores/ruleStore.test.ts`
- Frontend component: `npx vitest run src/pages/RuleSetManager/index.test.tsx`
- Frontend E2E: `npx playwright test e2e/rule-set-crud.spec.ts`
- Backend: `PYTHONPATH=. python tests/test_rules.py` (no pytest framework wired up — tests are runnable scripts).

---

## High-Level Architecture

### Backend structure (`backend/app/`)

| Module | Purpose |
|---|---|
| `main.py` | FastAPI app, lifespan boots `SchedulerManager`, mounts CORS + `TraceMiddleware`, registers global exception handlers (500 → includes trace_id, 400 → ValueError). |
| `config.py` | `pydantic-settings` `Settings` (DB URL, Redis, encryption, log rotation, scheduler). Cached via `get_settings()`. |
| `db.py` | `AsyncSessionLocal` + `get_db()` dependency (commits if no active txn, rolls back on exception). |
| `logging/` | Loguru setup: three sinks (access / error / app) with rotation/retention; per-request `trace_id` via contextvar. |
| `middleware/` | `TraceMiddleware` — reads/generates `X-Trace-Id`, logs JSON access lines, echoes header on response. |
| `api/v1/` | Domain routers: `rules`, `rule_sets`, `lookup_tables`, `tasks`, `data_sources`, `target_tables`, `etl_jobs`, `logs`, `ws`. |
| `models/` | SQLAlchemy ORM: `Rule`, `RuleSet`, `LookupTable`, `DataSource`, `TargetTable`, `ETLJob`, `ETLJobRun`, `ExecutionTask`, `AuditLog`. |
| `schemas/` | Pydantic request/response models. |
| `engine/` | Pure-Python rule engine (see below). |
| `tasks/` | Celery app + `SchedulerManager` (APScheduler AsyncIO, loads `ETLJob.cron_expression` on startup). |
| `utils/` | `crypto.py` (AES for data-source passwords), `mysql_reader.py`, `export.py`. |

### The rule engine (`backend/app/engine/`) — core domain logic

Rules are JSON-defined in `Rule.config` and executed as a Polars pipeline.

1. **`parser.py`** — `RuleParser.parse(rule_dict)` → `RuleConfig` with `conditions[]` (groups of `ConditionRow`), `cleaning_steps[]`, `lookup_*`, `formula_expression`, `depends_on[]`.
2. **`compiler.py`** — `compile_condition(row)` turns a `ConditionRow` into a boolean predicate. Operators: `eq/neq/contains/not_contains/matches/starts_with/ends_with/in/between/gt/gte/lt/lte/is_null/is_not_null`. Grouped by `AND`/`OR`.
3. **`dependency.py`** — `topological_sort(rules)` does Kahn's algorithm over `depends_on` fields; returns levels so each level can run "in parallel" (sequentially today, but the layering is the contract). Throws `CyclicDependencyError` on cycles.
4. **`executor.py`** — `RuleExecutor.execute(df)` iterates levels and dispatches by `rule_type`:
   - `mapping` — ordered `pl.when(...).then(result).otherwise(col)` cascade with `default_result` (or `keep_original`).
   - `cleaning` — applies `fill_null` / `replace` / `trim` / `regex_extract` / `substring` steps.
   - `lookup` — dict lookup by `lookup_key_field`, then `lookup_fallbacks[]` chain.
   - `computed` — delegates to `formula_engine.evaluate_formula`.
   - `RuleExecutionStats` records per-field matched/defaulted/errors.
5. **`formula_engine.py`** — Excel-like DSL compiled to Polars Expressions. Functions: `IF/COALESCE/IFNULL/NVL/ROUND/ABS/CEIL/FLOOR/SPLIT/UPPER/LOWER/TRIM/LENGTH/REPLACE/SUBSTR/CONTAINS/STARTS_WITH/NOT_CONTAINS`. Supports `IS NULL` / `IS NOT NULL` / `IN (...)` / `AND` / `OR`. Uses `eval(...)` with restricted `__builtins__`.
6. **`etl_runner.py`** — Glue code: builds parameterized extract SQL (`_safe_identifier` regex to prevent SQL injection), reads via `polars.read_database`, calls executor, writes to target table (`truncate_insert` / `upsert` w/ `ON DUPLICATE KEY UPDATE`), auto-creates tables if `auto_create_table=True`, updates incremental watermark. `run_etl_job` is the async entry point; sync core runs in `asyncio.to_thread` to keep the loop responsive.

### Frontend structure (`frontend/src/`)

- `App.tsx` — `HashRouter` + `QueryClientProvider` + Antd `ConfigProvider` (zh_CN, primary `#1677ff`) + `ErrorBoundary`. Routes: `/rule-sets`, `/rule-sets/:id`, `/rules`, `/lookup-tables`, `/tasks`, `/dag`, `/data-sources`, `/target-tables`, `/etl-jobs`. Unknown route → `/rule-sets`.
- `main.tsx` — Initializes logger, hooks `window.error`/`unhandledrejection` for error reporting.
- `api/` — `client.ts` (axios instance, injects and reads `X-Trace-Id`, auto-reports 5xx) + per-domain `xxxApi.ts` objects. Each has a co-located `.test.ts`.
- `stores/` — Zustand: `appStore` (sidebar collapse), `ruleStore` (full rule editor state — conditions, cleaning steps, lookup fallbacks, formula).
- `hooks/` — react-query wrappers per domain (`useRules`, `useDataSources`, etc.).
- `pages/` — One folder per page. `RuleSetManager` (card list + CRUD), `RuleSetDetail` (rules under a set), `RuleList`/`RuleEditor` (multi-tab: conditions / cleaning / lookup / formula), `DependencyDAG` (@xyflow/react graph), `ETLJobs`, `ETLJobRuns`, `TaskCenter`, `DataSources`, `TargetTables`, `LookupTables`, `RuleTest`.
- `components/` — `Layout/AppLayout` (sidebar + content), `ErrorBoundary`, `FieldSelect`, `OperatorSelect`.
- `utils/logger.ts` — `traceIdManager` (sessionStorage), `reportError` (POST to `/api/v1/logs/frontend-error`), `initLogger` (mutes console in prod).
- `test/` — `setup.ts` (jest-dom, jsdom polyfills, antd `message` mock) + `utils.tsx` (`renderWithProviders` wraps QueryClient/Router/ConfigProvider).

### Cross-cutting concepts

- **Trace ID propagation**: frontend `traceIdManager` → `X-Trace-Id` header → `TraceMiddleware` writes to contextvar → `logging` binds every log line → response echoes header. Frontend catches it and stores. 5xx errors auto-`POST` to `/api/v1/logs/frontend-error`.
- **Audit log**: `AuditLog` model exists; collection gated by `AUDIT_LOG_ENABLED` (default off).
- **Encryption**: `app.utils.crypto.encrypt/decrypt` using `ENCRYPTION_KEY` (SHA-256 derived if < 32 bytes). Used for `DataSource.db_password`.
- **Safe identifiers**: `_SAFE_IDENTIFIER` regex in `etl_runner.py` is the gatekeeper before any identifier is interpolated into SQL — table/column names from user input must pass this check.

### Testing infrastructure

- **Frontend**: 123 Vitest tests (`src/**/*.{test,spec}.{ts,tsx}`) + 4 Playwright specs in `e2e/`. Util: `renderWithProviders` for components. The `test-results/` and `coverage/` dirs are generated artifacts.
- **Backend**: No pytest — tests in `tests/` are runnable Python scripts invoked directly. `scripts/test_all_rules.py` is an HTTP-driven rule coverage suite.
- **Open issue** (per `overview.md`): `RuleSetManager.handleSubmit` and `DataSources` form submits don't `try/catch` `form.validateFields()` rejections → unhandled promise rejections on validation failure.

### Configuration

- `backend/.env` — `DEBUG=true`, `DB_HOST=localhost`, `LOG_LEVEL=DEBUG`, `ENCRYPTION_KEY=...` (dev key only).
- `backend/app/config.py` — full list of env vars. Notable: `SCHEDULER_TIMEZONE=Asia/Shanghai`, `ETL_BATCH_SIZE=10000`, `QUERY_TIMEOUT_SECONDS=600`, `MAX_QUERY_ROWS=2000000`.
- `frontend/vite.config.ts` — proxies `/api` → `http://localhost:8000`.
