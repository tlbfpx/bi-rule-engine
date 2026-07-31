"""Observer Pattern — 事件总线

提供事件基类、监听器接口与线程安全的事件总线（单例）。
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from app.patterns.singleton import Singleton


@dataclass
class Event:
    """事件基类"""

    name: str
    timestamp: datetime = field(default_factory=datetime.now)


class IEventListener(Protocol):
    """监听器接口"""

    def on_event(self, event: Event) -> None:
        """处理事件

        Args:
            event: 触发的事件
        """
        ...


class EventBus(metaclass=Singleton):
    """事件总线 — 线程安全的单例

    支持按事件名称订阅监听器，发布事件时通知所有订阅者。
    """

    def __init__(self) -> None:
        self._listeners: dict[str, list[IEventListener]] = {}
        self._lock: threading.Lock = threading.Lock()

    def subscribe(self, event_name: str, listener: IEventListener) -> None:
        """订阅事件

        Args:
            event_name: 事件名称
            listener: 监听器实例
        """
        with self._lock:
            if event_name not in self._listeners:
                self._listeners[event_name] = []
            self._listeners[event_name].append(listener)

    def publish(self, event: Event) -> None:
        """发布事件 — 通知所有订阅该事件名称的监听器

        Args:
            event: 要发布的事件
        """
        # 在锁内拷贝监听器列表，锁外遍历以避免长锁与回调死锁
        with self._lock:
            listeners = list(self._listeners.get(event.name, []))
        for listener in listeners:
            listener.on_event(event)
