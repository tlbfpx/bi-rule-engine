"""结果解析器注册表 — 将条件组的结果类型映射为 Polars 表达式。

用例：condition_group.result_type = "constant" → pl.lit(condition_group.result_value)
新增结果类型只需在此字典中添加一个条目。
"""
import polars as pl
from app.engine.constants import ResultType


def _resolve_constant(df: pl.DataFrame, cg) -> pl.Expr:
    """常量值 — pl.lit(cg.result_value)"""
    return pl.lit(cg.result_value)


def _resolve_field_value(df: pl.DataFrame, cg) -> pl.Expr:
    """列引用 — 如果列存在则 pl.col(name)，否则作为常量"""
    if cg.result_value is not None and cg.result_value in df.columns:
        return pl.col(cg.result_value)
    return pl.lit(cg.result_value)


def _resolve_null(df: pl.DataFrame, cg) -> pl.Expr:
    """空值 — pl.lit(None)"""
    return pl.lit(None)


RESULT_RESOLVER_REGISTRY: dict[str, callable] = {
    ResultType.CONSTANT: _resolve_constant,
    ResultType.FIELD_VALUE: _resolve_field_value,
    ResultType.NULL: _resolve_null,
}
