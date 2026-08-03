"""全面 API 集成测试 — 覆盖所有端点、所有规则类型、完整 ETL 流程"""
import json
import uuid
import httpx
import polars as pl
from io import BytesIO

BASE = "http://localhost:8000/api/v1"

# 禁用代理 — 确保本地请求不走 http_proxy / HTTP_PROXY
CLIENT = httpx.Client(timeout=60, trust_env=False)

# ─── 测试辅助 ───────────────────────────────────────────
passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}  {detail}")

def api(method, path, **kwargs):
    """统一 API 调用"""
    url = f"{BASE}{path}"
    resp = CLIENT.request(method, url, **kwargs)
    return resp


print("=" * 70)
print("BI Rule Engine — 全面 API 集成测试")
print("=" * 70)

# ============================================================
# 1. 健康检查 (在根路径，不在 /api/v1 下)
# ============================================================
print("\n📋 1. 健康检查")
resp = CLIENT.get("http://localhost:8000/api/health")
check("GET /api/health 返回 200", resp.status_code == 200)
data = resp.json()
check("status == ok", data.get("status") == "ok")
check("database ok", data.get("database", {}).get("ok") is True)

# ============================================================
# 2. 数据源 CRUD
# ============================================================
print("\n📋 2. 数据源管理 (8 端点)")

ds_payload = {
    "name": f"test_ds_{uuid.uuid4().hex[:8]}",
    "description": "API 测试数据源",
    "enabled": True,
    "db_host": "localhost",
    "db_port": 3306,
    "db_name": "bi_rule_engine",
    "db_username": "bi_rule",
    "db_password": "bi_rule_pass",
    "extract_mode": "table",
    "extract_table": "data_sources",
}

# 2.1 创建
resp = api("post", "/data-sources", json=ds_payload)
check("POST /data-sources → 201", resp.status_code == 201)
ds = resp.json()
ds_id = ds.get("id")
check("返回 id", ds_id is not None)
check("name 正确", ds.get("name") == ds_payload["name"])

# 2.2 列表
resp = api("get", "/data-sources", params={"page": 1, "page_size": 10})
check("GET /data-sources → 200", resp.status_code == 200)
check("返回 items", "items" in resp.json())

# 2.3 全部
resp = api("get", "/data-sources/all")
check("GET /data-sources/all → 200", resp.status_code == 200)

# 2.4 获取单个
resp = api("get", f"/data-sources/{ds_id}")
check("GET /data-sources/{id} → 200", resp.status_code == 200)

# 2.5 更新
resp = api("put", f"/data-sources/{ds_id}", json={"description": "更新后的描述"})
check("PUT /data-sources/{id} → 200", resp.status_code == 200)

# 2.6 测试连接
resp = api("post", "/data-sources/test-connection", json={
    "db_host": "localhost", "db_port": 3306, "db_name": "bi_rule_engine",
    "db_username": "bi_rule", "db_password": "bi_rule_pass"
})
check("POST /data-sources/test-connection → 200", resp.status_code == 200)
check("ok == true", resp.json().get("ok") is True)

# 2.7 预览 (POST 端点，需要实际数据的表)
resp = api("post", f"/data-sources/{ds_id}/preview", params={"limit": 5})
check("POST /data-sources/{id}/preview → 200", resp.status_code == 200)
preview = resp.json()
# 预览可能返回空结果如果表没有数据
check("有 columns 或 sql", ("columns" in preview) or ("sql" in preview))
check("有 preview_rows 或 sql", ("preview_rows" in preview) or ("sql" in preview))

# ============================================================
# 3. 目标表 CRUD
# ============================================================
print("\n📋 3. 目标表管理 (8 端点)")

tt_payload = {
    "name": f"test_tt_{uuid.uuid4().hex[:8]}",
    "description": "API 测试目标表",
    "enabled": True,
    "db_host": "localhost",
    "db_port": 3306,
    "db_name": "bi_rule_engine",
    "db_username": "bi_rule",
    "db_password": "bi_rule_pass",
    "table_name": f"test_output_{uuid.uuid4().hex[:8]}",
    "write_mode": "append",
    "auto_create_table": True,
}

