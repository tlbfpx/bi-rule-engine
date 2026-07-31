"""Template Method Pattern — 模板方法基础设施

提供泛型模板基类，execute 为模板方法（final），
依次调用 before() -> do_execute() -> after()。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, final


class BaseTemplate[T](ABC):
    """模板基类 — execute 为模板方法（final）

    子类必须实现 do_execute()，可选重写 before()/after() 钩子。
    """

    @final
    def execute(self, **kwargs: Any) -> T:
        """模板方法 — 依次调用 before -> do_execute -> after

        Args:
            **kwargs: 传递给各阶段的参数

        Returns:
            do_execute 的结果
        """
        self.before(**kwargs)
        result = self.do_execute(**kwargs)
        self.after(result, **kwargs)
        return result

    def before(self, **kwargs: Any) -> None:
        """前置钩子 — 子类可重写

        Args:
            **kwargs: 模板方法传入的参数
        """
        pass

    @abstractmethod
    def do_execute(self, **kwargs: Any) -> T:
        """核心逻辑 — 子类必须实现

        Args:
            **kwargs: 模板方法传入的参数

        Returns:
            类型 T 的结果
        """
        ...

    def after(self, result: T, **kwargs: Any) -> None:
        """后置钩子 — 子类可重写

        Args:
            result: do_execute 的结果
            **kwargs: 模板方法传入的参数
        """
        pass
