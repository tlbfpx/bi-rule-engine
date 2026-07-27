"""
生成「体检映射规则」全覆盖测试数据，并校验分支覆盖率。

输出：
  - storage/test_data_体检规则_全覆盖.xlsx  （上传执行用）
  - storage/test_data_体检规则_全覆盖.csv
  - 控制台打印每条规则每个分支的命中数，断言可达分支 100% 覆盖

设计：11 行数据，每行同时命中多个正交规则的分支，合计覆盖全部可达分支。
不可达分支（流水线依赖所致）单独标注，例如：
  - rate_2.default：company_segment_code 已被 R5 清洗填空，rate_2 永远不会看到 null
"""
import os
import sys
import requests
import polars as pl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)).replace('/scripts', '')) if False else '.')
from app.engine.parser import RuleParser
from app.engine.executor import RuleExecutor

BASE = "http://localhost:8000/api/v1"
OUT_DIR = "/Users/muxi/workspace/unipost/bi-rule-engine/storage"

# ───────────────────────── 测试数据（11 行） ─────────────────────────
# 字段说明见每行注释；NA = 该行不关心此字段对其他规则的影响（已确认无副作用）
ROWS = [
    # R1: prod_class.g1 | rate_2.g1(930000) | sum_fin_ar.branch1 | ar_balance.pay>ar
    #     | gmt.g1 | buyer.宁波 | upd.盟宠 | is_spec.default | if_reject.default
    dict(uid="u1", gmt_effect_end=None, partner_name="上海平安好医门诊",
         company_segment_code="930000", card_product_seg_name="金卡产品段",
         card_name="某卡", eorder_name="盟宠科技订单", fin_product="其他",
         buyer_contract_name="宁波分公司", buyer_name="原采购1",
         upd_eorder_name_temp="平安健康", buyer_contract_id="CG-OTHER",
         reject_reason="重复", sum_fin_rev=1000.0, pay_amount=1500.0,
         if_reject="剔除", is_spec_reject="否"),

    # R2: prod_class.g2(集团) | rate_2.g1(840000) | sum_fin_ar.branch1 | ar_balance.pay<ar
    #     | gmt.g2 | buyer.广东 | upd.else | is_spec.g1(match) | if_reject.g2
    dict(uid="u2", gmt_effect_end="原账户", partner_name="平安健康（检测）上海旗舰中心",
         company_segment_code="840000", card_product_seg_name=None,
         card_name="团体体检销管流转健管专用", eorder_name="某平安集团员工体检单",
         fin_product="其他", buyer_contract_name="广东支公司", buyer_name="原采购2",
         upd_eorder_name_temp="某关联方", buyer_contract_id="CG-2025PAJKSH119487",
         reject_reason=None, sum_fin_rev=2000.0, pay_amount=1000.0,
         if_reject="剔除", is_spec_reject="否"),

    # R3: prod_class.g3(集团) | rate_2.g2 | sum_fin_ar.branch2 | ar_balance.pay<ar
    #     | gmt.default | buyer.海南互联网 | upd.好医(SPLIT) | if_reject.default(reject_reason非空)
    dict(uid="u3", gmt_effect_end="正常账户", partner_name="无关合作方",
         company_segment_code="972400", card_product_seg_name=None,
         card_name="普通卡片", fin_product="集团体检", eorder_name="好医-a-b-c-d-e-f",
         buyer_contract_name="海南互联网公司", buyer_name="原采购3",
         upd_eorder_name_temp="平安健康", buyer_contract_id="CG-X",
         reject_reason="原因A", sum_fin_rev=3000.0, pay_amount=3000.0,
         if_reject="剔除", is_spec_reject="否"),

    # R4: prod_class.g4(团体) | rate_2.g2 | sum_fin_ar.branch2 | ar_balance.pay<ar
    #     | gmt.default | buyer.海南 | upd.else | if_reject.g1
    dict(uid="u4", gmt_effect_end="账户D", partner_name="无关",
         company_segment_code="970200", card_product_seg_name=None,
         card_name="团体体检套餐", eorder_name="普通企业单号", fin_product="其他",
         buyer_contract_name="海南分公司", buyer_name="原采购4",
         upd_eorder_name_temp="关联D", buyer_contract_id="CG-Y",
         reject_reason=None, sum_fin_rev=500.0, pay_amount=100.0,
         if_reject="剔除", is_spec_reject="否"),

    # R5: prod_class.g5(团体) | company_segment_code.fill(null→972400) | sum_fin_ar.branch2
    #     | ar_balance.pay>ar | buyer.湖北 | upd.else | if_reject.g1
    dict(uid="u5", gmt_effect_end="账户E", partner_name="无关",
         company_segment_code=None, card_product_seg_name=None,
         card_name="特殊卡", fin_product="团体体检专项", eorder_name="普通单",
         buyer_contract_name="湖北办", buyer_name="原采购5",
         upd_eorder_name_temp="关联E", buyer_contract_id="CG-Z",
         reject_reason=None, sum_fin_rev=200.0, pay_amount=999.0,
         if_reject="剔除", is_spec_reject="否"),

    # R6: prod_class.default(其他) | rate_2.g2 | sum_fin_ar.branch2 | buyer.陕西
    #     | upd.else | if_reject.default
    dict(uid="u6", gmt_effect_end="账户F", partner_name="无关",
         company_segment_code="970300", card_product_seg_name=None,
         card_name="杂项卡", fin_product="其他业务", eorder_name="普通",
         buyer_contract_name="陕西办", buyer_name="原采购6",
         upd_eorder_name_temp="关联F", buyer_contract_id="CG-W",
         reject_reason=None, sum_fin_rev=100.0, pay_amount=50.0,
         if_reject="剔除", is_spec_reject="否"),

    # R7: buyer.青岛 (其余 neutral/default)
    dict(uid="u7", gmt_effect_end="账户G", partner_name="无关",
         company_segment_code="970100", card_product_seg_name=None,
         card_name="杂项卡", fin_product="其他业务", eorder_name="普通",
         buyer_contract_name="青岛站", buyer_name="原采购7",
         upd_eorder_name_temp="关联G", buyer_contract_id="CG-QD",
         reject_reason=None, sum_fin_rev=100.0, pay_amount=50.0,
         if_reject="剔除", is_spec_reject="否"),

    # R8: buyer.上海
    dict(uid="u8", gmt_effect_end="账户H", partner_name="无关",
         company_segment_code="970100", card_product_seg_name=None,
         card_name="杂项卡", fin_product="其他业务", eorder_name="普通",
         buyer_contract_name="上海总站", buyer_name="原采购8",
         upd_eorder_name_temp="关联H", buyer_contract_id="CG-SH",
         reject_reason=None, sum_fin_rev=100.0, pay_amount=50.0,
         if_reject="剔除", is_spec_reject="否"),

    # R9: buyer.北京
    dict(uid="u9", gmt_effect_end="账户I", partner_name="无关",
         company_segment_code="970100", card_product_seg_name=None,
         card_name="杂项卡", fin_product="其他业务", eorder_name="普通",
         buyer_contract_name="北京办", buyer_name="原采购9",
         upd_eorder_name_temp="关联I", buyer_contract_id="CG-BJ",
         reject_reason=None, sum_fin_rev=100.0, pay_amount=50.0,
         if_reject="剔除", is_spec_reject="否"),

    # R10: buyer.总公司
    dict(uid="u10", gmt_effect_end="账户J", partner_name="无关",
         company_segment_code="970100", card_product_seg_name=None,
         card_name="杂项卡", fin_product="其他业务", eorder_name="普通",
         buyer_contract_name="总公司直营", buyer_name="原采购10",
         upd_eorder_name_temp="关联J", buyer_contract_id="CG-ZG",
         reject_reason=None, sum_fin_rev=100.0, pay_amount=50.0,
         if_reject="剔除", is_spec_reject="否"),

    # R11: buyer.default(无关键词)
    dict(uid="u11", gmt_effect_end="账户K", partner_name="无关",
         company_segment_code="970100", card_product_seg_name=None,
         card_name="杂项卡", fin_product="其他业务", eorder_name="普通",
         buyer_contract_name="海外机构", buyer_name="原海外",
         upd_eorder_name_temp="关联K", buyer_contract_id="CG-HW",
         reject_reason=None, sum_fin_rev=100.0, pay_amount=50.0,
         if_reject="剔除", is_spec_reject="否"),
]


