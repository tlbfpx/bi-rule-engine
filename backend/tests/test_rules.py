"""端到端测试 — 基于 Excel 体检映射规则的完整测试"""
import polars as pl
from app.engine.parser import RuleParser
from app.engine.executor import RuleExecutor
from app.engine.dependency import topological_sort, CyclicDependencyError

# ─── Excel 中的 11 条规则 ───

RULES_JSON = [
    {
        "rule_id": "rule_gmt_effect_end",
        "field_name": "gmt_effect_end",
        "field_label": "结算账户名称",
        "rule_type": "cleaning",
        "priority": 1, "enabled": True,
        "config": {
            "cleaning_steps": [
                {"action": "fill_null", "source_field": "partner_name",
                 "condition": {"field": "gmt_effect_end", "operator": "is_null"}},
                {"action": "replace",
                 "condition": {"field": "partner_name", "operator": "eq", "value": "平安健康（检测）上海旗舰中心"},
                 "replacement": "上海平安好医创智门诊部有限公司"},
            ]
        },
        "depends_on": [],
        "description": "若账户名为空且合作方名称包含平安好医，则取合作方名称；指定值替换",
    },
    {
        "rule_id": "rule_rate_2",
        "field_name": "rate_2",
        "field_label": "适用税率",
        "rule_type": "mapping",
        "priority": 2, "enabled": True,
        "config": {
            "conditions": [
                {"id": "cg_001", "priority": 1, "logic": "AND",
                 "rows": [{"id": "cr_001", "field": "company_segment_code", "operator": "in", "value": ["930000", "840000"]}],
                 "result_type": "constant", "result_value": 0},
            ],
            "default_result": 0.06,
        },
        "depends_on": ["company_segment_code"],
        "description": "公司段值930000/840000为0，其他为0.06",
    },
    {
        "rule_id": "rule_if_reject",
        "field_name": "if_reject",
        "field_label": "是否剔除",
        "rule_type": "mapping",
        "priority": 3, "enabled": True,
        "config": {
            "conditions": [
                {"id": "cg_001", "priority": 1, "logic": "AND",
                 "rows": [{"id": "cr_001", "field": "prod_class", "operator": "contains", "value": "团体体检"}],
                 "result_type": "constant", "result_value": "不剔除"},
            ],
            "default_result": "剔除",
        },
        "depends_on": ["prod_class"],
        "description": "团体体检类标记不剔除，其他按映射表规则",
    },
    {
        "rule_id": "rule_prod_class",
        "field_name": "prod_class",
        "field_label": "产品分类",
        "rule_type": "mapping",
        "priority": 4, "enabled": True,
        "config": {
            "conditions": [
                {"id": "cg_001", "priority": 1, "logic": "AND",
                 "rows": [{"id": "cr_001", "field": "card_product_seg_name", "operator": "is_not_null"}],
                 "result_type": "field_value", "result_value": "card_product_seg_name"},
                {"id": "cg_002", "priority": 2, "logic": "AND",
                 "rows": [
                     {"id": "cr_002", "field": "card_name", "operator": "contains", "value": "团体体检"},
                     {"id": "cr_003", "field": "eorder_name", "operator": "contains", "value": "平安集团员工体检"},
                 ],
                 "result_type": "constant", "result_value": "集团体检"},
                {"id": "cg_003", "priority": 3, "logic": "AND",
                 "rows": [
                     {"id": "cr_004", "field": "fin_product", "operator": "eq", "value": "集团体检"},
                     {"id": "cr_005", "field": "card_name", "operator": "not_contains", "value": "团体体检"},
                 ],
                 "result_type": "constant", "result_value": "集团体检"},
                {"id": "cg_004", "priority": 4, "logic": "AND",
                 "rows": [{"id": "cr_006", "field": "card_name", "operator": "matches", "value": "团体体检|体检|套餐"}],
                 "result_type": "constant", "result_value": "团体体检"},
            ],
            "default_result": None,
        },
        "depends_on": ["card_product_seg_name"],
        "description": "4级优先级链：卡映射→特定卡片→财务产品→关键词→NULL",
    },
    {
        "rule_id": "rule_company_segment_code",
        "field_name": "company_segment_code",
        "field_label": "公司段值",
        "rule_type": "cleaning",
        "priority": 5, "enabled": True,
        "config": {
            "cleaning_steps": [
                {"action": "fill_null", "value": "972400"},
            ]
        },
        "depends_on": [],
        "description": "空值转换为972400",
    },
    {
        "rule_id": "rule_buyer_name",
        "field_name": "buyer_name",
        "field_label": "采购主体段值",
        "rule_type": "mapping",
        "priority": 6, "enabled": True,
        "config": {
            "conditions": [
                {"id": "cg_001", "priority": 1, "logic": "AND",
                 "rows": [{"id": "cr_001", "field": "buyer_name", "operator": "eq", "value": "宁波"}],
                 "result_type": "constant", "result_value": "971500"},
                {"id": "cg_002", "priority": 2, "logic": "AND",
                 "rows": [{"id": "cr_002", "field": "buyer_name", "operator": "eq", "value": "广东"}],
                 "result_type": "constant", "result_value": "970200"},
                {"id": "cg_003", "priority": 3, "logic": "AND",
                 "rows": [{"id": "cr_003", "field": "buyer_name", "operator": "eq", "value": "海南"}],
                 "result_type": "constant", "result_value": "972400"},
            ],
            "default_result": None,
        },
        "depends_on": [],
        "description": "采购名称映射到段值",
    },
    {
        "rule_id": "rule_upd_eorder_name",
        "field_name": "upd_eorder_name",
        "field_label": "企业单关联方",
        "rule_type": "mapping",
        "priority": 7, "enabled": True,
        "config": {
            "conditions": [
                {"id": "cg_001", "priority": 1, "logic": "AND",
                 "rows": [
                     {"id": "cr_001", "field": "eorder_name", "operator": "contains", "value": "盟宠"},
                     {"id": "cr_002", "field": "upd_eorder_name", "operator": "eq", "value": "平安健康"},
                 ],
                 "result_type": "constant", "result_value": "盟宠生态"},
            ],
            "default_result": None,
        },
        "depends_on": ["eorder_name"],
        "description": "复杂衍生：盟宠→盟宠生态（自身依赖通过两步计算处理）",
    },
    {
        "rule_id": "rule_product_segment_code",
        "field_name": "product_segment_code",
        "field_label": "产品段值",
        "rule_type": "lookup",
        "priority": 8, "enabled": True,
        "config": {
            "lookup_table_id": "lookup_fin_card",
            "lookup_key_field": "card_name",
            "lookup_value_field": "product_segment_name",
            "lookup_fallbacks": [
                {"condition": {"field": "prod_class", "operator": "eq", "value": "集团体检"}, "value": "P10011"},
                {"condition": {"field": "prod_class", "operator": "eq", "value": "团体体检"}, "value": "P10012"},
            ],
        },
        "depends_on": ["prod_class"],
        "description": "取��射表，兜底：集团体检→P10011，团体体检→P10012",
    },
    {
        "rule_id": "rule_is_spec_reject",
        "field_name": "is_spec_reject",
        "field_label": "是否特殊业务剔除",
        "rule_type": "mapping",
        "priority": 9, "enabled": True,
        "config": {
            "conditions": [
                {"id": "cg_001", "priority": 1, "logic": "AND",
                 "rows": [{"id": "cr_001", "field": "buyer_contract_id", "operator": "eq", "value": "CG-2025PAJKSH119487"}],
                 "result_type": "constant", "result_value": "是"},
            ],
            "default_result": None,
        },
        "depends_on": [],
        "description": "特定合同ID标记为是",
    },
    {
        "rule_id": "rule_sum_fin_ar",
        "field_name": "sum_fin_ar",
        "field_label": "应收账款金额",
        "rule_type": "computed",
        "priority": 10, "enabled": True,
        "config": {
            "formula_expression": (
                "IF(company_segment_code IN ('930000', '840000'), sum_fin_rev, ROUND(sum_fin_rev * (1 + rate_2), 2))"
            )
        },
        "depends_on": ["company_segment_code", "rate_2"],
        "description": "930000/840000取sum_fin_rev，否则sum_fin_rev*(1+rate_2)",
    },
    {
        "rule_id": "rule_ar_balance",
        "field_name": "ar_balance",
        "field_label": "AR余额",
        "rule_type": "computed",
        "priority": 11, "enabled": True,
        "config": {
            "formula_expression": (
                "IF(pay_amount > sum_fin_ar, COALESCE(pay_amount, 0) - sum_fin_ar, 0)"
            )
        },
        "depends_on": ["sum_fin_ar"],
        "description": "pay_amount > sum_fin_ar时取差值，否则0",
    },
]


