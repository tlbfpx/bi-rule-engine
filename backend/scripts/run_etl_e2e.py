"""
真实 ETL 端到端验证：本地 MySQL 源表 → 11 条体检规则 → 目标表。

流程：
  1. 把 11 行测试数据写入源表 src_medical_checkup
  2. 创建 DataSource / TargetTable / ETLJob（关联「体检映射规则」规则集）
  3. POST /etl-jobs/{id}/run 触发后台执行
  4. 轮询执行记录直到完成
  5. 查询目标表 tgt_medical_checkup，校验关键字段（rate_2 / sum_fin_ar / ar_balance / prod_class）

幂等：同名 DataSource/TargetTable 先删后建；源/目标表 DROP IF EXISTS。
"""
import time
import pymysql
import polars as pl
import requests

BASE = "http://localhost:8000/api/v1"
H = {"Content-Type": "application/json"}
DB = dict(host="127.0.0.1", port=3306, user="bi_rule", password="bi_rule_pass", database="bi_rule_engine")
SRC_TABLE = "src_medical_checkup"
TGT_TABLE = "tgt_medical_checkup"
FIXTURE = "/Users/muxi/workspace/unipost/bi-rule-engine/storage/test_data_体检规则_全覆盖.xlsx"

DB_CONN = dict(db_host="127.0.0.1", db_port=3306, db_username="bi_rule", db_password="bi_rule_pass", db_name="bi_rule_engine")


def polars_dtype_to_mysql(dtype) -> str:
    s = str(dtype)
    if "Float" in s:
        return "DOUBLE"
    if s == "Int64":
        return "BIGINT"
    return "VARCHAR(255) NULL"


