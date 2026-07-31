"""Proxy Pattern — 代理基础设施

提供代理接口与缓存代理，使用 functools.lru_cache 缓存相同参数的调用结果。
"""
from __future__ import annotations

import functools
from typing import Any, Protocol


class IProxy[T](Protocol):
    """代理接口 — 代理目标对象的方法调用"""

    def execute(self, *args: Any, **kwargs: Any) -> T:
        """执行代理调用

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            类型 T 的结果
        """
        ...


class CachedProxy[T]:
    """缓存代理 — 对相同参数调用返回缓存结果

    使用 functools.lru_cache 缓存内部执行结果，要求参数可哈希。
    """

    def __init__(self, target: Any) -> None:
        """初始化缓存代理

        Args:
            target: 被代理的目标对象，需提供 execute(*args, **kwargs) 方法
        """
        self._target = target

        @functools.lru_cache(maxsize=128)
        def _cached(key: tuple) -> Any:
            args, kwargs_items = key
            return target.execute(*args, **dict(kwargs_items))

        self._cached = _cached

    def execute(self, *args: Any, **kwargs: Any) -> T:
        """执行代理调用，命中缓存则直接返回

        Args:
            *args: 位置参数（需可哈希）
            **kwargs: 关键字参数（键值需可哈希）

        Returns:
            类型 T 的结果
        """
        key = (args, tuple(sorted(kwargs.items())))
        return self._cached(key)
