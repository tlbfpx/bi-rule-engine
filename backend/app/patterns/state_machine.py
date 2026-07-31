"""State Pattern — 状态机基础设施

提供状态抽象基类与状态机，支持状态注册、转换定义与事件触发。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class State(ABC):
    """状态抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """状态名称"""
        ...

    def on_enter(self, context: Any) -> None:
        """进入状态时的生命周期钩子 — 子类可重写

        Args:
            context: 状态机上下文
        """
        pass

    def on_exit(self, context: Any) -> None:
        """离开状态时的生命周期钩子 — 子类可重写

        Args:
            context: 状态机上下文
        """
        pass


class StateMachine:
    """状态机 — 管理状态与转换，支持事件触发状态流转"""

    def __init__(self) -> None:
        self._states: dict[str, State] = {}
        # (from_state_name, event_name) -> to_state_name
        self._transitions: dict[tuple[str, str], str] = {}
        self._current_state: State | None = None

    def add_state(self, state: State) -> None:
        """添加状态；首个添加的状态自动设为初始状态

        Args:
            state: 状态实例
        """
        self._states[state.name] = state
        if self._current_state is None:
            self._current_state = state
            state.on_enter(None)

    def add_transition(self, from_state: str, to_state: str, event_name: str) -> None:
        """添加状态转换

        Args:
            from_state: 起始状态名称
            to_state: 目标状态名称
            event_name: 触发事件名称
        """
        self._transitions[(from_state, event_name)] = to_state

    def trigger(self, event_name: str) -> None:
        """触发事件，执行状态转换

        Args:
            event_name: 事件名称

        Raises:
            RuntimeError: 尚未设置当前状态
            ValueError: 当前状态下无该事件的转换或目标状态未注册
        """
        if self._current_state is None:
            raise RuntimeError("No current state set")
        key = (self._current_state.name, event_name)
        if key not in self._transitions:
            raise ValueError(
                f"No transition for event '{event_name}' "
                f"from state '{self._current_state.name}'"
            )
        to_state_name = self._transitions[key]
        if to_state_name not in self._states:
            raise ValueError(f"Target state not registered: {to_state_name}")
        old_state = self._current_state
        new_state = self._states[to_state_name]
        old_state.on_exit(None)
        self._current_state = new_state
        new_state.on_enter(None)

    @property
    def current_state(self) -> State | None:
        """当前状态"""
        return self._current_state
