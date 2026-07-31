"""Repository 模式 — 数据访问统一抽象（阿里规约）。

通过 IRepository 协议定义数据访问接口，BaseRepository 提供基于
SQLAlchemy AsyncSession 的通用实现，子类可通过 _build_filters
模板方法扩展自定义查询条件。
"""
from typing import Any, Protocol, TypeVar, runtime_checkable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

M = TypeVar("M")


@runtime_checkable
class IRepository(Protocol[M]):
    """泛型仓储接口协议。

    M 为 ORM 模型类型，所有方法均为异步。
    """

    async def find_by_id(self, id: str) -> M | None:
        """根据主键 ID 查询实体。"""
        ...

    async def find_all(
        self,
        *filters: Any,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[M], int]:
        """分页查询实体列表，返回 (实体列表, 总数)。"""
        ...

    async def save(self, entity: M) -> M:
        """保存实体（新增或更新）。"""
        ...

    async def update(self, entity: M, **values: Any) -> M:
        """更新实体指定字段。"""
        ...

    async def delete(self, entity: M) -> None:
        """删除实体。"""
        ...

    async def exists(self, **filters: Any) -> bool:
        """判断是否存在满足条件的实体。"""
        ...


class BaseRepository(IRepository[M]):
    """基于 SQLAlchemy AsyncSession 的仓储基类。

    通过构造函数注入 AsyncSession 和 model_class，
    提供通用的 CRUD 操作。子类可重写 _build_filters 实现自定义过滤。

    Attributes:
        db: 异步数据库会话
        model_class: ORM 模型类
    """

    def __init__(self, db: AsyncSession, model_class: type[M]) -> None:
        self.db = db
        self.model_class = model_class

    async def find_by_id(self, id: str) -> M | None:
        """根据主键 ID 查询实体。

        Args:
            id: 实体主键

        Returns:
            实体对象，不存在则返回 None
        """
        result = await self.db.execute(
            select(self.model_class).where(self.model_class.id == id)
        )
        return result.scalar_one_or_none()

    async def find_all(
        self,
        *filters: Any,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[M], int]:
        """分页查询实体列表。

        Args:
            *filters: SQLAlchemy 过滤表达式（如 Model.name == "foo"）
            offset: 偏移量
            limit: 每页条数

        Returns:
            (实体列表, 总数) 元组
        """
        query = select(self.model_class)
        for f in filters:
            query = query.where(f)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        result = await self.db.execute(query.offset(offset).limit(limit))
        items = list(result.scalars().all())

        return items, total

    async def save(self, entity: M) -> M:
        """保存实体（新增或更新）。

        将实体加入会话并 flush 到数据库，刷新获取服务端生成的字段值。
        注意：不执行 commit，由外层统一事务管理。

        Args:
            entity: 待保存的实体对象

        Returns:
            保存后的实体（含服务端生成的字段）
        """
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def update(self, entity: M, **values: Any) -> M:
        """更新实体指定字段。

        Args:
            entity: 待更新的实体对象
            **values: 需更新的字段键值对

        Returns:
            更新后的实体
        """
        for key, value in values.items():
            setattr(entity, key, value)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def delete(self, entity: M) -> None:
        """删除实体。

        Args:
            entity: 待删除的实体对象
        """
        await self.db.delete(entity)
        await self.db.flush()

    async def exists(self, **filters: Any) -> bool:
        """判断是否存在满足条件的实体。

        Args:
            **filters: 字段键值对，转为等值条件

        Returns:
            存在返回 True，否则 False
        """
        query = select(self.model_class).limit(1)
        query = self._build_filters(query, **filters)
        result = await self.db.execute(query)
        return result.scalars().first() is not None

    def _build_filters(self, query: Any, **filters: Any) -> Any:
        """构建查询条件（模板方法）。

        默认实现：将关键字参数转为等值条件（column == value）。
        子类可重写以实现自定义过滤逻辑（如模糊搜索、范围查询等）。

        Args:
            query: SQLAlchemy 查询对象
            **filters: 字段键值对

        Returns:
            添加了过滤条件的查询对象
        """
        for key, value in filters.items():
            column = getattr(self.model_class, key, None)
            if column is not None:
                query = query.where(column == value)
        return query
