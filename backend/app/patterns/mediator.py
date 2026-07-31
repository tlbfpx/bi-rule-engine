"""Mediator Pattern — 中介者基础设施

提供中介者接口与具体实现，通过 handler 注册表解耦组件间通信。
"""
from __future__ import annotations

from typing import Any, Callable, Protocol


class IMediator(Protocol):
    """中介者接口"""

    def send(self, message_type: str, payload: Any) -> Any:
        """发送消息

        Args:
            message_type: 消息类型
            payload: 消息载荷

        Returns:
            处理结果
        """
        ...


class Mediator:
    """具体中介者 — 维护 handler 注册表并分发消息"""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., Any]] = {}

    def register_handler(
        self, message_type: str, handler: Callable[..., Any]
    ) -> None:
        """注册消息处理器

        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        self._handlers[message_type] = handler

    def send(self, message_type: str, payload: Any) -> Any:
        """发送消息给已注册的处理器

        Args:
            message_type: 消息类型
            payload: 消息载荷

        Raises:
            KeyError: 未注册该消息类型的处理器
        """
        if message_type not in self._handlers:
            raise KeyError(f"No handler registered for message type: {message_type}")
        return self._handlers[message_type](payload)
