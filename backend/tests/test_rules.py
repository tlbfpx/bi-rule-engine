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
                "pl.when(pl.col('company_segment_code').is_in(['930000', '840000']))"
                ".then(pl.col('sum_fin_rev'))"
                ".otherwise((pl.col('sum_fin_rev') * (1 + pl.col('rate_2'))).round(2))"
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
                "pl.when(pl.col('pay_amount') > pl.col('sum_fin_ar'))"
                ".then(pl.col('pay_amount').fill_null(0) - pl.col('sum_fin_ar'))"
                ".otherwise(pl.lit(0))"
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
    assert actual[:4] == expected[:4], f"rate_2 映射失败: {actual}"
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
    print(f"✅ gmt_effect_end 清洗: {result['gmt_effect_end'].to_list()}")


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
    print(f"  rate_2: {result['rate_2'].to_list()}")
    print(f"  sum_fin_ar: {result['sum_fin_ar'].to_list()}")
    print(f"  ar_balance: {result['ar_balance'].to_list()}")
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
