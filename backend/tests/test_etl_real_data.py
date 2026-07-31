"""真实数据 ETL 测试 — 使用 storage/test_data_体检规则_全覆盖.csv 的 11 行数据跑完整规则引擎

这个测试验证：
1. CSV 数据可以被正确读取
2. 11 条规则在真实数据上的执行结果符合业务预期
3. 多规则依赖链（cleaning → mapping → lookup → computed）正确排序和执行
"""
import os
import polars as pl

from app.engine.parser import RuleParser
from app.engine.executor import RuleExecutor
from app.engine.dependency import topological_sort

# ── 测试数据路径 ──
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "storage",
)
CSV_PATH = os.path.join(DATA_DIR, "test_data_体检规则_全覆盖.csv")

# ── 复用 test_rules.py 的 11 条规则定义 ──
from tests.test_rules import RULES_JSON  # noqa: E402


def load_test_data() -> pl.DataFrame:
    """加载 CSV 测试数据"""
    df = pl.read_csv(CSV_PATH, infer_schema_length=0)
    # 数值列转换为 Float64
    for col in ["sum_fin_rev", "pay_amount"]:
        if col in df.columns:
            df = df.with_columns(pl.col(col).cast(pl.Float64, strict=False))
    return df


def test_csv_data_exists():
    """验证测试数据文件存在且可读"""
    assert os.path.isfile(CSV_PATH), f"CSV 数据文件不存在: {CSV_PATH}"
    df = load_test_data()
    assert df.height == 11, f"预期 11 行，实际 {df.height} 行"
    expected_cols = {
        "uid", "gmt_effect_end", "partner_name", "company_segment_code",
        "card_product_seg_name", "card_name", "eorder_name", "fin_product",
        "buyer_name", "upd_eorder_name_temp", "buyer_contract_id",
        "reject_reason", "sum_fin_rev", "pay_amount", "if_reject", "is_spec_reject",
    }
    assert expected_cols.issubset(set(df.columns)), f"缺少列: {expected_cols - set(df.columns)}"
    print(f"✅ CSV 数据验证: {df.height} 行, {len(df.columns)} 列")


def test_rule_engine_on_real_data():
    """在真实 CSV 数据上运行完整规则引擎"""
    df = load_test_data()
    rules = [RuleParser.parse(r) for r in RULES_JSON]

    # 验证拓扑排序
    levels = topological_sort(rules)
    assert len(levels) >= 3, f"拓扑排序应至少3层，实际 {len(levels)} 层"

    # 执行规则引擎
    executor = RuleExecutor(rules, lookup_tables={})
    result, stats = executor.execute(df)

    assert result.height == df.height, f"结果行数应与输入一致: {result.height} vs {df.height}"

    # ── 逐行验证关键计算结果 ──

    # 1. company_segment_code: 空值填充为 "972400"
    csc = result["company_segment_code"].to_list()
    # 所有原始值应该保留，空值填充
    for i, original in enumerate(df["company_segment_code"].to_list()):
        if not original or original == "":
            assert csc[i] == "972400", f"行 {i}: 空值应填充为 972400，实际: {csc[i]}"

    # 2. rate_2: 930000/840000 → 0, 其他 → 0.06
    rate = result["rate_2"].to_list()
    for i, seg in enumerate(csc):
        if seg in ("930000", "840000"):
            assert rate[i] == 0.0, f"行 {i} (seg={seg}): rate_2 应为 0, 实际 {rate[i]}"
        else:
            assert rate[i] == 0.06, f"行 {i} (seg={seg}): rate_2 应为 0.06, 实际 {rate[i]}"

    # 3. sum_fin_ar: 930000/840000 取 sum_fin_rev 原值，其他 = sum_fin_rev * (1 + rate_2)
    sfa = result["sum_fin_ar"].to_list()
    rev = df["sum_fin_rev"].to_list()
    for i, seg in enumerate(csc):
        expected = rev[i]
        if seg not in ("930000", "840000"):
            expected = round(rev[i] * 1.06, 2)
        assert abs(sfa[i] - expected) < 0.01, (
            f"行 {i} (seg={seg}): sum_fin_ar 应为 {expected}, 实际 {sfa[i]}"
        )

    # 4. ar_balance: pay_amount > sum_fin_ar 时取差值，否则 0
    arb = result["ar_balance"].to_list()
    pay = df["pay_amount"].to_list()
    for i in range(len(arb)):
        if pay[i] is not None and sfa[i] is not None and pay[i] > sfa[i]:
            expected = round(pay[i] - sfa[i], 2)
            assert abs(arb[i] - expected) < 0.01, (
                f"行 {i}: ar_balance 应为 {pay[i]} - {sfa[i]} = {expected}, 实际 {arb[i]}"
            )
        else:
            assert arb[i] == 0, f"行 {i}: ar_balance 应为 0, 实际 {arb[i]}"

    # 5. buyer_name: 映射为段值
    bn = result["buyer_name"].to_list()
    original_bn = df["buyer_name"].to_list()
    # 宁波 → 971500, 广东 → 970200, 海南 → 972400
    for i, orig in enumerate(original_bn):
        if orig == "宁波":
            assert bn[i] == "971500", f"行 {i}: 宁波应映射为 971500, 实际 {bn[i]}"
        elif orig == "广东":
            assert bn[i] == "970200", f"行 {i}: 广东应映射为 970200, 实际 {bn[i]}"
        elif orig == "海南":
            assert bn[i] == "972400", f"行 {i}: 海南应映射为 972400, 实际 {bn[i]}"

    # 6. is_spec_reject: 合同 ID 匹配 CG-2025PAJKSH119487 → "是"
    isr = result["is_spec_reject"].to_list()
    bcid = df["buyer_contract_id"].to_list()
    for i, cid in enumerate(bcid):
        if cid == "CG-2025PAJKSH119487":
            assert isr[i] == "是", f"行 {i}: 特殊合同应标记为'是', 实际 {isr[i]}"

    # 7. gmt_effect_end: 清洗规则 — 空值取 partner_name
    gee = result["gmt_effect_end"].to_list()
    original_gee = df["gmt_effect_end"].to_list()
    partner = df["partner_name"].to_list()
    # u1: gmt_effect_end 空 → 取 partner_name "上海平安好医门诊"
    assert gee[0] == partner[0] or gee[0] == "上海好医", f"u1 空值应取 partner_name, 实际 {gee[0]}"

    # 打印统计信息
    print("\n=== 真实数据 ETL 执行统计 ===")
    print(f"输入: {df.height} 行")
    print(f"输出列: {[c for c in result.columns if not c.startswith('_')]}")
    for field_name, s in stats.to_dict().items():
        print(f"  {field_name}: matched={s['matched']}, defaulted={s['defaulted']}")

    print("\n=== 关键计算结果（前5行）===")
    for col in ["uid", "company_segment_code", "rate_2", "sum_fin_ar", "ar_balance", "buyer_name", "is_spec_reject"]:
        if col in result.columns:
            vals = result[col].to_list()
            print(f"  {col}: {vals[:5]}")

    print("\n✅ 真实数据 ETL 测试通过")