def test_topological_sort():
    """测试依赖拓扑排序"""
    rules = [RuleParser.parse(r) for r in RULES_JSON]
    levels = topological_sort(rules)
    print(f"拓扑排序: {len(levels)} 层, 共 {len(rules)} 条规则")
    for i, level in enumerate(levels):
        print(f"  Level {i}: {[r.field_name for r in level]}")
    assert len(levels) >= 3, "应该有至少3层依赖"
    print("✅ 拓扑排序测试通过")


def test_mapping_rule():
    """测试条件映射规则"""
    rule = RuleParser.parse(RULES_JSON[1])  # rate_2
    df = pl.DataFrame({
        "company_segment_code": ["930000", "840000", "972400", "970200", None],
    })
    executor = RuleExecutor([rule])
    result, stats = executor.execute(df)
    expected = [0.0, 0.0, 0.06, 0.06, 0.06]
    actual = result["rate_2"].to_list()
    assert len(actual) == len(expected), f"行数不匹配: {len(actual)} vs {len(expected)}"
    for i, (a, e) in enumerate(zip(actual, expected)):
        assert a == e, f"rate_2[{i}] 映射失败: 期望 {e}, 实际 {a}"
    print(f"✅ rate_2 条件映射: {actual}")


def test_cleaning_rule():
    """测试数据清洗规则"""
    rule = RuleParser.parse(RULES_JSON[0])  # gmt_effect_end
    df = pl.DataFrame({
        "gmt_effect_end": [None, "平安健康（检测）上海旗舰中心", "正常账户"],
        "partner_name": ["上海好医", "平安健康（检测）上海旗舰中心", None],
    })
    executor = RuleExecutor([rule])
    result, stats = executor.execute(df)
    actual = result["gmt_effect_end"].to_list()
    # fill_null: 第一行 partner_name 有值 → 取 partner_name
    assert actual[0] == "上海好医", f"fill_null 失败: {actual[0]}"
    # replace: 第二行 partner_name 匹配 → 替换为新值
    assert actual[1] == "上海平安好医创智门诊部有限公司", f"replace 失败: {actual[1]}"
    # 第三行不匹配任何条件，保持原值
    assert actual[2] == "正常账户", f"不匹配行应保持原值: {actual[2]}"
    print(f"✅ gmt_effect_end 清洗: {actual}")


