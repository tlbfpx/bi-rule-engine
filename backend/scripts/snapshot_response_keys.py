"""
抓取各 API 端点响应的「字段集合」快照，用于 C3 改造前后 diff。
只关心字段名集合（顶层 / items 元素 / 嵌套对象），不关心值。

用法：python scripts/snapshot_response_keys.py > /tmp/before.txt
"""
import json
import requests

BASE = "http://localhost:8000/api/v1"


def keys_of(obj):
    return sorted(obj.keys()) if isinstance(obj, dict) else []


def nested_keys(obj, *path):
    cur = obj
    for p in path:
        if not isinstance(cur, dict):
            return []
        cur = cur.get(p)
    return keys_of(cur)


def show(label, resp):
    if resp.status_code != 200:
        print(f"{label}: HTTP {resp.status_code}")
        return
    data = resp.json()
    top = keys_of(data)
    item = keys_of(data["items"][0]) if isinstance(data, dict) and data.get("items") else keys_of(data)
    lines = [f"{label}", f"  top   = {top}", f"  item  = {item}"]
    # 嵌套对象
    sample = data["items"][0] if isinstance(data, dict) and data.get("items") else data
    for fld in ("data_source", "target_table", "etl_job"):
        if isinstance(sample, dict) and isinstance(sample.get(fld), dict):
            lines.append(f"  {fld} = {keys_of(sample[fld])}")
    print("\n".join(lines))


def main():
    # 取一些已有 id
    rule_id = requests.get(f"{BASE}/rules", params={"page_size": 1}).json()["items"][0]["id"]
    rs_id = requests.get(f"{BASE}/rule-sets/all").json()["items"][0]["id"]
    jobs = requests.get(f"{BASE}/etl-jobs", params={"page_size": 1}).json().get("items", [])
    job_id = jobs[0]["id"] if jobs else None
    runs = requests.get(f"{BASE}/etl-jobs/runs", params={"page_size": 1}).json().get("items", []) if jobs else []
    run_id = runs[0]["id"] if runs else None
    ds_id = requests.get(f"{BASE}/data-sources", params={"page_size": 1}).json()["items"][0]["id"]
    tt_id = requests.get(f"{BASE}/target-tables", params={"page_size": 1}).json()["items"][0]["id"]
    lt_id = requests.get(f"{BASE}/lookup-tables", params={"page_size": 1}).json()["items"][0]["id"]
    tasks = requests.get(f"{BASE}/tasks", params={"page_size": 1}).json().get("items", [])
    task_id = tasks[0]["id"] if tasks else None

    show("GET /rules", requests.get(f"{BASE}/rules", params={"page_size": 1}))
    show("GET /rules/{id}", requests.get(f"{BASE}/rules/{rule_id}"))
    show("GET /rule-sets", requests.get(f"{BASE}/rule-sets", params={"page_size": 1}))
    show("GET /rule-sets/all", requests.get(f"{BASE}/rule-sets/all"))
    show("GET /rule-sets/{id}", requests.get(f"{BASE}/rule-sets/{rs_id}"))
    if job_id:
        show("GET /etl-jobs", requests.get(f"{BASE}/etl-jobs", params={"page_size": 1}))
        show("GET /etl-jobs/{id}", requests.get(f"{BASE}/etl-jobs/{job_id}"))
    if run_id:
        show("GET /etl-jobs/runs", requests.get(f"{BASE}/etl-jobs/runs", params={"page_size": 1}))
        show("GET /etl-jobs/runs/{id}", requests.get(f"{BASE}/etl-jobs/runs/{run_id}"))
    show("GET /data-sources", requests.get(f"{BASE}/data-sources", params={"page_size": 1}))
    show("GET /data-sources/{id}", requests.get(f"{BASE}/data-sources/{ds_id}"))
    show("GET /target-tables", requests.get(f"{BASE}/target-tables", params={"page_size": 1}))
    show("GET /target-tables/{id}", requests.get(f"{BASE}/target-tables/{tt_id}"))
    show("GET /lookup-tables", requests.get(f"{BASE}/lookup-tables", params={"page_size": 1}))
    show("GET /lookup-tables/{id}", requests.get(f"{BASE}/lookup-tables/{lt_id}"))
    show("GET /tasks", requests.get(f"{BASE}/tasks", params={"page_size": 1}))
    if task_id:
        show("GET /tasks/{id}/status", requests.get(f"{BASE}/tasks/{task_id}/status"))


if __name__ == "__main__":
    main()
