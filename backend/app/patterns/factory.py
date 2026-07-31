"""Factory Pattern — 泛型工厂基础设施

提供工厂接口与工厂注册表，支持按 key 注册并创建实例。
"""
from __future__ import annotations

from typing import Any, Protocol


class IFactory[T](Protocol):
    """工厂接口 — 创建泛型类型 T 的实例"""

    def create(self, **kwargs: Any) -> T:
        """创建实例

        Args:
            **kwargs: 创建参数

        Returns:
            类型 T 的实例
        """
        ...


class FactoryRegistry[T]:
    """工厂注册表 — 按键注册工厂并创建实例"""

    def __init__(self) -> None:
        self._factories: dict[str, IFactory[T]] = {}

    def register(self, key: str, factory: IFactory[T]) -> None:
        """注册工厂

        Args:
            key: 工厂标识
            factory: 工厂实例
        """
        self._factories[key] = factory

    def create(self, key: str, **kwargs: Any) -> T:
        """根据键创建实例

        Args:
            key: 工厂标识
            **kwargs: 传递给工厂的创建参数

        Raises:
            KeyError: 未注册该键对应的工厂
        """
        if key not in self._factories:
            raise KeyError(f"Factory not registered for key: {key}")
        return self._factories[key].create(**kwargs)