def test_computed_rule():
    """测试公式计算规则"""
    rules = [
        RuleParser.parse(RULES_JSON[1]),   # rate_2
        RuleParser.parse(RULES_JSON[9]),   # sum_fin_ar (depends on rate_2)
        RuleParser.parse(RULES_JSON[10]),  # ar_balance (depends on sum_fin_ar)
    ]
    df = pl.DataFrame({
        "company_segment_code": ["930000", "972400", "972400"],
        "sum_fin_rev": [1000.0, 2000.0, 3000.0],
        "pay_amount": [500.0, 2500.0, 2000.0],
    })
    executor = RuleExecutor(rules)
    result, stats = executor.execute(df)
    rate_2 = result["rate_2"].to_list()
    sum_fin_ar = result["sum_fin_ar"].to_list()
    ar_balance = result["ar_balance"].to_list()

    # rate_2: 930000→0, 其他→0.06
    assert rate_2[0] == 0.0, f"rate_2[0] 应为 0: {rate_2[0]}"
    assert rate_2[1] == 0.06, f"rate_2[1] 应为 0.06: {rate_2[1]}"
    assert rate_2[2] == 0.06, f"rate_2[2] 应为 0.06: {rate_2[2]}"

    # sum_fin_ar: 930000 取 sum_fin_rev 原值；其他 = rev * (1 + rate_2)
    assert sum_fin_ar[0] == 1000.0, f"sum_fin_ar[0] 应为 1000: {sum_fin_ar[0]}"
    assert sum_fin_ar[1] == 2120.0, f"sum_fin_ar[1] 应为 2000*1.06=2120: {sum_fin_ar[1]}"
    assert sum_fin_ar[2] == 3180.0, f"sum_fin_ar[2] 应为 3000*1.06=3180: {sum_fin_ar[2]}"

    # ar_balance: pay_amount > sum_fin_ar 时取差值，否则 0
    assert ar_balance[0] == 0, f"ar_balance[0] 应为 0 (500 < 1000): {ar_balance[0]}"
    assert ar_balance[1] == 380.0, f"ar_balance[1] 应为 2500-2120=380: {ar_balance[1]}"
    assert ar_balance[2] == 0, f"ar_balance[2] 应为 0 (2000 < 3180): {ar_balance[2]}"

    print(f"  rate_2: {rate_2}")
    print(f"  sum_fin_ar: {sum_fin_ar}")
    print(f"  ar_balance: {ar_balance}")
    print("✅ 公式计算链测试通过")


