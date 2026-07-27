"""更新公式计算规则的 DSL 语法为正确格式"""
import requests, json

BASE = "http://localhost:8000/api/v1"

# ar_balance: IF(pay_amount > sum_fin_ar, COALESCE(pay_amount, 0) - sum_fin_ar, 0)
# sum_fin_ar: IF(company_segment_code IN ('930000', '840000'), sum_fin_rev, ROUND(sum_fin_rev * 1.06, 2))
# upd_eorder_name: 复杂嵌套公式

formulas = {
    "ar_balance": 'IF(pay_amount > sum_fin_ar, COALESCE(pay_amount, 0) - sum_fin_ar, 0)',
    "sum_fin_ar": "IF(company_segment_code IN ('930000', '840000'), sum_fin_rev, ROUND(sum_fin_rev * 1.06, 2))",
    "upd_eorder_name": "IF(CONTAINS(eorder_name, '盟宠') AND upd_eorder_name_temp = '平安健康', '盟宠生态', IF(CONTAINS(eorder_name, '好医') AND upd_eorder_name_temp = '平安健康', SPLIT(eorder_name, '-', 6), upd_eorder_name_temp))",
}

for field_name, formula in formulas.items():
    r = requests.get(f"{BASE}/rules?page_size=50&field_name={field_name}")
    items = r.json()["items"]
    if not items:
        print(f"  {field_name}: 规则不存在")
        continue

    rule = items[0]
    config = rule["config"]
    config["formula_expression"] = formula

    resp = requests.put(
        f"{BASE}/rules/{rule['id']}",
        json={"config": config},
        headers={"Content-Type": "application/json"},
    )
    if resp.status_code == 200:
        print(f"  {field_name}: ✅ 已更新 → {formula[:60]}...")
    else:
        print(f"  {field_name}: ❌ {resp.status_code}")

print("\n完成！")