resp = api("post", "/target-tables", json=tt_payload)
check("POST /target-tables → 201", resp.status_code == 201)
tt = resp.json()
tt_id = tt.get("id")
check("返回 id", tt_id is not None)

resp = api("get", "/target-tables", params={"page": 1, "page_size": 10})
check("GET /target-tables → 200", resp.status_code == 200)

resp = api("get", "/target-tables/all")
check("GET /target-tables/all → 200", resp.status_code == 200)

resp = api("get", f"/target-tables/{tt_id}")
check("GET /target-tables/{id} → 200", resp.status_code == 200)

resp = api("put", f"/target-tables/{tt_id}", json={"description": "updated"})
check("PUT /target-tables/{id} → 200", resp.status_code == 200)

resp = api("post", "/target-tables/test-connection", json={
    "db_host": "localhost", "db_port": 3306, "db_name": "bi_rule_engine",
    "db_username": "bi_rule", "db_password": "bi_rule_pass",
    "table_name": "test", "write_mode": "append"
})
check("POST /target-tables/test-connection → 200", resp.status_code == 200)

# ============================================================
# 4. 规则集 CRUD
# ============================================================
print("\n📋 4. 规则集管理 (6 端点)")

rs_payload = {
    "name": f"test_rs_{uuid.uuid4().hex[:8]}",
    "description": "API 测试规则集",
    "color": "#52c41a",
    "sort_order": 0,
    "enabled": True,
}

resp = api("post", "/rule-sets", json=rs_payload)
check("POST /rule-sets → 201", resp.status_code == 201)
rs = resp.json()
rs_id = rs.get("id")
check("返回 id", rs_id is not None)

resp = api("get", "/rule-sets", params={"page": 1, "page_size": 10})
check("GET /rule-sets → 200", resp.status_code == 200)

resp = api("get", "/rule-sets/all")
check("GET /rule-sets/all → 200", resp.status_code == 200)

resp = api("get", f"/rule-sets/{rs_id}")
check("GET /rule-sets/{id} → 200", resp.status_code == 200)

resp = api("put", f"/rule-sets/{rs_id}", json={"description": "updated"})
check("PUT /rule-sets/{id} → 200", resp.status_code == 200)

# ============================================================
# 5. 规则 CRUD — 4 种类型全覆盖
# ============================================================
print("\n📋 5. 规则管理 (7 端点 + 4 种规则类型)")

# 5a. 条件映射规则
rule_mapping = {
    "rule_set_id": rs_id,
    "field_name": "test_mapping_field",
    "field_label": "测试映射字段",
    "rule_type": "mapping",
    "priority": 1,
    "enabled": True,
    "config": {
        "conditions": [
            {
                "id": "cg_001", "priority": 1, "logic": "AND",
                "rows": [{"id": "cr_001", "field": "source_col", "operator": "eq", "value": "A"}],
                "result_type": "constant", "result_value": "匹配A"
            },
            {
                "id": "cg_002", "priority": 2, "logic": "OR",
                "rows": [
                    {"id": "cr_002", "field": "source_col", "operator": "eq", "value": "B"},
                    {"id": "cr_003", "field": "source_col", "operator": "eq", "value": "C"},
                ],
                "result_type": "constant", "result_value": "匹配B或C"
            },
        ],
        "default_result": "默认值",
    },
    "depends_on": ["source_col"],
    "description": "条件映射规则测试",
}

resp = api("post", "/rules", json=rule_mapping)
check("POST /rules (mapping) → 201", resp.status_code == 201)
rule_mapping_id = resp.json().get("id")
check("返回 id", rule_mapping_id is not None)

