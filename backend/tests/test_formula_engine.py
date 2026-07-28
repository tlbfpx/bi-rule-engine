"""公式引擎 (formula_engine) 表驱动测试。

覆盖：IF/COALESCE/ROUND/算术、字符串函数、IS NULL / IN，
以及 AND/OR 与比较运算符 (`=`/`>`/`<`...) 混用时的【优先级回归】。
"""
import polars as pl
import pytest
from app.engine.formula_engine import evaluate_formula, compile_formula


# ─── 基础：IF + 算术 + COALESCE ───────────────────────────────

def test_if_gt_with_arithmetic():
    df = pl.DataFrame({"pay_amount": [1000.0, 500.0, 200.0], "sum_fin_ar": [800.0, 600.0, 100.0]})
    f = "IF(pay_amount > sum_fin_ar, pay_amount - sum_fin_ar, 0)"
    assert evaluate_formula(df, f).to_list() == [200.0, 0.0, 100.0]


def test_coalesce_fills_null():
    df = pl.DataFrame({"a": [1.0, None, 3.0], "b": [10.0, 20.0, None]})
    # COALESCE(a, b) → a 非空取 a，否则 b
    assert evaluate_formula(df, "COALESCE(a, b)").to_list() == [1.0, 20.0, 3.0]


def test_round():
    df = pl.DataFrame({"x": [1.234, 2.5, 3.456]})
    assert evaluate_formula(df, "ROUND(x, 2)").to_list() == [1.23, 2.5, 3.46]


def test_round_literal_value():
    df = pl.DataFrame({"rev": [1000.0, 2000.0]})
    # ROUND(rev * 1.06, 2)
    assert evaluate_formula(df, "ROUND(rev * 1.06, 2)").to_list() == [1060.0, 2120.0]


# ─── 字符串函数 ───────────────────────────────────────────────

def test_split_takes_nth_part():
    df = pl.DataFrame({"s": ["a-b-c-d-e-f", "1-2-3-4-5-6"]})
    # SPLIT 第 6 段（1-indexed）；6 段字符串的第 6 段
    assert evaluate_formula(df, "SPLIT(s, '-', 6)").to_list() == ["f", "6"]


def test_contains_upper():
    df = pl.DataFrame({"s": ["hello", "WORLD"]})
    assert evaluate_formula(df, "CONTAINS(s, 'ell')").to_list() == [True, False]
    assert evaluate_formula(df, "UPPER(s)").to_list() == ["HELLO", "WORLD"]


# ─── IS NULL / IN ─────────────────────────────────────────────

def test_is_null_and_is_not_null():
    df = pl.DataFrame({"s": ["a", None, "c"]})
    assert evaluate_formula(df, "s IS NULL").to_list() == [False, True, False]
    assert evaluate_formula(df, "s IS NOT NULL").to_list() == [True, False, True]


def test_in_list():
    df = pl.DataFrame({"code": ["930000", "840000", "972400"]})
    assert evaluate_formula(df, "code IN ('930000', '840000')").to_list() == [True, True, False]


# ─── 优先级回归（核心 bug）─────────────────────────────────────
# DSL 把 AND/OR→&/|、=→==，但 Python 里 & 优先级高于 ==，
# 故 `A AND B = C` 会被解析成 `(A & B) == C`（bitand str 报错或语义错误）。

def test_and_with_equality_no_parens():
    """CONTAINS(...) AND field = 'x' 必须正确地先求等值、再 AND。"""
    df = pl.DataFrame({
        "eorder_name": ["盟宠-x", "好医-x", "z"],
        "upd": ["平安健康", "平安健康", "其他"],
    })
    f = "CONTAINS(eorder_name, '盟宠') AND upd = '平安健康'"
    assert evaluate_formula(df, f).to_list() == [True, False, False]


def test_or_with_equality_no_parens():
    df = pl.DataFrame({"x": [1, 2, 3], "y": [9, 9, 3]})
    f = "x = 1 OR y = 3"
    assert evaluate_formula(df, f).to_list() == [True, False, True]


def test_if_nested_and_with_equality():
    """IF 参数内的 `x = 1 AND y = 2` 同样要正确分组。"""
    df = pl.DataFrame({"x": [1, 1, 2], "y": [2, 3, 2]})
    f = "IF(x = 1 AND y = 2, 'match', 'no')"
    assert evaluate_formula(df, f).to_list() == ["match", "no", "no"]


def test_gt_with_and_arithmetic_operand():
    """比较运算符左操作数含算术 + AND 组合。"""
    df = pl.DataFrame({"a": [10.0, 5.0], "b": [3.0, 3.0], "c": [1, 2]})
    f = "a - b > 5 AND c = 1"
    assert evaluate_formula(df, f).to_list() == [True, False]  # row0: 7>5 & 1=1 → T ; row1: 2>5 → F


# ─── compile_formula 返回 Expr ─────────────────────────────────

def test_compile_formula_returns_expr():
    expr = compile_formula("a + b", ["a", "b"])
    df = pl.DataFrame({"a": [1, 2], "b": [3, 4]})
    assert df.select(expr.alias("r"))["r"].to_list() == [4, 6]


# ─── 边界：NOT / 混合优先级 / 错误信息 ──────────────────────────

def test_not_operator():
    df = pl.DataFrame({"x": [1, 2]})
    assert evaluate_formula(df, "NOT (x = 1)").to_list() == [False, True]


def test_mixed_and_or_precedence():
    """AND 结合度高于 OR：(x>1 AND y=2) OR z=3。"""
    df = pl.DataFrame({"x": [2, 2, 0], "y": [2, 0, 2], "z": [3, 0, 0]})
    assert evaluate_formula(df, "x > 1 AND y = 2 OR z = 3").to_list() == [True, False, False]


def test_unknown_function_raises():
    df = pl.DataFrame({"x": [1]})
    with pytest.raises(ValueError, match="未知函数"):
        evaluate_formula(df, "FOO(x)")


def test_parse_error_message():
    df = pl.DataFrame({"x": [1]})
    with pytest.raises(ValueError, match="公式语法错误"):
        evaluate_formula(df, "IF(a, b")  # 括号不闭合

