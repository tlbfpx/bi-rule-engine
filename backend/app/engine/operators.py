"""统一操作符注册表 — 所有条件评估逻辑的单一来源。

设计原则：
- 每个操作符是一个 (Series, value) → boolean-mask 的可调用对象。
- 注册表是模块级 dict，新增操作符只需添加一个条目。
- cleaning/lookup/mapping 等所有模块共享同一套操作符实现，消除重复。
"""
import polars as pl
from typing import Any
from app.engine.constants import Operator

# ───────────────────────── 操作符实现 ─────────────────────────


def _op_is_null(col: pl.Series, _val: Any = None) -> pl.Series:
    return col.is_null() | (col.cast(pl.Utf8) == "")


def _op_is_not_null(col: pl.Series, _val: Any = None) -> pl.Series:
    return ~(col.is_null() | (col.cast(pl.Utf8) == ""))


def _op_eq(col: pl.Series, val: Any) -> pl.Series:
    """相等比较：数值列做数值比较，其余做字符串比较。"""
    if col.dtype.is_numeric():
        try:
            return col == float(val)
        except (ValueError, TypeError):
            return col.cast(pl.Utf8) == str(val)
    return col.cast(pl.Utf8) == str(val)


def _op_neq(col: pl.Series, val: Any) -> pl.Series:
    """不等比较：数值列做数值比较，其余做字符串比较。"""
    if col.dtype.is_numeric():
        try:
            return col != float(val)
        except (ValueError, TypeError):
            return col.cast(pl.Utf8) != str(val)
    return col.cast(pl.Utf8) != str(val)


def _op_contains(col: pl.Series, val: Any) -> pl.Series:
    return col.cast(pl.Utf8).str.contains(str(val), literal=True)


def _op_not_contains(col: pl.Series, val: Any) -> pl.Series:
    return ~col.cast(pl.Utf8).str.contains(str(val), literal=True)


def _op_matches(col: pl.Series, val: Any) -> pl.Series:
    return col.cast(pl.Utf8).str.contains(str(val))


def _op_starts_with(col: pl.Series, val: Any) -> pl.Series:
    return col.cast(pl.Utf8).str.starts_with(str(val))


def _op_ends_with(col: pl.Series, val: Any) -> pl.Series:
    return col.cast(pl.Utf8).str.ends_with(str(val))


def _op_gt(col: pl.Series, val: Any) -> pl.Series:
    return col.cast(pl.Float64, strict=False) > float(val)


def _op_gte(col: pl.Series, val: Any) -> pl.Series:
    return col.cast(pl.Float64, strict=False) >= float(val)


def _op_lt(col: pl.Series, val: Any) -> pl.Series:
    return col.cast(pl.Float64, strict=False) < float(val)


def _op_lte(col: pl.Series, val: Any) -> pl.Series:
    return col.cast(pl.Float64, strict=False) <= float(val)


def _op_in(col: pl.Series, val: Any) -> pl.Series:
    if isinstance(val, list):
        vals = [str(v) for v in val]
    elif isinstance(val, str) and "," in val:
        vals = [v.strip() for v in val.split(",")]
    else:
        vals = [str(val)]
    return col.cast(pl.Utf8).is_in(vals)


def _op_between(col: pl.Series, val: Any) -> pl.Series:
    lo, hi = (val[0], val[1]) if isinstance(val, (list, tuple)) else (val, val)
    num_col = col.cast(pl.Float64, strict=False)
    return (num_col >= float(lo)) & (num_col <= float(hi))


# ───────────────────────── 注册表 ─────────────────────────

# 操作符名称 → 实现函数 的映射表。
# 新增操作符只需在此字典中添加一个条目。
OPERATOR_REGISTRY: dict[str, callable] = {
    Operator.IS_NULL: _op_is_null,
    Operator.IS_NOT_NULL: _op_is_not_null,
    Operator.EQ: _op_eq,
    Operator.NEQ: _op_neq,
    Operator.CONTAINS: _op_contains,
    Operator.NOT_CONTAINS: _op_not_contains,
    Operator.MATCHES: _op_matches,
    Operator.STARTS_WITH: _op_starts_with,
    Operator.ENDS_WITH: _op_ends_with,
    Operator.GT: _op_gt,
    Operator.GTE: _op_gte,
    Operator.LT: _op_lt,
    Operator.LTE: _op_lte,
    Operator.IN: _op_in,
    Operator.BETWEEN: _op_between,
}


def evaluate_condition(col: pl.Series, operator: str, value: Any) -> pl.Series:
    """根据操作符名称评估条件，返回布尔 mask Series。

    如果操作符未注册，返回全 False mask；如果列不存在（调用方应预先检查），
    此处不做判断，直接执行（会抛 Polars 异常，有明确的错误信息）。
    """
    impl = OPERATOR_REGISTRY.get(operator)
    if impl is None:
        return pl.Series("_unknown", [False] * len(col))
    return impl(col, value)
