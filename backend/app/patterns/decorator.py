"""Decorator Pattern — 装饰器基础设施

提供服务接口与日志、指标装饰器，通过构造函数注入被包装对象。
"""
from __future__ import annotations

import logging
import time
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class IService[T](Protocol):
    """服务接口"""

    def execute(self, **kwargs: Any) -> T:
        """执行服务

        Args:
            **kwargs: 调用参数

        Returns:
            类型 T 的结果
        """
        ...


class LoggingDecorator[T]:
    """日志装饰器 — 自动记录方法调用日志"""

    def __init__(self, wrapped: IService[T]) -> None:
        """初始化装饰器

        Args:
            wrapped: 被包装的服务
        """
        self._wrapped = wrapped

    def execute(self, **kwargs: Any) -> T:
        """执行服务并记录调用日志"""
        logger.info("Executing service, kwargs: %s", kwargs)
        result = self._wrapped.execute(**kwargs)
        logger.info("Service executed, result type: %s", type(result).__name__)
        return result


class MetricsDecorator[T]:
    """指标装饰器 — 自动记录执行耗时"""

    def __init__(self, wrapped: IService[T]) -> None:
        """初始化装饰器

        Args:
            wrapped: 被包装的服务
        """
        self._wrapped = wrapped

    def execute(self, **kwargs: Any) -> T:
        """执行服务并记录耗时"""
        start = time.perf_counter()
        result = self._wrapped.execute(**kwargs)
        elapsed = time.perf_counter() - start
        logger.info("Service executed in %.4fs", elapsed)
        return result
