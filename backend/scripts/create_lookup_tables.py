"""
创建映射表数据并关联到规则。
Excel 中的规则引用了 fin_card_mapping_total_d_temp 映射表，
用于产品段值的查找。
"""
import requests
import json

BASE = "http://localhost:8000/api/v1"

# ============ 1. 创建产品段值映射表 ============
print("1. 创建产品段值映射表...")

# 模拟常见体检卡片到产品段的映射
card_mapping = {
    "团体体检销管流转健管专用": "P10011",
    "团体体检套餐A": "P10012",
    "团体体检套餐B": "P10012",
    "体检套餐基础版": "P10012",
    "集团员工体检套餐": "P10011",
    "入职体检套餐": "P10012",
    "高端体检套餐": "P10012",
    "企业年度体检": "P10012",
    "平安集团员工体检": "P10011",
    "团体体检标准版": "P10012",
}

r = requests.post(f"{BASE}/lookup-tables", json={
    "name": "fin_card_mapping_total_d_temp",
    "description": "卡片名称到产品段值的映射表（P10011=集团体检, P10012=团体体检）",
    "source_type": "manual",
    "columns": {"key_col": "card_name", "value_col": "product_segment_code"},
    "data": card_mapping,
})
if r.status_code in (200, 201):
    table = r.json()
    table_id = table["id"]
    print(f"   创建成功: {table['name']} (ID: {table_id}, {table['row_count']}行)")
else:
    print(f"   失败: {r.status_code} {r.text}")
    table_id = None

# ============ 2. 关联到 product_segment_code 规则 ============
if table_id:
    print("\n2. 关联映射表到 product_segment_code 规则...")
    
    # 找到规则 ID
    r = requests.get(f"{BASE}/rules?page_size=50&field_name=product_segment_code")
    rules = r.json()["items"]
    if rules:
        rule = rules[0]
        rid = rule["id"]
        
        # 更新规则，设置 lookup_table_id
        config = rule["config"]
        config["lookup_table_id"] = table_id
        config["lookup_key_field"] = "card_name"
        config["lookup_value_field"] = "product_segment_code"
        
        r = requests.put(f"{BASE}/rules/{rid}", json={
            "lookup_table_id": table_id,
            "config": config,
        })
        if r.status_code == 200:
            updated = r.json()
            print(f"   关联成功: {updated['field_name']} → lookup_table={updated['lookup_table_id']}")
        else:
            print(f"   失败: {r.status_code}")
    else:
        print("   未找到 product_segment_code 规则")

# ============ 3. 创建采购主体映射表（buyer_name 也可用） ============
print("\n3. 创建采购主体映射表...")

buyer_mapping = {
    "宁波": "971500",
    "广东": "970200",
    "海南": "972400",
    "湖北": "970700",
    "陕西": "970300",
    "青岛": "930000",
    "上海": "970100",
    "北京": "970500",
    "总公司": "970000",
    "海南互联网": "840000",
}

r = requests.post(f"{BASE}/lookup-tables", json={
    "name": "buyer_name_mapping",
    "description": "采购主体名称到公司段值的映射表",
    "source_type": "manual",
    "columns": {"key_col": "buyer_contract_name", "value_col": "company_segment_code"},
    "data": buyer_mapping,
})
if r.status_code in (200, 201):
    table2 = r.json()
    print(f"   创建成功: {table2['name']} (ID: {table2['id']}, {table2['row_count']}行)")
else:
    print(f"   失败: {r.status_code} {r.text}")

# ============ 4. 验证 ============
print("\n4. 验证...")
r = requests.get(f"{BASE}/lookup-tables?page_size=50")
tables = r.json()
print(f"   共 {tables['total']} 个映射表:")
for t in tables["items"]:
    print(f"     - {t['name']}: {t['row_count']} 行 ({t['columns']['key_col']} → {t['columns']['value_col']})")

print("\n✅ 完成！")
