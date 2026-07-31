"""Strategy Pattern — 策略基础设施

提供策略接口与策略注册表，支持按名称注册并获取策略。
"""
from __future__ import annotations

from typing import Any, Protocol


class IStrategy[T](Protocol):
    """策略接口"""

    def execute(self, *args: Any, **kwargs: Any) -> T:
        """执行策略

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            类型 T 的结果
        """
        ...


class StrategyRegistry[T]:
    """策略注册表 — 按名称注册并获取策略"""

    def __init__(self) -> None:
        self._strategies: dict[str, IStrategy[T]] = {}

    def register(self, name: str, strategy: IStrategy[T]) -> None:
        """注册策略

        Args:
            name: 策略名称
            strategy: 策略实例
        """
        self._strategies[name] = strategy

    def get(self, name: str) -> IStrategy[T]:
        """获取策略

        Args:
            name: 策略名称

        Raises:
            KeyError: 未注册该名称对应的策略
        """
        if name not in self._strategies:
            raise KeyError(f"Strategy not registered: {name}")
        return self._strategies[name]
