"""领域值对象 — 不可变、自校验的领域概念封装。

值对象遵循 DDD 原则：
- 不可变（frozen dataclass）
- 创建时自校验，构造成功即合法
- 封装领域规则，避免原始类型滥用
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import polars as pl

__all__ = ["RuleType", "FieldName", "Formula"]

# 合法规则类型白名单
_VALID_RULE_TYPES: frozenset[str] = frozenset({"mapping", "cleaning", "lookup", "computed"})

# 合法字段名：字母/下划线开头，仅含字母数字下划线
_FIELD_NAME_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


@dataclass(frozen=True)
class RuleType:
    """规则类型值对象 — 不可变。

    封装规则类型的合法性校验，确保类型值始终在白名单内。

    Attributes:
        value: 规则类型字符串（mapping/cleaning/lookup/computed）
    """

    value: str

    def __post_init__(self) -> None:
        if self.value not in _VALID_RULE_TYPES:
            raise ValueError(f"无效的规则类型: {self.value}，合法值: {sorted(_VALID_RULE_TYPES)}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class FieldName:
    """字段名值对象 — 不可变。

    封装字段名的合法性校验，防止 SQL 注入和非法标识符。
    规则：字母或下划线开头，仅含字母、数字、下划线。

    Attributes:
        value: 字段名字符串
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value or not _FIELD_NAME_PATTERN.match(self.value):
            raise ValueError(f"无效的字段名: {self.value}，需匹配 {_FIELD_NAME_PATTERN.pattern}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Formula:
    """公式值对象 — 不可变，封装 DSL 编译。

    创建时校验表达式非空，编译时委托给 formula_engine。
    延迟编译：compile() 在需要时才调用，避免构造时开销。

    Attributes:
        expression: 公式 DSL 表达式字符串
    """

    expression: str

    def __post_init__(self) -> None:
        if not self.expression or not self.expression.strip():
            raise ValueError("公式表达式不能为空")

    def compile(self, columns: list[str] | None = None) -> pl.Expr:
        """将 DSL 公式编译为 Polars Expression。

        Args:
            columns: 可用列名列表（兼容参数，实现不依赖）

        Returns:
            编译后的 Polars Expression

        Raises:
            ValueError: 公式语法错误或编译失败
        """
        from app.engine.formula_engine import compile_formula

        return compile_formula(self.expression, columns)

    def __str__(self) -> str:
        return self.expression
