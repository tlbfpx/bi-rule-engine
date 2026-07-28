"""条件编译器 (compiler) 表驱动测试：全操作符 + 条件组 AND/OR。"""
import pytest
from app.engine.parser import ConditionRow, ConditionGroup
from app.engine.compiler import compile_condition, evaluate_group


@pytest.mark.parametrize(
    "op,value,input,expected",
    [
        # 相等 / 不等
        ("eq", "x", "x", True),
        ("eq", "x", "y", False),
        ("eq", "x", None, False),
        ("neq", "x", "y", True),
        ("neq", "x", None, True),
        # 包含
        ("contains", "ell", "hello", True),
        ("contains", "ell", "world", False),
        ("not_contains", "ell", "world", True),
        ("not_contains", "ell", "hello", False),
        # 正则 / 前后缀
        ("matches", "a|b", "apple", True),
        ("matches", "^z", "zzz", True),
        ("matches", "^z", "az", False),
        ("starts_with", "he", "hello", True),
        ("starts_with", "he", "xhello", False),
        ("ends_with", "lo", "hello", True),
        ("ends_with", "lo", "hellox", False),
        # 列表 / 范围
        ("in", ["a", "b"], "a", True),
        ("in", ["a", "b"], "c", False),
        ("between", [1, 10], 5, True),
        ("between", [1, 10], 11, False),
        # 数值比较
        ("gt", 5, 10, True),
        ("gt", 5, 5, False),
        ("gte", 5, 5, True),
        ("lt", 5, 1, True),
        ("lte", 5, 5, True),
        # 空值
        ("is_null", None, None, True),
        ("is_null", None, "", True),
        ("is_null", None, "x", False),
        ("is_not_null", None, "x", True),
        ("is_not_null", None, "", False),
        ("is_not_null", None, None, False),
    ],
)
def test_compile_condition(op, value, input, expected):
    row = ConditionRow(field="f", operator=op, value=value)
    assert compile_condition(row)(input) is expected


def test_compile_condition_unknown_operator_raises():
    with pytest.raises(ValueError, match="Unknown operator"):
        compile_condition(ConditionRow(field="f", operator="bogus", value=1))


def _group(logic, rows):
    return ConditionGroup(
        id="g", priority=1, logic=logic,
        rows=[ConditionRow(field=f, operator="eq", value=v) for f, v in rows],
    )


def test_evaluate_group_and():
    g = _group("AND", [("a", 1), ("b", 2)])
    assert evaluate_group(g, {"a": 1, "b": 2}) is True
    assert evaluate_group(g, {"a": 1, "b": 9}) is False


def test_evaluate_group_or():
    g = _group("OR", [("a", 1), ("b", 2)])
    assert evaluate_group(g, {"a": 1, "b": 9}) is True
    assert evaluate_group(g, {"a": 9, "b": 9}) is False
