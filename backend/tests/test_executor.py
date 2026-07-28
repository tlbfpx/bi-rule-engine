"""规则执行器 (executor) 测试：lookup、keep_original 默认值、停用规则、统计。

注：mapping/cleaning/computed 的基础场景已由 test_rules.py 覆盖；这里补齐盲区。
"""
import polars as pl
from app.engine.parser import RuleParser
from app.engine.executor import RuleExecutor


def _parse(**kw) -> object:
    base = dict(field_name="t", rule_type="mapping", priority=1, enabled=True, config={}, depends_on=[])
    base.update(kw)
    return RuleParser.parse(base)


def test_lookup_with_fallback():
    rc = _parse(
        field_name="seg", rule_type="lookup",
        config={
            "lookup_table_id": "lt1",
            "lookup_key_field": "card",
            "lookup_value_field": "seg",
            "lookup_fallbacks": [
                {"condition": {"field": "cls", "operator": "eq", "value": "A"}, "value": "FB_A"},
            ],
        },
        depends_on=[],
    )
    df = pl.DataFrame({"card": ["k1", "k2", "k3"], "cls": ["X", "A", "X"]})
    out, _ = RuleExecutor([rc], lookup_tables={"lt1": {"k1": "SEG1"}}).execute(df)
    # k1 命中映射表 → SEG1；k2 未命中且 cls=A → 兜底 FB_A；k3 → null
    assert out["seg"].to_list() == ["SEG1", "FB_A", None]


def test_mapping_default_keep_original():
    rc = _parse(
        field_name="t", rule_type="mapping",
        config={
            "conditions": [
                {"id": "g1", "priority": 1, "logic": "AND",
                 "rows": [{"id": "c1", "field": "flag", "operator": "eq", "value": "Y"}],
                 "result_type": "constant", "result_value": "MATCHED"},
            ],
            "default_result": "keep_original",
        },
        depends_on=[],
    )
    df = pl.DataFrame({"t": ["orig1", "orig2"], "flag": ["Y", "N"]})
    out, _ = RuleExecutor([rc]).execute(df)
    # row0 命中 → MATCHED；row1 未命中 → 保持原值 orig2
    assert out["t"].to_list() == ["MATCHED", "orig2"]


def test_mapping_default_literal():
    rc = _parse(
        field_name="t", rule_type="mapping",
        config={
            "conditions": [
                {"id": "g1", "priority": 1, "logic": "AND",
                 "rows": [{"id": "c1", "field": "flag", "operator": "eq", "value": "Y"}],
                 "result_type": "constant", "result_value": "MATCHED"},
            ],
            "default_result": "LIT_DEFAULT",
        },
        depends_on=[],
    )
    df = pl.DataFrame({"t": ["orig1", "orig2"], "flag": ["Y", "N"]})
    out, _ = RuleExecutor([rc]).execute(df)
    assert out["t"].to_list() == ["MATCHED", "LIT_DEFAULT"]


def test_disabled_rules_are_skipped():
    enabled = _parse(field_name="a", rule_type="mapping",
                     config={"conditions": [], "default_result": "FROM_A"})
    disabled = RuleParser.parse({
        "field_name": "b", "rule_type": "mapping", "priority": 2, "enabled": False,
        "config": {"conditions": [], "default_result": "FROM_B"}, "depends_on": [],
    })
    df = pl.DataFrame({"x": [1]})
    out, _ = RuleExecutor([enabled, disabled]).execute(df)
    # a 启用 → 写入；b 停用 → 不执行，列不存在
    assert "a" in out.columns
    assert "b" not in out.columns


def test_stats_recorded_per_field():
    rc = _parse(
        field_name="t", rule_type="mapping",
        config={
            "conditions": [
                {"id": "g1", "priority": 1, "logic": "AND",
                 "rows": [{"id": "c1", "field": "flag", "operator": "eq", "value": "Y"}],
                 "result_type": "constant", "result_value": "M"},
            ],
            "default_result": "D",
        },
        depends_on=[],
    )
    df = pl.DataFrame({"t": ["o1", "o2", "o3"], "flag": ["Y", "N", "Y"]})
    _, stats = RuleExecutor([rc]).execute(df)
    s = stats.to_dict()["t"]
    assert s["matched"] == 2  # row0, row2
    assert s["defaulted"] == 1  # row1
    assert s["errors"] == 0


def test_empty_rules_returns_input():
    df = pl.DataFrame({"x": [1, 2]})
    out, stats = RuleExecutor([]).execute(df)
    # 无启用规则 → 原样返回（不附加 _error_* 列）
    assert out.columns == ["x"]
    assert stats.to_dict() == {}
