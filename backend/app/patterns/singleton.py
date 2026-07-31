"""Singleton Pattern — 单例元类

提供线程安全的单例元类，使用方式：

    class EventBus(metaclass=Singleton):
        ...
"""
from __future__ import annotations

import threading
from typing import Any


class Singleton(type):
    """单例元类 — 确保每个类只有一个实例（线程安全）

    使用双重检查锁定（double-checked locking）保证并发安全。
    """

    _instances: dict[type, Any] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        # 快速路径：实例已存在直接返回
        if cls not in Singleton._instances:
            with Singleton._lock:
                # 双重检查：拿到锁后再次确认
                if cls not in Singleton._instances:
                    Singleton._instances[cls] = super().__call__(*args, **kwargs)
        return Singleton._instances[cls]
