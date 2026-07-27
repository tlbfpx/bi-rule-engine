"""
将 Excel 中的 11 条规则批量导入到 BI 规则引擎系统。

每条规则按 Excel 中的映射规则描述，转换为系统的 ConditionGroup 格式。
"""
import requests
import json

BASE = "http://localhost:8000/api/v1"
HEADERS = {"Content-Type": "application/json"}


def post(path, data):
    r = requests.post(f"{BASE}{path}", json=data, headers=HEADERS)
    if r.status_code not in (200, 201):
        print(f"  ERROR {r.status_code}: {r.text}")
    else:
        print(f"  OK {r.status_code}")
    return r


def make_cond_group(priority, rows, result_type="constant", result_value=None, logic="AND"):
    """快速构建一个条件组"""
    cond_rows = []
    for i, (field, op, val) in enumerate(rows):
        cond_rows.append({
            "id": f"c_{priority}_{i+1}",
            "field": field,
            "operator": op,
            "value": val,
        })
    return {
        "id": f"g_{priority}",
        "priority": priority,
        "logic": logic,
        "rows": cond_rows,
        "result_type": result_type,
        "result_value": result_value,
    }


def make_config(conditions=None, cleaning_steps=None, lookup_table_id=None,
                lookup_key_field=None, lookup_value_field=None, lookup_fallbacks=None,
                formula_expression=None, default_result=None):
    return {
        "conditions": conditions or [],
        "cleaning_steps": cleaning_steps or [],
        "lookup_table_id": lookup_table_id,
        "lookup_key_field": lookup_key_field,
        "lookup_value_field": lookup_value_field,
        "lookup_fallbacks": lookup_fallbacks or [],
        "formula_expression": formula_expression,
        "default_result": default_result,
    }


def ensure_rule_set(name="体检映射规则", description="源自 Excel《体检映射规则》的 11 条字段映射/清洗/计算规则"):
    """确保业务线（规则集）存在，返回其 id。"""
    r = requests.get(f"{BASE}/rule-sets/all", headers=HEADERS)
    for rs in r.json().get("items", []):
        if rs["name"] == name:
            return rs["id"]
    r = requests.post(f"{BASE}/rule-sets", json={"name": name, "description": description, "color": "#1677ff"}, headers=HEADERS)
    if r.status_code not in (200, 201):
        print(f"  创建规则集失败 {r.status_code}: {r.text}")
        return None
    print(f"  已创建规则集「{name}」")
    return r.json()["id"]


def existing_rule_ids(rule_set_id):
    """返回该规则集下 {field_name: rule_id} 映射（用于幂等 upsert）。"""
    r = requests.get(f"{BASE}/rules", params={"rule_set_id": rule_set_id, "page_size": 200}, headers=HEADERS)
    return {item["field_name"]: item["id"] for item in r.json().get("items", [])}


