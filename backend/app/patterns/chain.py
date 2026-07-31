"""Chain of Responsibility Pattern — 责任链基础设施

提供处理器接口与责任链，handle 返回 True 表示继续传递，False 表示终止。
"""
from __future__ import annotations

from typing import Protocol, Self


class IHandler[T](Protocol):
    """处理器接口 — handle 返回 True 表示继续链，False 表示终止"""

    def handle(self, context: T) -> bool:
        """处理上下文

        Args:
            context: 请求上下文

        Returns:
            True 表示继续传递给下一个处理器，False 表示终止链
        """
        ...


class HandlerChain[T]:
    """责任链 — 按顺序调用处理器，支持链式添加"""

    def __init__(self) -> None:
        self._handlers: list[IHandler[T]] = []

    def add_handler(self, handler: IHandler[T]) -> Self:
        """添加处理器到链尾

        Args:
            handler: 处理器实例

        Returns:
            self，支持链式调用
        """
        self._handlers.append(handler)
        return self

    def execute(self, context: T) -> None:
        """依次执行处理器，遇到返回 False 的处理器则终止"""
        for handler in self._handlers:
            if not handler.handle(context):
                break