def build_df():
    return pl.DataFrame(ROWS)


def load_rules():
    """从 API 拉取全部启用规则（与上传执行一致：跑所有 enabled 规则）。"""
    items = requests.get(f"{BASE}/rules", params={"page_size": 50}).json()["items"]
    return items, [RuleParser.parse(r) for r in items]


def coverage_report(df_input, rule_dicts, rule_configs):
    """运行流水线，逐规则统计分支命中数，返回 (输出df, 覆盖明细列表, 是否全覆盖)。

    关键：mapping 规则的分支判定基于"该规则执行前"的 df 快照（因为部分规则的条件
    读取自己的目标字段，如 gmt_effect_end，执行后已被改写）。通过回放流水线实现。
    """
    from app.engine.dependency import topological_sort

    executor = RuleExecutor(rule_configs, lookup_tables={})
    levels = topological_sort(executor.rules)

    # 回放流水线，抓取每个 mapping 规则执行前的快照
    df = df_input.with_columns(
        pl.lit(False).alias("_error_flag"),
        pl.lit("").alias("_error_msg"),
    )
    snapshots = {}  # field_name -> 执行前 df
    for level in levels:
        for rule in level:
            if rule.rule_type == "mapping":
                snapshots[rule.field_name] = df
            df = executor._execute_rule(df, rule)
    out = df

    by_field = {rc.field_name: rc for rc in rule_configs}
    lines = []
    all_ok = True

    def emit(rule_name, branch, count, reachable=True, note=""):
        nonlocal all_ok
        flag = "✅" if count > 0 else ("⛔不可达" if not reachable else "❌未覆盖")
        if count == 0 and reachable:
            all_ok = False
        lines.append(f"  {flag} {rule_name:<22} {branch:<28} 命中={count}  {note}")

    # ── mapping 规则：用执行前快照判定首个命中条件组 ──
    for fname in ["gmt_effect_end", "rate_2", "if_reject", "prod_class", "buyer_name", "is_spec_reject"]:
        rc = by_field[fname]
        snap = snapshots[fname]
        groups = sorted(rc.conditions, key=lambda c: c.priority)
        not_matched = pl.Series("_nm", [True] * len(snap))
        group_hit = {}
        for g in groups:
            mask = executor._evaluate_condition_group(snap, g).fill_null(False) & not_matched
            group_hit[g.priority] = int(mask.sum())
            not_matched = not_matched & ~mask
        default_hit = int(not_matched.sum())
        for g in groups:
            emit(fname, f"组{g.priority}({g.result_value})", group_hit[g.priority])
        note = ""
        reachable = True
        if fname == "rate_2":
            note = "company_segment_code 已被清洗填空，default 不可达"; reachable = False
        emit(fname, "default", default_hit, reachable=reachable, note=note)

    # ── cleaning: company_segment_code（按输入 null 统计）──
    in_col = df_input["company_segment_code"]
    fill_hit = int(in_col.null_count())
    keep_hit = int(len(df_input) - fill_hit)
    emit("company_segment_code", "fill_null(null→972400)", fill_hit)
    emit("company_segment_code", "保留原值", keep_hit)

    # ── lookup: product_segment_code（按 prod_class 兜底分支）──
    pc = out["prod_class"]
    emit("product_segment_code", "fb1(集团体检→P10011)", int((pc == "集团体检").sum()))
    emit("product_segment_code", "fb2(团体体检→P10012)", int((pc == "团体体检").sum()))
    emit("product_segment_code", "无兜底(其他→null)", int(((pc != "集团体检") & (pc != "团体体检")).sum()))

    # ── computed: sum_fin_ar ──
    csc = out["company_segment_code"].cast(pl.Utf8)
    in_list = int(csc.is_in(["930000", "840000"]).sum())
    emit("sum_fin_ar", "branch1(in list→sum_fin_rev)", in_list)
    emit("sum_fin_ar", "branch2(×1.06 round)", len(out) - in_list)

    # ── computed: ar_balance ──
    pay = out["pay_amount"]
    sfa = out["sum_fin_ar"]
    gt = int((pay > sfa).sum())
    emit("ar_balance", "pay>ar→差额", gt)
    emit("ar_balance", "else→0", len(out) - gt)

    # ── computed: upd_eorder_name（公式三分支）──
    eord = out["eorder_name"].cast(pl.Utf8).fill_null("")
    temp = out["upd_eorder_name_temp"].cast(pl.Utf8).fill_null("")
    m1 = eord.str.contains("盟宠") & (temp == "平安健康")
    m2 = (~m1) & eord.str.contains("好医") & (temp == "平安健康")
    emit("upd_eorder_name", "盟宠&temp平安健康→盟宠生态", int(m1.sum()))
    emit("upd_eorder_name", "好医&temp平安健康→SPLIT", int(m2.sum()))
    emit("upd_eorder_name", "else→temp", int((~m1 & ~m2).sum()))

    return out, None, lines, all_ok


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    df = build_df()

    # 写文件
    xlsx = os.path.join(OUT_DIR, "test_data_体检规则_全覆盖.xlsx")
    csv = os.path.join(OUT_DIR, "test_data_体检规则_全覆盖.csv")
    df.write_excel(xlsx)
    df.write_csv(csv)
    print(f"已生成测试数据：{xlsx}（{len(df)} 行 × {len(df.columns)} 列）")
    print(f"                  {csv}\n")

    rule_dicts, rule_configs = load_rules()
    out, stats, lines, all_ok = coverage_report(df, rule_dicts, rule_configs)

    print("=" * 72)
    print("分支覆盖率报告（11 条体检规则）")
    print("=" * 72)
    for ln in lines:
        print(ln)
    print("=" * 72)
    print(f"结论：{'✅ 所有可达分支已 100% 覆盖' if all_ok else '❌ 存在未覆盖的可达分支'}")
    return all_ok


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