def import_all():
    rules = [
        # ===== 1. gmt_effect_end - 结算账户名称 (映射：条件覆盖原始值) =====
        # 注：逻辑为"账户为空且合作方含平安好医→取合作方名；合作方为指定中心→替换固定值"，
        # 本质是条件映射。rule_type 用 mapping 才能让 conditions 生效（cleaning 只读 cleaning_steps）。
        {
            "field_name": "gmt_effect_end",
            "field_label": "结算账户名称",
            "rule_type": "mapping",
            "priority": 1,
            "enabled": True,
            "description": "若账户名为空且合作方名称包含平安好医，则取合作方名称；若合作方为指定中心，则指定为固定值",
            "depends_on": ["partner_name"],
            "config": make_config(
                conditions=[
                    make_cond_group(1, [
                        ("gmt_effect_end", "is_null", None),
                        ("partner_name", "contains", "平安好医"),
                    ], "field_value", "partner_name"),
                    make_cond_group(2, [
                        ("partner_name", "eq", "平安健康（检测）上海旗舰中心"),
                    ], "constant", "上海平安好医创智门诊部有限公司"),
                ],
                default_result="keep_original",
            ),
        },

        # ===== 2. rate_2 - 适用税率 (映射) =====
        {
            "field_name": "rate_2",
            "field_label": "适用税率",
            "rule_type": "mapping",
            "priority": 2,
            "enabled": True,
            "description": "公司段值930000/840000为0，其他为0.06",
            "depends_on": ["company_segment_code"],
            "config": make_config(
                conditions=[
                    make_cond_group(1, [
                        ("company_segment_code", "in", "930000,840000"),
                    ], "constant", "0"),
                    make_cond_group(2, [
                        ("company_segment_code", "is_not_null", None),
                    ], "constant", "0.06"),
                ],
                default_result="0.06",
            ),
        },

        # ===== 3. if_reject - 是否剔除 (映射) =====
        {
            "field_name": "if_reject",
            "field_label": "是否剔除",
            "rule_type": "mapping",
            "priority": 3,
            "enabled": True,
            "description": "团体体检类标记不剔除；产品段P10011/P10012无剔除原因时标记不剔除",
            "depends_on": ["prod_class", "product_segment_code", "reject_reason"],
            "config": make_config(
                conditions=[
                    make_cond_group(1, [
                        ("prod_class", "eq", "团体体检"),
                    ], "constant", "不剔除"),
                    make_cond_group(2, [
                        ("product_segment_code", "in", "P10011,P10012"),
                        ("reject_reason", "is_null", None),
                    ], "constant", "不剔除"),
                ],
                default_result="keep_original",
            ),
        },

        # ===== 4. prod_class - 产品分类 (映射 - 4级优先级链) =====
        {
            "field_name": "prod_class",
            "field_label": "产品分类",
            "rule_type": "mapping",
            "priority": 4,
            "enabled": True,
            "description": "根据卡片名称、企业单名称、财务产品按优先级推导：集团体检/团体体检/其他",
            "depends_on": ["card_product_seg_name", "card_name", "eorder_name", "fin_product"],
            "config": make_config(
                conditions=[
                    make_cond_group(1, [
                        ("card_product_seg_name", "is_not_null", None),
                    ], "field_value", "card_product_seg_name"),
                    make_cond_group(2, [
                        ("card_product_seg_name", "is_null", None),
                        ("card_name", "eq", "团体体检销管流转健管专用"),
                        ("eorder_name", "contains", "平安集团员工体检"),
                    ], "constant", "集团体检"),
                    make_cond_group(3, [
                        ("card_product_seg_name", "is_null", None),
                        ("fin_product", "eq", "集团体检"),
                        ("card_name", "not_contains", "团体体检"),
                    ], "constant", "集团体检"),
                    make_cond_group(4, [
                        ("card_product_seg_name", "is_null", None),
                        ("card_name", "matches", "团体体检|体检|套餐"),
                        ("eorder_name", "not_contains", "平安集团员工体检"),
                    ], "constant", "团体体检"),
                    make_cond_group(5, [
                        ("card_product_seg_name", "is_null", None),
                        ("fin_product", "contains", "团体体检"),
                    ], "constant", "团体体检"),
                ],
                default_result="其他",
            ),
        },

        # ===== 5. company_segment_code - 公司段值 (清洗) =====
        {
            "field_name": "company_segment_code",
            "field_label": "公司段值",
            "rule_type": "cleaning",
            "priority": 5,
            "enabled": True,
            "description": "将 company_segment_code 的空值转换为 '972400'",
            "depends_on": [],
            "config": make_config(
                cleaning_steps=[
                    {"id": "s1", "action": "fill_null", "params": {"fill_value": "972400"}},
                ],
            ),
        },

        # ===== 6. buyer_name - 采购主体段值 (映射 - 字典查找) =====
        {
            "field_name": "buyer_name",
            "field_label": "采购主体段值",
            "rule_type": "mapping",
            "priority": 6,
            "enabled": True,
            "description": "采购名称映射：宁波→971500，广东→970200 等",
            "depends_on": ["buyer_contract_name"],
            "config": make_config(
                conditions=[
                    make_cond_group(1, [("buyer_contract_name", "contains", "宁波")], "constant", "971500"),
                    make_cond_group(2, [("buyer_contract_name", "contains", "广东")], "constant", "970200"),
                    make_cond_group(3, [("buyer_contract_name", "contains", "海南互联网")], "constant", "840000"),
                    make_cond_group(4, [("buyer_contract_name", "contains", "海南")], "constant", "972400"),
                    make_cond_group(5, [("buyer_contract_name", "contains", "湖北")], "constant", "970700"),
                    make_cond_group(6, [("buyer_contract_name", "contains", "陕西")], "constant", "970300"),
                    make_cond_group(7, [("buyer_contract_name", "contains", "青岛")], "constant", "930000"),
                    make_cond_group(8, [("buyer_contract_name", "contains", "上海")], "constant", "970100"),
                    make_cond_group(9, [("buyer_contract_name", "contains", "北京")], "constant", "970500"),
                    make_cond_group(10, [("buyer_contract_name", "contains", "总公司")], "constant", "970000"),
                ],
                default_result="keep_original",
            ),
        },

        # ===== 7. upd_eorder_name - 企业单关联方 (computed - 复杂) =====
        {
            "field_name": "upd_eorder_name",
            "field_label": "企业单关联方",
            "rule_type": "computed",
            "priority": 7,
            "enabled": True,
            "description": "拆分 eorder_name + 嵌套条件判断：盟宠→盟宠生态，好医→拆分取第6部分",
            "depends_on": ["eorder_name"],
            "config": make_config(
                formula_expression="IF(CONTAINS(eorder_name, '盟宠') AND (upd_eorder_name_temp = '平安健康'), '盟宠生态', IF(CONTAINS(eorder_name, '好医') AND (upd_eorder_name_temp = '平安健康'), SPLIT(eorder_name, '-', 6), upd_eorder_name_temp))",
                conditions=[
                    make_cond_group(1, [
                        ("eorder_name", "is_not_null", None),
                        ("eorder_name", "matches", "^(?!2022_).*"),
                    ], "field_value", None),  # SPLIT(eorder_name, '-', 4) - 前端公式处理
                    make_cond_group(2, [
                        ("eorder_name", "is_not_null", None),
                        ("eorder_name", "starts_with", "2022_"),
                    ], "field_value", None),  # SPLIT(eorder_name, '-', 2)
                ],
                default_result=None,
            ),
        },

        # ===== 8. product_segment_code - 产品段值 (lookup + 兜底) =====
        {
            "field_name": "product_segment_code",
            "field_label": "产品段值",
            "rule_type": "lookup",
            "priority": 8,
            "enabled": True,
            "description": "取映射表 fin_card_mapping_total_d_temp，兜底：集团体检→P10011，团体体检→P10012",
            "depends_on": ["prod_class", "card_name"],
            "config": make_config(
                lookup_table_id=None,
                lookup_key_field="card_name",
                lookup_value_field="product_segment_code",
                lookup_fallbacks=[
                    {
                        "id": "fb1",
                        "condition_field": "prod_class",
                        "condition_operator": "eq",
                        "condition_value": "集团体检",
                        "fallback_value": "P10011",
                    },
                    {
                        "id": "fb2",
                        "condition_field": "prod_class",
                        "condition_operator": "eq",
                        "condition_value": "团体体检",
                        "fallback_value": "P10012",
                    },
                ],
            ),
        },

        # ===== 9. is_spec_reject - 是否特殊业务剔除 (映射) =====
        {
            "field_name": "is_spec_reject",
            "field_label": "是否特殊业务剔除",
            "rule_type": "mapping",
            "priority": 9,
            "enabled": True,
            "description": "buyer_contract_id = 'CG-2025PAJKSH119487' 则为'是'，否则保持原值（null转为空）",
            "depends_on": ["buyer_contract_id"],
            "config": make_config(
                conditions=[
                    make_cond_group(1, [
                        ("buyer_contract_id", "eq", "CG-2025PAJKSH119487"),
                    ], "constant", "是"),
                ],
                default_result="keep_original",
            ),
        },

        # ===== 10. sum_fin_ar - 应收账款金额 (computed) =====
        {
            "field_name": "sum_fin_ar",
            "field_label": "应收账款金额",
            "rule_type": "computed",
            "priority": 10,
            "enabled": True,
            "description": "公司段值930000/840000 → sum_fin_rev；其他 → ROUND(sum_fin_rev * 1.06, 2)",
            "depends_on": ["company_segment_code", "sum_fin_rev"],
            "config": make_config(
                formula_expression="IF(company_segment_code IN ('930000', '840000'), sum_fin_rev, ROUND(sum_fin_rev * 1.06, 2))",
            ),
        },

        # ===== 11. ar_balance - 应收余额 (computed) =====
        {
            "field_name": "ar_balance",
            "field_label": "应收余额",
            "rule_type": "computed",
            "priority": 11,
            "enabled": True,
            "description": "如果 pay_amount > sum_fin_ar 则返回 COALESCE(pay_amount,0) - sum_fin_ar，否则返回 0",
            "depends_on": ["pay_amount", "sum_fin_ar"],
            "config": make_config(
                formula_expression="IF(pay_amount > sum_fin_ar, COALESCE(pay_amount, 0) - sum_fin_ar, 0)",
            ),
        },
    ]

    print("开始批量导入 11 条规则...\n")

    rule_set_id = ensure_rule_set()
    existing = existing_rule_ids(rule_set_id) if rule_set_id else {}

    created, updated = 0, 0
    for i, rule in enumerate(rules, 1):
        rule["rule_set_id"] = rule_set_id
        label = f"{rule['field_name']} ({rule['field_label']}) - {rule['rule_type']}"
        rid = existing.get(rule["field_name"])
        if rid:
            r = requests.put(f"{BASE}/rules/{rid}", json=rule, headers=HEADERS)
            tag = f"更新 OK" if r.status_code in (200, 201) else f"更新 ERROR {r.status_code}: {r.text}"
            print(f"[{i}/11] {label} - {tag}")
            if r.status_code in (200, 201):
                updated += 1
        else:
            r = post("/rules", rule)
            if r.status_code in (200, 201):
                created += 1

    print(f"\n新建 {created} 条，更新 {updated} 条")

    # 验证
    r = requests.get(f"{BASE}/rules?page_size=50", headers=HEADERS)
    data = r.json()
    print(f"\n✅ 导入完成！共 {data['total']} 条规则")
    for item in data["items"]:
        print(f"  [{item['rule_type']}] {item['field_name']}: {item['field_label']} (优先级 {item['priority']})")


if __name__ == "__main__":
    import_all()
