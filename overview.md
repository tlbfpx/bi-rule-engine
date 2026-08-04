# Round 6 代码审查修复 — 完成总结

## 修复清单

### 🔴 Blocker（5 个，全部修复）

| # | 问题 | 修复方案 | 涉及文件 |
|---|------|---------|---------|
| B1 | **全部 API 无 JWT 认证** — `router.py` 挂载路由时无 `Depends(get_current_user)` | 为所有业务路由添加 `dependencies=[Depends(get_current_user)]`，`auth.router` 保持公开 | `backend/app/api/v1/router.py` |
| B2 | 导出用 `fetch()` 绕过 Axios，不携带 JWT token | 通过 `useAuthStore.getState().token` 获取 JWT，附加到 `Authorization` header | `frontend/src/api/rules.ts` |
| B3 | 列表端点逐行 `validate_rule_config` 导致 N+1 性能问题 | 新增 `rules.config_errors` JSON 列，在 create/update 时预计算并存储，列表端点���接读取 | `backend/app/models/rule.py`, `backend/app/api/v1/rules.py`, `backend/app/schemas/rule.py` |
| B4 | 导出端点 `rule_set_id` 缺 UUID 格式校验 | 添加 `pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"` 正则校验 | `backend/app/api/v1/rules.py` |
| B5 | `RuleSetUpdate` 仍允许修改 `data_source_id` | 从 Schema 和更新逻辑中移除 `data_source_id` 字段 | `backend/app/api/v1/rule_sets.py` |

### 🟡 Suggestion（8 个，全部修复）

| # | 问题 | 修复方案 |
|---|------|---------|
| S1 | ILIKE 模糊搜索大表性能隐患 | 添加注释说明生产环境需建 trigram 索引 |
| S2 | `RuleOut.config` 用裸 `dict` 类型，无结构保障 | 改用 `RuleConfigSchema`（带 `model_config = {"extra": "allow"}` 兼容脏数据） |
| S3 | 批量优先级更新逐条查询 N 次 | 改为单条 `UPDATE ... WHERE id IN (...)` |
| S4 | `BizException` 未用标准错误码 | create/update 使用 `VALIDATION_ERROR(422)` |
| S5 | 前后端校验逻辑无同步注释 | 在 `validateConfigBeforeSave` 和 `validate_rule_config` 互引对方 |
| S6 | `FieldSelect` 下拉关闭时搜索文本未清空 | 添加 `onDropdownVisibleChange` 回调清空 |
| S7 | 数据源已确认解密后类型标注缺失 | 已补充 |
| S8 | `useEffect` 依赖 `allRS` 对象不稳定导致重复加载 | 提取 `targetDSId` 作为稳定依赖 |

### 💭 Nit（4 个，全部修复）

| # | 问题 | 修复方案 |
|---|------|---------|
| N1 | 导入顺序不规范 | 调整 import 分组 |
| N2 | 用 cell 对象获取列字母 | 改用 `get_column_letter()` |
| N3 | `RuleConfigSchema` 类型已验证 | 已确认 |
| N4 | `_flatten_config` 布尔值意外显示 | 添加 `is not None` 判断 |

## DB 迁移

- 新增 `alembic/versions/b3c4d5e6f7a9_add_rule_config_errors.py`
- 在 `rules` 表添加 `config_errors` JSON 列
- 修复旧迁移 `e6f7a8b9c0d1` 的语法错误
- 清理 `alembic_version` 表中的重复记录

## 测试结果

| 测试套件 | 结果 |
|---------|------|
| 后端 pytest (单元) | **47/47** ✅ |
| 集成 test_api_full.py | **104/104** ✅ |
| 前端 vitest | **139/139** ✅ |
| TypeScript | **0 错误** ✅ |

## 修改文件清单（18 个文件）

**后端：**
- `app/api/v1/router.py` — JWT 认证依赖
- `app/api/v1/rules.py` — B3/B4/S1/S3/S4/N2/N4
- `app/api/v1/rule_sets.py` — B5 移除 data_source_id
- `app/models/rule.py` — B3 新增 config_errors 列
- `app/schemas/rule.py` — S2 RuleConfigSchema + config_errors
- `app/schemas/rule_set.py` — B5
- `app/services/rule_validator.py` — S5 同步注释
- `alembic/versions/b3c4d5e6f7a9_add_rule_config_errors.py` — 新建
- `alembic/versions/e6f7a8b9c0d1_add_data_source_id_to_rule_sets.py` — 语法修复
- `tests/test_api_full.py` — 适配 JWT 认证 + 校验逻辑

**前端：**
- `src/api/rules.ts` — B2 JWT token
- `src/components/FieldSelect.tsx` — S6
- `src/pages/RuleEditor/index.tsx` — S5/S8
