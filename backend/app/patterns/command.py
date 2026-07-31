"""Command Pattern — 命令基础设施

提供命令接口与命令调用器，维护命令历史支持 undo/redo。
"""
from __future__ import annotations

from typing import Any, Protocol


class ICommand(Protocol):
    """命令接口

    undo() 为可选实现：不支持撤销的命令可实现为 no-op。
    """

    def execute(self) -> Any:
        """执行命令

        Returns:
            执行结果
        """
        ...

    def undo(self) -> Any:
        """撤销命令（可选）

        Returns:
            撤销结果
        """
        ...


class CommandInvoker:
    """命令调用器 — 维护命令历史，支持撤销与重做"""

    def __init__(self) -> None:
        self._history: list[ICommand] = []
        self._redo_stack: list[ICommand] = []

    def execute(self, command: ICommand) -> Any:
        """执行命令并记录历史

        Args:
            command: 命令实例

        Returns:
            执行结果
        """
        result = command.execute()
        self._history.append(command)
        # 新命令清空重做栈
        self._redo_stack.clear()
        return result

    def undo(self) -> Any:
        """撤销最近一次命令

        Returns:
            撤销结果；无历史时返回 None
        """
        if not self._history:
            return None
        command = self._history.pop()
        result = command.undo()
        self._redo_stack.append(command)
        return result

    def redo(self) -> Any:
        """重做最近撤销的命令

        Returns:
            重做结果；无可重做命令时返回 None
        """
        if not self._redo_stack:
            return None
        command = self._redo_stack.pop()
        result = command.execute()
        self._history.append(command)
        return result

    def get_history(self) -> list[ICommand]:
        """获取命令历史副本"""
        return list(self._history)
