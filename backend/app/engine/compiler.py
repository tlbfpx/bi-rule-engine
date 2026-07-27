"""条件编译器 — 将 ConditionRow 的 operator + value 编译为可执行函数"""
import re
from typing import Any, Callable
from app.engine.parser import ConditionRow

OperatorFunc = Callable[[Any], bool]


def compile_condition(row: ConditionRow) -> OperatorFunc:
    """编译单个条件行为可执行函数"""
    op = row.operator
    val = row.value

    if op == "is_null":
        return lambda v: v is None or v == ""

    if op == "is_not_null":
        return lambda v: v is not None and v != ""

    if op == "eq":
        return lambda v: str(v) == str(val) if v is not None else False

    if op == "neq":
        return lambda v: str(v) != str(val) if v is not None else True

    if op == "contains":
        return lambda v: str(val) in str(v) if v is not None else False

    if op == "not_contains":
        return lambda v: str(val) not in str(v) if v is not None else True

    if op == "matches":
        pattern = re.compile(str(val))
        return lambda v: bool(pattern.search(str(v))) if v is not None else False

    if op == "starts_with":
        return lambda v: str(v).startswith(str(val)) if v is not None else False

    if op == "ends_with":
        return lambda v: str(v).endswith(str(val)) if v is not None else False

    if op == "in":
        val_list = val if isinstance(val, list) else [val]
        return lambda v: str(v) in [str(x) for x in val_list] if v is not None else False

    if op == "between":
        lo, hi = val if isinstance(val, (list, tuple)) else (val, val)
        return lambda v: float(lo) <= float(v) <= float(hi) if v is not None else False

    if op == "gt":
        return lambda v: float(v) > float(val) if v is not None else False
    if op == "gte":
        return lambda v: float(v) >= float(val) if v is not None else False
    if op == "lt":
        return lambda v: float(v) < float(val) if v is not None else False
    if op == "lte":
        return lambda v: float(v) <= float(val) if v is not None else False

    raise ValueError(f"Unknown operator: {op}")


def evaluate_group(group, row_data: dict) -> bool:
    """对一行数据评估整个条件组"""
    results = []
    for cond_row in group.rows:
        func = compile_condition(cond_row)
        field_val = row_data.get(cond_row.field)
        results.append(func(field_val))

    if group.logic == "AND":
        return all(results)
    else:
        return any(results)
