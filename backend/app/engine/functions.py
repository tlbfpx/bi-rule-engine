"""[已废弃] 内置函数库 — 规则 DSL 中可调用的所有函数。

此模块已被 formula_engine.py 中的 FUNCS 字典完全取代（双模式 Expr/scalar 实现）。
保留此文件仅为兼容旧代码引用；新代码请直接使用 formula_engine.FUNCS。
"""
import re
import math
import warnings

warnings.warn(
    "app.engine.functions 已废弃，请使用 app.engine.formula_engine.FUNCS",
    DeprecationWarning,
    stacklevel=2,
)


def fn_split(value: str, delimiter: str, index: int) -> str | None:
    """按分隔符取第 N 段 (1-indexed)"""
    if not value:
        return None
    parts = str(value).split(delimiter)
    if 1 <= index <= len(parts):
        return parts[index - 1]
    return None


def fn_coalesce(*values) -> object:
    """取第一个非空值"""
    for v in values:
        if v is not None and v != "":
            return v
    return None


def fn_round(value: float, decimals: int = 2) -> float | None:
    """四舍五入"""
    if value is None:
        return None
    return round(float(value), decimals)


def fn_replace(value: str, old: str, new: str) -> str | None:
    """字符串替换"""
    if not value:
        return value
    return str(value).replace(old, new)


def fn_upper(value: str) -> str | None:
    if not value:
        return value
    return str(value).upper()


def fn_lower(value: str) -> str | None:
    if not value:
        return value
    return str(value).lower()


def fn_concat(*args, sep: str = "") -> str:
    """字符串拼接"""
    return sep.join(str(a) for a in args if a is not None)


def fn_if(condition: bool, true_val, false_val):
    """三元条件"""
    return true_val if condition else false_val


def fn_abs(value: float) -> float | None:
    if value is None:
        return None
    return abs(float(value))


def fn_ceil(value: float) -> float | None:
    if value is None:
        return None
    return math.ceil(float(value))


def fn_floor(value: float) -> float | None:
    if value is None:
        return None
    return math.floor(float(value))


def fn_length(value: str) -> int:
    if not value:
        return 0
    return len(str(value))


def fn_trim(value: str) -> str | None:
    if not value:
        return value
    return str(value).strip()


def fn_substr(value: str, start: int, length: int) -> str | None:
    if not value:
        return value
    s = str(value)
    return s[start:start + length]


def fn_contains(value: str, substring: str) -> bool:
    if not value:
        return False
    return substring in str(value)


def fn_not_contains(value: str, substring: str) -> bool:
    return not fn_contains(value, substring)


def fn_matches(value: str, pattern: str) -> bool:
    if not value:
        return False
    return bool(re.search(pattern, str(value)))


def fn_starts_with(value: str, prefix: str) -> bool:
    if not value:
        return False
    return str(value).startswith(prefix)


def fn_ends_with(value: str, suffix: str) -> bool:
    if not value:
        return False
    return str(value).endswith(suffix)


FUNCTION_REGISTRY = {
    "SPLIT": fn_split,
    "COALESCE": fn_coalesce,
    "ROUND": fn_round,
    "REPLACE": fn_replace,
    "UPPER": fn_upper,
    "LOWER": fn_lower,
    "CONCAT": fn_concat,
    "IF": fn_if,
    "ABS": fn_abs,
    "CEIL": fn_ceil,
    "FLOOR": fn_floor,
    "LENGTH": fn_length,
    "TRIM": fn_trim,
    "SUBSTR": fn_substr,
}
