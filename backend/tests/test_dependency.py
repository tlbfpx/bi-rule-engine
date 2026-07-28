"""依赖分析 (dependency) 测试：拓扑分层 + 环检测。"""
import pytest
from app.engine.parser import RuleConfig
from app.engine.dependency import topological_sort, CyclicDependencyError


def _rc(field, depends_on=None) -> RuleConfig:
    return RuleConfig(
        rule_id=f"r_{field}", field_name=field, field_label="",
        rule_type="computed", priority=0, enabled=True,
        depends_on=depends_on or [],
    )


def test_topo_layers_and_order():
    rules = [_rc("a"), _rc("b", ["a"]), _rc("c", ["b"]), _rc("d")]  # d 独立
    levels = topological_sort(rules)

    flat = [r.field_name for lvl in levels for r in lvl]
    assert set(flat) == {"a", "b", "c", "d"}
    # a → b → c 顺序
    assert flat.index("a") < flat.index("b") < flat.index("c")
    # a、d 同在 level 0
    level0 = {r.field_name for r in levels[0]}
    assert {"a", "d"} <= level0
    # b 在 level 1
    assert levels[1][0].field_name == "b"


def test_topo_parallel_same_level():
    rules = [_rc("a"), _rc("b"), _rc("c", ["a", "b"])]
    levels = topological_sort(rules)
    level0 = {r.field_name for r in levels[0]}
    assert level0 == {"a", "b"}
    assert levels[1][0].field_name == "c"


def test_topo_cycle_raises():
    rules = [_rc("a", ["b"]), _rc("b", ["a"])]
    with pytest.raises(CyclicDependencyError) as exc:
        topological_sort(rules)
    assert set(exc.value.fields) == {"a", "b"}


def test_depends_on_non_rule_ignored():
    """depends_on 引用源列（非规则字段）应被忽略，不影响分层。"""
    rules = [_rc("a", ["source_col"]), _rc("b")]
    levels = topological_sort(rules)
    level0 = {r.field_name for r in levels[0]}
    assert {"a", "b"} <= level0  # 都在 level 0


def test_empty_rules():
    assert topological_sort([]) == []
