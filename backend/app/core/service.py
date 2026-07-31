"""BaseService — 模板方法模式 + 单一职责（阿里规约）。

通过构造函数注入 Repository，提供通用的 CRUD 业务操作。
每个操作包含 before/after 钩子，子类可按需重写以扩展业务逻辑，
无需修改核心流程，符合开闭原则。
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from app.core.exceptions import NotFoundException

R = TypeVar("R")


class BaseService(Generic[R]):
    """泛型服务基类。

    通过构造函数注入 Repository，R 为 Repository 类型。
    提供模板方法模式的 CRUD 操作，每个方法有 before/after 钩子。

    Attributes:
        repository: 注入的仓储实例
    """

    def __init__(self, repository: R) -> None:
        self.repository = repository

    async def create(self, data: dict[str, Any]) -> Any:
        """创建实体（模板方法）。

        流程：before_create -> 构建实体 -> repository.save -> after_create

        Args:
            data: 实体字段字典

        Returns:
            创建后的实体
        """
        await self.before_create(data)
        model_class = self.repository.model_class
        entity = model_class(**data)
        result = await self.repository.save(entity)
        await self.after_create(result)
        return result

    async def update(self, id: str, data: dict[str, Any]) -> Any:
        """更新实体（模板方法）。

        流程：before_update -> 查找实体 -> repository.update -> after_update

        Args:
            id: 实体主键
            data: 需更新的字段字典

        Returns:
            更新后的实体

        Raises:
            NotFoundException: 实体不存在时抛出
        """
        await self.before_update(id, data)
        entity = await self.repository.find_by_id(id)
        if entity is None:
            raise NotFoundException(detail=f"实体不存在: id={id}")
        result = await self.repository.update(entity, **data)
        await self.after_update(result)
        return result

    async def delete(self, id: str) -> None:
        """删除实体（模板方法）。

        流程：before_delete -> 查找实体 -> repository.delete -> after_delete

        Args:
            id: 实体主键

        Raises:
            NotFoundException: 实体不存在时抛出
        """
        await self.before_delete(id)
        entity = await self.repository.find_by_id(id)
        if entity is None:
            raise NotFoundException(detail=f"实体不存在: id={id}")
        await self.repository.delete(entity)
        await self.after_delete(id)

    async def get_by_id(self, id: str) -> Any:
        """根据 ID 查询实体（模板方法）。

        流程：before_get_by_id -> repository.find_by_id -> after_get_by_id

        Args:
            id: 实体主键

        Returns:
            实体对象，不存在则返回 None
        """
        await self.before_get_by_id(id)
        entity = await self.repository.find_by_id(id)
        await self.after_get_by_id(entity)
        return entity

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        **filters: Any,
    ) -> tuple[list[Any], int]:
        """分页查询实体列表（模板方法）。

        流程：before_list -> repository.find_all -> after_list

        Args:
            page: 页码（从 1 开始）
            page_size: 每页条数
            **filters: 过滤条件键值对

        Returns:
            (实体列表, 总数) 元组
        """
        await self.before_list(page, page_size, **filters)
        offset = (page - 1) * page_size

        # 将关键字过滤条件转为 SQLAlchemy 等值表达式
        conditions = []
        model_class = self.repository.model_class
        for key, value in filters.items():
            column = getattr(model_class, key, None)
            if column is not None:
                conditions.append(column == value)

        items, total = await self.repository.find_all(
            *conditions, offset=offset, limit=page_size
        )
        await self.after_list(items, total)
        return items, total

    # ────────────── 钩子方法，子类按需重写 ──────────────

    async def before_create(self, data: dict[str, Any]) -> None:
        """创建前钩子，子类可重写以做参数校验、唯一性检查等。"""
        pass

    async def after_create(self, entity: Any) -> None:
        """创建后钩子，子类可重写以做缓存清理、事件发布等。"""
        pass

    async def before_update(self, id: str, data: dict[str, Any]) -> None:
        """更新前钩子，子类可重写以做权限校验、字段过滤等。"""
        pass

    async def after_update(self, entity: Any) -> None:
        """更新后钩子，子类可重写以做缓存更新、日志记录等。"""
        pass

    async def before_delete(self, id: str) -> None:
        """删除前钩子，子类可重写以做关联检查、权限校验等。"""
        pass

    async def after_delete(self, id: str) -> None:
        """删除后钩子，子类可重写以做缓存清理、级联处理等。"""
        pass

    async def before_get_by_id(self, id: str) -> None:
        """查询前钩子，子类可重写以做缓存预加载等。"""
        pass

    async def after_get_by_id(self, entity: Any) -> None:
        """查询后钩子，子类可重写以做数据脱敏、缓存写入等。"""
        pass

    async def before_list(
        self, page: int, page_size: int, **filters: Any
    ) -> None:
        """列表查询前钩子，子类可重写以做参数校验等。"""
        pass

    async def after_list(self, items: list[Any], total: int) -> None:
        """列表查询后钩子，子类可重写以做数据加工等。"""
        pass
