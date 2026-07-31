"""规则引擎常量 — 枚举类型替代硬编码字符串，消除魔法值。"""
from enum import Enum


# ───────────────────────── 规则类型 ─────────────────────────

class RuleType(str, Enum):
    """规则类型枚举。继承 str 以便与 JSON 字段值直接比较。"""
    MAPPING = "mapping"
    CLEANING = "cleaning"
    LOOKUP = "lookup"
    COMPUTED = "computed"

    @classmethod
    def _missing_(cls, value):
        """未知类型返回 None，调用方自行处理。"""
        return None


# ───────────────────────── 操作符 ─────────────────────────

class Operator(str, Enum):
    """统一操作符枚举 — 条件映射、清洗替换、回退条件共享同一套操作符。"""
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    EQ = "eq"
    NEQ = "neq"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    MATCHES = "matches"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    BETWEEN = "between"


# ───────────────────────── 结果类型 ─────────────────────────

class ResultType(str, Enum):
    """条件命中后的结果值类型。"""
    CONSTANT = "constant"
    FIELD_VALUE = "field_value"
    NULL = "null"


# ───────────────────────── 清洗动作 ─────────────────────────

class CleaningAction(str, Enum):
    """清洗步骤动作类型。"""
    FILL_NULL = "fill_null"
    REPLACE = "replace"
    TRIM = "trim"
    REGEX_EXTRACT = "regex_extract"
    SUBSTRING = "substring"


# ───────────────────────── 默认结果 ─────────────────────────

class DefaultResult(str, Enum):
    """特殊默认结果值。"""
    KEEP_ORIGINAL = "keep_original"
