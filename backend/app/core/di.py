"""依赖注入容器 — 避免硬编码依赖（阿里规约）。

通过 DIContainer 管理依赖的注册与解析，支持单例和工厂两种模式。
生产环境通过容器注册接口与实现的绑定，测试环境可替换为 Mock 实现。
"""
import threading
from collections.abc import Callable
from typing import Any, TypeVar, cast

T = TypeVar("T")


class DIContainer:
    """简单的依赖注入容器（线程安全 Singleton）。

    支持两种注册方式：
    - register: 注册单例实例，resolve 时返回同一实例
    - register_factory: 注册工厂函数，resolve 时每次调用工厂创建新实例

    使用示例::

        container = DIContainer()
        container.register(ICache, MemoryCache())
        container.register_factory(IRepository, lambda: UserRepository(db))
        cache = container.resolve(ICache)
    """

    _instance: "DIContainer | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "DIContainer":
        # 双重检查锁定（DCL），确保多线程下只创建一个实例
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        with self._lock:
            if getattr(self, "_initialized", False):
                return
            self._initialized = True
            self._instances: dict[type, Any] = {}
            self._factories: dict[type, Callable[[], Any]] = {}

    def register(self, interface_type: type[T], implementation: T) -> None:
        """注册单例实例。

        Args:
            interface_type: 接口/抽象类型
            implementation: 具体实现实例
        """
        self._factories.pop(interface_type, None)
        self._instances[interface_type] = implementation

    def register_factory(
        self,
        interface_type: type[T],
        factory: Callable[[], T],
    ) -> None:
        """注册工厂函数，每次 resolve 创建新实例。

        Args:
            interface_type: 接口/抽象类型
            factory: 工厂函数，调用返回新实例
        """
        self._instances.pop(interface_type, None)
        self._factories[interface_type] = factory

    def resolve(self, interface_type: type[T]) -> T:
        """解析依赖，返回注册的实例或工厂创建的实例。

        优先返回单例实例，其次调用工厂函数创建新实例。

        Args:
            interface_type: 接口/抽象类型

        Returns:
            对应的实现实例

        Raises:
            KeyError: 未注册的依赖类型
        """
        if interface_type in self._instances:
            return cast("T", self._instances[interface_type])
        if interface_type in self._factories:
            return cast("T", self._factories[interface_type]())
        raise KeyError(f"未注册的依赖: {interface_type.__name__}")

    def clear(self) -> None:
        """清空容器（测试用）。

        清除所有已注册的单例实例和工厂函数。
        """
        self._instances.clear()
        self._factories.clear()