# 5b. 数据清洗规则
rule_cleaning = {
    "rule_set_id": rs_id,
    "field_name": "test_cleaning_field",
    "field_label": "测试清洗字段",
    "rule_type": "cleaning",
    "priority": 2,
    "enabled": True,
    "config": {
        "cleaning_steps": [
            {"action": "fill_null", "value": "空值填充"},
            {"action": "trim"},
            {"action": "replace", "condition": {"field": "test_cleaning_field", "operator": "eq", "value": "old"}, "replacement": "new"},
        ],
    },
    "depends_on": [],
    "description": "数据清洗规则测试 — 3步清洗",
}

resp = api("post", "/rules", json=rule_cleaning)
check("POST /rules (cleaning) → 201", resp.status_code == 201)
rule_cleaning_id = resp.json().get("id")

# 5c. 字典查找规则
rule_lookup = {
    "rule_set_id": rs_id,
    "field_name": "test_lookup_field",
    "field_label": "测试查找字段",
    "rule_type": "lookup",
    "priority": 3,
    "enabled": True,
    "config": {
        "lookup_table_id": None,
        "lookup_key_field": "source_col",
        "lookup_value_field": "mapped_value",
        "lookup_fallbacks": [
            {"condition": {"field": "source_col", "operator": "eq", "value": "X"}, "value": "兜底X"},
        ],
    },
    "depends_on": ["source_col"],
    "description": "字典查找规则测试",
}

resp = api("post", "/rules", json=rule_lookup)
check("POST /rules (lookup) → 201", resp.status_code == 201)
rule_lookup_id = resp.json().get("id")

# 5d. 公式计算规则
rule_computed = {
    "rule_set_id": rs_id,
    "field_name": "test_computed_field",
    "field_label": "测试计算字段",
    "rule_type": "computed",
    "priority": 4,
    "enabled": True,
    "config": {
        "formula_expression": "COALESCE(test_mapping_field, 'N/A')",
    },
    "depends_on": ["test_mapping_field"],
    "description": "公式计算规则测试",
}

resp = api("post", "/rules", json=rule_computed)
check("POST /rules (computed) → 201", resp.status_code == 201)
rule_computed_id = resp.json().get("id")

# 5e. 规则列表 (含过滤)
resp = api("get", "/rules", params={"page": 1, "page_size": 20, "rule_set_id": rs_id})
check("GET /rules (filter by rule_set_id) → 200", resp.status_code == 200)
rules_data = resp.json()
check("返回 4 条规则", len(rules_data.get("items", [])) >= 4)

resp = api("get", "/rules", params={"rule_type": "mapping"})
check("GET /rules (filter mapping) → 200", resp.status_code == 200)

resp = api("get", "/rules", params={"rule_type": "cleaning"})
check("GET /rules (filter cleaning) → 200", resp.status_code == 200)

resp = api("get", "/rules", params={"rule_type": "computed"})
check("GET /rules (filter computed) → 200", resp.status_code == 200)

resp = api("get", "/rules", params={"rule_type": "lookup"})
check("GET /rules (filter lookup) → 200", resp.status_code == 200)

# 5f. 获取单个规则
resp = api("get", f"/rules/{rule_mapping_id}")
check("GET /rules/{id} → 200", resp.status_code == 200)

# 5g. 更新规则
resp = api("put", f"/rules/{rule_mapping_id}", json={"priority": 10})
check("PUT /rules/{id} → 200", resp.status_code == 200)

# 5h. 规则测试 — 条件映射
print("\n  📌 规则测试 — 条件映射:")
test_rows = [
    {"source_col": "A"},
    {"source_col": "B"},
    {"source_col": "C"},
    {"source_col": "D"},
]
resp = api("post", f"/rules/{rule_mapping_id}/test", json={"test_rows": test_rows})
check("POST /rules/{id}/test → 200", resp.status_code == 200)
test_result = resp.json()
results = test_result.get("results", [])
check("返回 4 行结果", len(results) == 4)
if len(results) >= 4:
    check("A → 匹配A", results[0].get("output_value") == "匹配A")
    check("B → 匹配B或C", results[1].get("output_value") == "匹配B或C")
    check("C → 匹配B或C", results[2].get("output_value") == "匹配B或C")
    check("D → 默认值", results[3].get("output_value") == "默认值")