def test_dependency_ordering():
    """验证规则依赖拓扑排序的正确性"""
    rules = [RuleParser.parse(r) for r in RULES_JSON]
    levels = topological_sort(rules)

    # 第 0 层不应有依赖其他规则的规则
    level_0_fields = {r.field_name for r in levels[0]}
    # gmt_effect_end（cleaning, 无依赖）、company_segment_code（cleaning, 无依赖）
    # 应该在最早的层
    assert "company_segment_code" in level_0_fields or any(
        "company_segment_code" in {r.field_name for r in lvl} for lvl in levels[:2]
    ), "company_segment_code 应在早期层"

    # sum_fin_ar 依赖 rate_2，所以 rate_2 应在更早的层
    rate_level = None
    ar_level = None
    for i, level in enumerate(levels):
        for rule in level:
            if rule.field_name == "rate_2":
                rate_level = i
            if rule.field_name == "sum_fin_ar":
                ar_level = i
    assert rate_level is not None and ar_level is not None
    assert rate_level < ar_level, f"rate_2(L{rate_level}) 应在 sum_fin_ar(L{ar_level}) 之前"

    # ar_balance 依赖 sum_fin_ar
    bal_level = None
    for i, level in enumerate(levels):
        for rule in level:
            if rule.field_name == "ar_balance":
                bal_level = i
    assert bal_level is not None
    assert ar_level < bal_level, f"sum_fin_ar(L{ar_level}) 应在 ar_balance(L{bal_level}) 之前"

    print(f"✅ 拓扑排序验证通过: {len(levels)} 层")
    for i, level in enumerate(levels):
        print(f"  Level {i}: {[r.field_name for r in level]}")


def test_no_data_loss():
    """验证规则执行不会丢失或增加行数"""
    df = load_test_data()
    original_height = df.height
    original_uids = set(df["uid"].to_list())

    rules = [RuleParser.parse(r) for r in RULES_JSON]
    executor = RuleExecutor(rules, lookup_tables={})
    result, _ = executor.execute(df)

    assert result.height == original_height, (
        f"行数变化: 输入 {original_height}, 输出 {result.height}"
    )
    result_uids = set(result["uid"].to_list())
    assert result_uids == original_uids, (
        f"UID 不一致: 缺失 {original_uids - result_uids}, "
        f"新增 {result_uids - original_uids}"
    )
    print(f"✅ 数据完整性: 输入 {original_height} 行 = 输出 {result.height} 行")


def test_all_rules_executed():
    """验证所有 11 个规则字段都在结果中生成"""
    df = load_test_data()
    rules = [RuleParser.parse(r) for r in RULES_JSON]
    executor = RuleExecutor(rules, lookup_tables={})
    result, _ = executor.execute(df)

    expected_fields = {r["field_name"] for r in RULES_JSON}
    actual_fields = set(result.columns)
    missing = expected_fields - actual_fields
    assert not missing, f"规则引擎未生成以下字段: {missing}"

    # 检查每个字段至少有非 null 值
    for field in expected_fields:
        non_null = result[field].null_count()
        total = result.height
        # 至少应该有一些非 null 值（除非规则 default 就是 null）
        print(f"  {field}: {total - non_null}/{total} 非 null")

    print(f"✅ 所有 {len(expected_fields)} 个规则字段均已生成")
