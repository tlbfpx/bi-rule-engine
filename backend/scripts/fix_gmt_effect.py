import requests, json

BASE = "http://localhost:8000/api/v1"

# 找到规则 ID
r = requests.get(f"{BASE}/rules?page_size=50&field_name=gmt_effect_end")
rule = r.json()["items"][0]
rid = rule["id"]
print(f"Updating rule: {rid} ({rule['field_name']})")

# 正确配置：条件映射类型，两级优先级
new_config = {
    "conditions": [
        {
            "id": "g_1",
            "priority": 1,
            "logic": "AND",
            "rows": [
                {"id": "c_1_1", "field": "gmt_effect_end", "operator": "is_null", "value": None},
                {"id": "c_1_2", "field": "partner_name", "operator": "eq", "value": "平安健康（检测）上海旗舰中心"},
            ],
            "result_type": "constant",
            "result_value": "上海平安好医创智门诊部有限公司",
        },
        {
            "id": "g_2",
            "priority": 2,
            "logic": "AND",
            "rows": [
                {"id": "c_2_1", "field": "gmt_effect_end", "operator": "is_null", "value": None},
                {"id": "c_2_2", "field": "partner_name", "operator": "contains", "value": "平安好医"},
            ],
            "result_type": "field_value",
            "result_value": "partner_name",
        },
    ],
    "cleaning_steps": [],
    "lookup_table_id": None,
    "lookup_key_field": None,
    "lookup_value_field": None,
    "lookup_fallbacks": [],
    "formula_expression": None,
    "default_result": "keep_original",
}

resp = requests.put(
    f"{BASE}/rules/{rid}",
    json={
        "rule_type": "mapping",
        "field_label": "结算账户名称",
        "description": "若账户名为空且合作方名称包含平安好医，则取合作方名称；若��作方为指定中心，则指定为固定值",
        "depends_on": ["partner_name"],
        "config": new_config,
    },
    headers={"Content-Type": "application/json"},
)
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