# 5i. 规则测试 — 数据清洗
print("\n  📌 规则测试 — 数据清洗:")
test_rows_cleaning = [
    {"test_cleaning_field": None},
    {"test_cleaning_field": "  spaced  "},
    {"test_cleaning_field": "old"},
    {"test_cleaning_field": "normal"},
]
resp = api("post", f"/rules/{rule_cleaning_id}/test", json={"test_rows": test_rows_cleaning})
check("POST /rules/{id}/test (cleaning) → 200", resp.status_code == 200)
results_clean = resp.json().get("results", [])
if len(results_clean) >= 4:
    check("None → 空值填充", results_clean[0].get("output_value") == "空值填充")
    check("spaced → trimmed", results_clean[1].get("output_value") == "spaced")
    check("old → new", results_clean[2].get("output_value") == "new")

# 5j. 规则测试 — 公式计算
print("\n  📌 规则测试 — 公式计算:")
test_rows_computed = [
    {"test_mapping_field": "hello"},
    {"test_mapping_field": None},
]
resp = api("post", f"/rules/{rule_computed_id}/test", json={"test_rows": test_rows_computed})
check("POST /rules/{id}/test (computed) → 200", resp.status_code == 200)
results_comp = resp.json().get("results", [])
if len(results_comp) >= 2:
    check("COALESCE(hello) → hello", results_comp[0].get("output_value") == "hello")
    check("COALESCE(None) → N/A", results_comp[1].get("output_value") == "N/A")

# 5k. 批量优先级更新
resp = api("put", "/rules/batch-priority", json={
    "items": [
        {"id": rule_mapping_id, "priority": 100},
        {"id": rule_cleaning_id, "priority": 200},
    ]
})
check("PUT /rules/batch-priority → 200", resp.status_code == 200)

# ============================================================
# 6. 映射表 CRUD
# ============================================================
print("\n📋 6. 映射表管理 (6 端点)")

lt_payload = {
    "name": f"test_lt_{uuid.uuid4().hex[:8]}",
    "description": "测试映射表",
    "columns": {"key_col": "code", "value_col": "name"},
    "data": {"A001": "名称A", "A002": "名称B", "A003": "名称C"},
}

resp = api("post", "/lookup-tables", json=lt_payload)
check("POST /lookup-tables → 201", resp.status_code == 201)
lt_id = resp.json().get("id")
check("返回 id", lt_id is not None)

resp = api("get", "/lookup-tables", params={"page": 1, "page_size": 10})
check("GET /lookup-tables → 200", resp.status_code == 200)

resp = api("get", f"/lookup-tables/{lt_id}")
check("GET /lookup-tables/{id} → 200", resp.status_code == 200)

resp = api("put", f"/lookup-tables/{lt_id}", json={"description": "updated"})
check("PUT /lookup-tables/{id} → 200", resp.status_code == 200)

# 搜索
resp = api("get", "/lookup-tables", params={"search": lt_payload["name"][:5]})
check("GET /lookup-tables (search) → 200", resp.status_code == 200)

# ============================================================
# 7. ETL 任务 CRUD + 执行
# ============================================================
print("\n📋 7. ETL 调度任务 (10 端点)")

etl_payload = {
    "job_name": f"test_etl_{uuid.uuid4().hex[:8]}",
    "description": "测试 ETL 任务",
    "enabled": False,
    "data_source_id": ds_id,
    "target_table_id": tt_id,
    "rule_set_id": rs_id,
    "cron_expression": "0 3 * * *",
    "timezone": "Asia/Shanghai",
    "error_retry_count": 0,
    "timeout_seconds": 600,
}

resp = api("post", "/etl-jobs", json=etl_payload)
check("POST /etl-jobs → 201", resp.status_code == 201)
job = resp.json()
job_id = job.get("id")
check("返回 id", job_id is not None)