def test_full_pipeline():
    """完整流水线测试 — 模拟真实数据"""
    rules = [RuleParser.parse(r) for r in RULES_JSON]
    df = pl.DataFrame({
        "gmt_effect_end": [None, "正常账户", "测试"],
        "partner_name": ["上海好医", "无关", "平安健康（检测）上海旗舰中心"],
        "company_segment_code": ["930000", "972400", None],
        "buyer_name": ["宁波", "广东", "未知"],
        "card_product_seg_name": [None, "团体体检", None],
        "card_name": ["团体体检xxx", "某体检卡", "团体体检销管流转健管专用"],
        "eorder_name": ["平安集团员工体检-2025", "某企业单", "平安集团员工体检"],
        "fin_product": [None, "集团体检", None],
        "upd_eorder_name": ["平安健康", "其他", "平安健康"],
        "buyer_contract_id": ["CG-2025PAJKSH119487", "CG-OTHER", "CG-OTHER"],
        "sum_fin_rev": [1000.0, 2000.0, 3000.0],
        "pay_amount": [500.0, 2500.0, 3500.0],
    })

    executor = RuleExecutor(rules, lookup_tables={})
    result, stats = executor.execute(df)

    # ── 关键断言 ──
    # 1. company_segment_code: 清洗 fill_null(None→"972400")
    csc = result["company_segment_code"].to_list()
    assert csc[2] == "972400", f"company_segment_code fill_null 失败: {csc[2]}"

    # 2. rate_2: 930000→0, 其他→0.06
    r2 = result["rate_2"].to_list()
    assert r2[0] == 0.0, f"rate_2[0] 应为 0: {r2[0]}"
    assert r2[1] == 0.06, f"rate_2[1] 应为 0.06: {r2[1]}"

    # 3. prod_class: 第一行和第三行同时匹配 card_name+eorder_name → "集团体检"(cg_002)
    pc = result["prod_class"].to_list()
    assert pc[0] == "集团体检", f"prod_class[0] 匹配失败: {pc[0]}"
    assert pc[2] == "集团体检", f"prod_class[2] 匹配失败: {pc[2]}"
    # 第二行 card_product_seg_name 有值 → 直接取值(cg_001)
    assert pc[1] == "团体体检", f"prod_class[1] 应取 card_product_seg_name: {pc[1]}"

    # 4. if_reject: prod_class 含"团体体检"才不剔除；row0/row2 prod_class=集团体检 → "剔除"
    ir = result["if_reject"].to_list()
    assert ir[0] == "剔除", f"if_reject[0] 应为剔除(集团体检≠团体体检): {ir[0]}"
    assert ir[1] == "不剔除", f"if_reject[1] 应为不剔除(prod_class=团体体检): {ir[1]}"

    # 5. buyer_name: 宁波→971500, 广东→970200, 未知→None
    bn = result["buyer_name"].to_list()
    assert bn[0] == "971500", f"buyer_name[0] 映射失败: {bn[0]}"
    assert bn[1] == "970200", f"buyer_name[1] 映射失败: {bn[1]}"

    # 6. is_spec_reject: 合同 ID 匹配 → "是"
    isr = result["is_spec_reject"].to_list()
    assert isr[0] == "是", f"is_spec_reject[0] 应为是: {isr[0]}"

    # 7. sum_fin_ar: 930000 取原值 1000, 其他 = rev * 1.06
    sfa = result["sum_fin_ar"].to_list()
    assert sfa[0] == 1000.0, f"sum_fin_ar[0] 应为 1000: {sfa[0]}"
    assert sfa[1] == 2120.0, f"sum_fin_ar[1] 应为 2120: {sfa[1]}"

    print("\n=== 完整流水线结果 ===")
    for col in result.columns:
        if not col.startswith("_"):
            print(f"  {col}: {result[col].to_list()}")

    print("\n=== 执行统计 ===")
    for field, s in stats.to_dict().items():
        print(f"  {field}: matched={s['matched']}, defaulted={s['defaulted']}")

    print("\n✅ 完整流水线测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("BI 规则引擎 — 端到端测试")
    print("=" * 60)
    test_topological_sort()
    test_mapping_rule()
    test_cleaning_rule()
    test_computed_rule()
    test_full_pipeline()
    print("\n🎉 所有测试通过!")