def prepare_source():
    df = pl.read_excel(FIXTURE)
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS `{SRC_TABLE}`")
            cols = ", ".join(f"`{c}` {polars_dtype_to_mysql(dt)}" for c, dt in zip(df.columns, df.dtypes))
            cur.execute(f"CREATE TABLE `{SRC_TABLE}` ({cols}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
            ph = ", ".join(["%s"] * len(df.columns))
            collist = ", ".join(f"`{c}`" for c in df.columns)
            rows = [tuple(None if v is None else v for v in r) for r in df.rows()]
            cur.executemany(f"INSERT INTO `{SRC_TABLE}` ({collist}) VALUES ({ph})", rows)
        conn.commit()
    finally:
        conn.close()
    cur2 = pymysql.connect(**DB).cursor()
    cur2.execute(f"SELECT COUNT(*) FROM `{SRC_TABLE}`")
    n = cur2.fetchone()[0]
    cur2.close()
    print(f"[源] {SRC_TABLE}: {n} 行 × {len(df.columns)} 列")
    return df


def _find(collection_url, name):
    items = requests.get(f"{BASE}{collection_url}", params={"page_size": 200}, headers=H).json().get("items", [])
    return next((i["id"] for i in items if i["name"] == name), None)


def get_or_create(name, collection_url, payload):
    """存在则复用（避免 FK RESTRICT 导致的删除失败）；不存在则创建。"""
    existing = _find(collection_url, name)
    if existing:
        print(f"[配] {name}: 复用 {existing}")
        return existing
    r = requests.post(f"{BASE}{collection_url}", json=payload, headers=H)
    assert r.status_code in (200, 201), f"创建 {name} 失败: {r.status_code} {r.text}"
    print(f"[配] {name}: {r.json().get('id')}")
    return r.json()["id"]


def setup_pipeline():
    src_id = get_or_create("e2e-数据源-体检", "/data-sources", {
        "name": "e2e-数据源-体检", "enabled": True, **DB_CONN,
        "extract_mode": "table", "extract_table": SRC_TABLE,
    })
    tgt_id = get_or_create("e2e-目标表-体检", "/target-tables", {
        "name": "e2e-目标表-体检", "enabled": True, **DB_CONN,
        "table_name": TGT_TABLE, "write_mode": "truncate_insert",
        "upsert_keys": [], "auto_create_table": True,
    })
    rs_id = next(i["id"] for i in requests.get(f"{BASE}/rule-sets/all", headers=H).json()["items"]
                 if i["name"] == "体检映射规则")
    # ETLJob：按 job_name 复用，否则创建
    jobs = requests.get(f"{BASE}/etl-jobs", params={"page_size": 200}, headers=H).json()["items"]
    job = next((j["id"] for j in jobs if j["job_name"] == "e2e-ETL-体检"), None)
    if job:
        print(f"[配] ETLJob e2e-ETL-体检: 复用 {job}")
        return job
    r = requests.post(f"{BASE}/etl-jobs", json={
        "job_name": "e2e-ETL-体检", "enabled": False,
        "data_source_id": src_id, "target_table_id": tgt_id, "rule_set_id": rs_id,
        "cron_expression": "0 3 * * *", "timezone": "Asia/Shanghai",
        "error_retry_count": 0, "timeout_seconds": 3600,
    }, headers=H)
    assert r.status_code in (200, 201), f"创建 ETLJob 失败: {r.status_code} {r.text}"
    print(f"[配] ETLJob e2e-ETL-体检: {r.json()['id']}")
    return r.json()["id"]


def run_and_wait(job_id):
    r = requests.post(f"{BASE}/etl-jobs/{job_id}/run", headers=H)
    assert r.status_code == 200, f"触发失败: {r.status_code} {r.text}"
    run_id = r.json()["run_id"]
    print(f"[跑] run_id={run_id}，轮询...")
    for _ in range(30):
        time.sleep(1)
        run = requests.get(f"{BASE}/etl-jobs/runs/{run_id}", headers=H).json()
        if run["status"] in ("completed", "failed"):
            print(f"[跑] 状态={run['status']} 输入{run.get('input_rows')}→输出{run.get('output_rows')} 耗时{run.get('duration_ms')}ms")
            if run["status"] == "failed":
                print(f"     error_log: {run.get('error_log')}")
                print(f"     executed_sql: {run.get('executed_sql')}")
            return run
    raise TimeoutError("ETL 执行超时")


def verify_target(expected_rows: int):
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(f"SELECT * FROM `{TGT_TABLE}` ORDER BY `uid`")
            rows = cur.fetchall()
    finally:
        conn.close()
    assert len(rows) == expected_rows, f"目标表行数 {len(rows)} != {expected_rows}"
    # 抽几列核对（uid 升序对应 fixture 的 u1..u11）
    print(f"[验] 目标表 {len(rows)} 行，关键字段：")
    for r in rows:
        print(f"     uid={r.get('uid')} prod_class={r.get('prod_class')!s:<10} rate_2={r.get('rate_2')} "
              f"prod_seg={r.get('product_segment_code')} sum_fin_ar={r.get('sum_fin_ar')} "
              f"ar_balance={r.get('ar_balance')} if_reject={r.get('if_reject')} buyer={r.get('buyer_name')}")
    # 关键断言：u1(930000→rate_2=0,sum_fin_ar=1000,ar_balance=500,upd=盟宠生态,buyer=971500)
    u1 = next(r for r in rows if r["uid"] == "u1")
    assert float(u1["rate_2"]) == 0.0, u1["rate_2"]
    assert float(u1["sum_fin_ar"]) == 1000.0, u1["sum_fin_ar"]
    assert float(u1["ar_balance"]) == 500.0, u1["ar_balance"]
    assert u1["upd_eorder_name"] == "盟宠生态", u1["upd_eorder_name"]
    assert str(u1["buyer_name"]) == "971500", u1["buyer_name"]
    # u5: company_segment_code 原为 null → 清洗为 972400 → rate_2=0.06, sum_fin_ar=212, ar_balance=787
    u5 = next(r for r in rows if r["uid"] == "u5")
    assert str(u5["company_segment_code"]) == "972400", u5["company_segment_code"]
    assert float(u5["sum_fin_ar"]) == 212.0, u5["sum_fin_ar"]
    assert float(u5["ar_balance"]) == 787.0, u5["ar_balance"]
    print("\n✅ ETL 端到端验证通过：DB→11规则→DB，关键字段全部正确")


def main():
    df = prepare_source()
    job_id = setup_pipeline()
    run = run_and_wait(job_id)
    if run["status"] != "completed":
        raise SystemExit("ETL 执行失败，见上")
    verify_target(df.height)


if __name__ == "__main__":
    main()