resp = api("get", "/etl-jobs", params={"page": 1, "page_size": 10})
check("GET /etl-jobs → 200", resp.status_code == 200)

resp = api("get", f"/etl-jobs/{job_id}")
check("GET /etl-jobs/{id} → 200", resp.status_code == 200)
check("含 data_source", resp.json().get("data_source") is not None)
check("含 target_table", resp.json().get("target_table") is not None)

resp = api("put", f"/etl-jobs/{job_id}", json={"description": "updated"})
check("PUT /etl-jobs/{id} → 200", resp.status_code == 200)

# Toggle
resp = api("post", f"/etl-jobs/{job_id}/toggle", params={"enabled": True})
check("POST /etl-jobs/{id}/toggle (enable) → 200", resp.status_code == 200)

resp = api("post", f"/etl-jobs/{job_id}/toggle", params={"enabled": False})
check("POST /etl-jobs/{id}/toggle (disable) → 200", resp.status_code == 200)

# 手动执行
resp = api("post", f"/etl-jobs/{job_id}/run")
check("POST /etl-jobs/{id}/run → 200", resp.status_code == 200)
run_result = resp.json()
run_id = run_result.get("run_id")
check("返回 run_id", run_id is not None)

# 执行历史
import time
time.sleep(2)  # 等待异步执行

resp = api("get", f"/etl-jobs/{job_id}/runs", params={"page": 1, "page_size": 10})
check("GET /etl-jobs/{id}/runs → 200", resp.status_code == 200)

resp = api("get", f"/etl-jobs/runs/{run_id}")
check("GET /etl-jobs/runs/{run_id} → 200", resp.status_code == 200)

resp = api("get", "/etl-jobs/runs", params={"page": 1, "page_size": 10})
# 这个端点可能不存在或返回 404
check("GET /etl-jobs/runs (all) → 200/404", resp.status_code in (200, 404))

# ============================================================
# 8. 任务管理 (上传执行)
# ============================================================
print("\n📋 8. 任务管理 (8 端点)")

# 创建测试 CSV
csv_content = "source_col,amount\nA,100\nB,200\nC,300\nD,400\nA,500\n"
csv_file = BytesIO(csv_content.encode())
files = {"file": ("test.csv", csv_file, "text/csv")}

resp = api("post", "/tasks/upload", files=files)
check("POST /tasks/upload → 200", resp.status_code == 200)
upload_data = resp.json()
check("有 columns", "columns" in upload_data)
check("total_rows == 5", upload_data.get("total_rows") == 5)
check("total_columns == 2", upload_data.get("total_columns") == 2)

# 上传执行 (需要重新创建文件对象)
csv_file2 = BytesIO(csv_content.encode())
files2 = {"file": ("test2.csv", csv_file2, "text/csv")}
resp = api("post", "/tasks/upload/execute", files=files2)
check("POST /tasks/upload/execute → 200", resp.status_code == 200, f"got {resp.status_code}: {resp.text[:200]}")
exec_data = resp.json()
task_id = exec_data.get("task_id")
check("返回 task_id", task_id is not None)
check("status == completed", exec_data.get("status") == "completed")

time.sleep(1)
# 查询任务状态
resp = api("get", f"/tasks/{task_id}/status")
check("GET /tasks/{id}/status → 200", resp.status_code == 200)

# 任务列表
resp = api("get", "/tasks", params={"page": 1, "page_size": 10})
check("GET /tasks → 200", resp.status_code == 200)

# ============================================================
# 9. 日志上报
# ============================================================
print("\n📋 9. 日志上报 (1 端点)")

resp = api("post", "/logs/frontend-error", json={
    "message": "Test error from API test",
    "stack": "Error: test\n    at test.js:1:1",
    "url": "http://localhost:5173/test",
    "user_agent": "TestAgent/1.0",
})
check("POST /logs/frontend-error → 204", resp.status_code == 204)

# ============================================================
# 10. 边界情况和错误处理
# ============================================================
print("\n📋 10. 边界情况与错误处理")

# 10a. 重复名称
resp = api("post", "/data-sources", json=ds_payload)
check("重复 name → 409", resp.status_code == 409)

# 10b. 无效 ID
resp = api("get", "/data-sources/nonexistent-id-12345")
check("不存在 ID → 404", resp.status_code == 404)

# 10c. 无效规则类型
invalid_rule = {**rule_mapping, "rule_type": "invalid_type"}
resp = api("post", "/rules", json=invalid_rule)
check("无效 rule_type → 422", resp.status_code == 422)

# 10d. 缺少必填字段
resp = api("post", "/rules", json={"field_name": "test"})
check("缺少必填字段 → 422", resp.status_code == 422)

# 10e. 空条件组
empty_mapping = {**rule_mapping, "config": {"conditions": [], "default_result": "empty"}}
resp = api("post", "/rules", json=empty_mapping)
check("空条件组创建 → 201", resp.status_code == 201)
empty_rule_id = resp.json().get("id")
# 测试空条件组规则
resp = api("post", f"/rules/{empty_rule_id}/test", json={
    "test_rows": [{"source_col": "A"}, {"source_col": "B"}]
})
check("空条件组测试 → 200", resp.status_code == 200)
# 空条件组所有行都走默认值，output_value 应为 "empty"
check("空条件组 → 默认值", all(
    r.get("output_value") == "empty"
    for r in resp.json().get("results", [])
))

# 10f. 删除有规则的规则集 (应该 400)
resp = api("delete", f"/rule-sets/{rs_id}")
check("有规则的规则集删除 → 400", resp.status_code == 400)

# 10g. 无效 cron (可能 422 或 400)
invalid_etl = {**etl_payload, "cron_expression": "invalid"}
resp = api("post", "/etl-jobs", json=invalid_etl)
check("无效 cron → 4xx", resp.status_code in (400, 422))

# 10h. 错误连接测试
resp = api("post", "/data-sources/test-connection", json={
    "db_host": "nonexistent.host", "db_port": 3306,
    "db_name": "test", "db_username": "test", "db_password": "test"
})
check("无效连接测试 → 400", resp.status_code == 400)

# ============================================================
# 11. 清理测试数据
# ============================================================
print("\n📋 11. 清理测试数据")

# 删除空条件组规则
resp = api("delete", f"/rules/{empty_rule_id}")
check(f"DELETE /rules/{empty_rule_id} → 204", resp.status_code == 204)

# 删除 ETL 任务
resp = api("delete", f"/etl-jobs/{job_id}")
check(f"DELETE /etl-jobs/{job_id} → 200", resp.status_code == 200)

# 删除规则
for rid in [rule_mapping_id, rule_cleaning_id, rule_lookup_id, rule_computed_id]:
    if rid:
        try:
            resp = api("delete", f"/rules/{rid}")
            check(f"DELETE /rules/{rid} → 204", resp.status_code == 204)
        except Exception as e:
            check(f"DELETE /rules/{rid} → 204", False, str(e))

# 删除规则集
resp = api("delete", f"/rule-sets/{rs_id}")
check(f"DELETE /rule-sets/{rs_id} → 200", resp.status_code == 200)

# 删除映射表
resp = api("delete", f"/lookup-tables/{lt_id}")
check(f"DELETE /lookup-tables/{lt_id} → 204", resp.status_code == 204)

# 删除目标表
resp = api("delete", f"/target-tables/{tt_id}")
check(f"DELETE /target-tables/{tt_id} → 200", resp.status_code == 200)

# 删除数据源
resp = api("delete", f"/data-sources/{ds_id}")
check(f"DELETE /data-sources/{ds_id} → 200", resp.status_code == 200)

# ============================================================
# 总结
# ============================================================
total = passed + failed
print(f"\n{'='*70}")
print(f"测试结果: {passed}/{total} 通过, {failed} 失败")
if failed == 0:
    print("🎉 所有测试通过!")
else:
    print(f"⚠️  {failed} 个测试失败，需要修复!")
print(f"{'='*70}")
