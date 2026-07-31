"""规则管理应用服务 — Facade Pattern。

封装规则管理的完整用例：创建、查询、更新、删除、试跑。
通过 Repository 接口访问数据，不直接操作 HTTP 请求/响应（阿里规约）。

兼容性：旧 app/services/rule_service.py 的 test_rule 函数委托到本服务，
确保 API 层无需修改。
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import polars as pl
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.domain.value_objects import FieldName, RuleType
from app.engine.executor import RuleExecutor
from app.engine.parser import RuleParser
from app.models.lookup_table import LookupTable
from app.models.rule import Rule

__all__ = ["RuleRepository", "RuleService"]


# ───────────────────────── Repository 接口 ─────────────────────────


@runtime_checkable
class RuleRepository(Protocol):
    """规则仓储接口 — 定义规则持久化的抽象契约。

    所有数据库操作通过此接口，服务层不直接依赖 SQLAlchemy Session。
    """

    async def find_by_id(self, id: str) -> Rule | None:
        """根据 ID 查询规则。"""
        ...

    async def find_all(
        self,
        *conditions: Any,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Rule], int]:
        """分页查询规则列表，返回 (规则列表, 总数)。"""
        ...

    async def save(self, entity: Rule) -> Rule:
        """保存规则（新增或更新）。"""
        ...

    async def update(self, entity: Rule, **data: Any) -> Rule:
        """更新规则字段。"""
        ...

    async def delete(self, entity: Rule) -> None:
        """删除规则。"""
        ...


# ───────────────────────── Facade 服务 ─────────────────────────


class RuleService:
    """规则管理应用服务 — Facade Pattern。

    统一封装规则管理的业务用例，对外提供简洁接口，
    内部协调 Repository、值对象校验、规则引擎等组件。

    Attributes:
        rule_repo: 规则仓储实例
    """

    def __init__(self, rule_repo: RuleRepository) -> None:
        self.rule_repo = rule_repo

    async def create_rule(self, data: dict[str, Any]) -> Rule:
        """创建规则。

        流程：值对象校验 → 构建实体 → 保存 → 发布日志。

        Args:
            data: 规则字段字典，包含 field_name, rule_type, config 等

        Returns:
            创建后的 Rule 实体

        Raises:
            ValidationException: 字段名或规则类型不合法
        """
        # 值对象校验 — 构造即校验，失败抛 ValueError
        try:
            RuleType(data["rule_type"])
            FieldName(data["field_name"])
        except ValueError as e:
            raise ValidationException(detail=str(e)) from e

        entity = Rule(**data)
        result = await self.rule_repo.save(entity)
        logger.info(f"创建规则: {result.field_name} ({result.rule_type})")
        return result

    async def list_rules(
        self,
        page: int = 1,
        page_size: int = 20,
        **filters: Any,
    ) -> tuple[list[Rule], int]:
        """分页查询规则列表。

        Args:
            page: 页码（从 1 开始）
            page_size: 每页条数
            **filters: 过滤条件（field_name, rule_type, enabled, rule_set_id）

        Returns:
            (规则列表, 总数) 元组
        """
        offset = (page - 1) * page_size
        conditions = self._build_filter_conditions(filters)
        items, total = await self.rule_repo.find_all(
            *conditions, offset=offset, limit=page_size
        )
        return items, total

    async def get_rule(self, rule_id: str) -> Rule:
        """根据 ID 查询规则。

        Args:
            rule_id: 规则 ID

        Returns:
            Rule 实体

        Raises:
            NotFoundException: 规则不存在
        """
        rule = await self.rule_repo.find_by_id(rule_id)
        if rule is None:
            raise NotFoundException(detail=f"规则不存在: id={rule_id}")
        return rule

    async def update_rule(self, rule_id: str, data: dict[str, Any]) -> Rule:
        """更新规则。

        Args:
            rule_id: 规则 ID
            data: 需更新的字段字典

        Returns:
            更新后的 Rule 实体

        Raises:
            NotFoundException: 规则不存在
            ValidationException: 字段校验失败
        """
        # 如果更新了 field_name 或 rule_type，做值对象校验
        if "rule_type" in data:
            try:
                RuleType(data["rule_type"])
            except ValueError as e:
                raise ValidationException(detail=str(e)) from e
        if "field_name" in data:
            try:
                FieldName(data["field_name"])
            except ValueError as e:
                raise ValidationException(detail=str(e)) from e

        rule = await self.get_rule(rule_id)
        result = await self.rule_repo.update(rule, **data)
        logger.info(f"更新规则: {result.field_name}")
        return result

    async def delete_rule(self, rule_id: str) -> None:
        """删除规则。

        Args:
            rule_id: 规则 ID

        Raises:
            NotFoundException: 规则不存在
        """
        rule = await self.get_rule(rule_id)
        await self.rule_repo.delete(rule)
        logger.info(f"删除规则: {rule.field_name}")

    async def test_rule(
        self,
        rule_id: str,
        test_rows: list[dict[str, Any]],
        db: AsyncSession,
    ) -> dict[str, Any]:
        """对单条规则用测试数据试跑，返回逐行结果 + 汇总统计。

        迁移自 app/services/rule_service.py 的 test_rule 函数，
        逻辑保持完全兼容，但使用 BizException 替代 HTTPException。

        Args:
            rule_id: 规则 ID
            test_rows: 测试数据行列表
            db: 数据库会话（用于加载 LookupTable）

        Returns:
            包含 results（逐行结果）和 summary（汇总统计）的字典

        Raises:
            NotFoundException: 规则不存在
        """
        rule = await self.rule_repo.find_by_id(rule_id)
        if rule is None:
            raise NotFoundException(detail=f"规则不存在: id={rule_id}")

        rule_config = RuleParser.parse_rule(rule)

        # 构建测试 DataFrame：补全缺失的列
        df = pl.DataFrame(test_rows)
        missing_cols: set[str] = set()
        if rule_config.rule_type == "cleaning":
            if rule_config.field_name not in df.columns:
                missing_cols.add(rule_config.field_name)
        if rule_config.rule_type == "computed":
            if rule_config.field_name not in df.columns:
                missing_cols.add(rule_config.field_name)
            for dep in rule_config.depends_on:
                if dep not in df.columns:
                    missing_cols.add(dep)
        for dep in rule_config.depends_on:
            if dep not in df.columns:
                missing_cols.add(dep)

        for col in missing_cols:
            df = df.with_columns(pl.lit(None).alias(col))

        # 加载 lookup 表数据（lookup 类型规则需要）
        lt_result = await db.execute(select(LookupTable))
        lookup_tables = {str(t.id): t.data for t in lt_result.scalars().all()}

        executor = RuleExecutor([rule_config], lookup_tables)
        result_df, stats = executor.execute(df)
        field_stat = stats.to_dict().get(rule.field_name, {})

        # 确定每行的执行状态
        default_val = rule_config.default_result
        input_cols = list(test_rows[0].keys()) if test_rows else []

        results: list[dict[str, Any]] = []
        for i in range(len(result_df)):
            # 安全读取：computed 规则无 formula 时列可能未被创建
            if rule.field_name in result_df.columns:
                output_val = result_df[rule.field_name][i]
            else:
                output_val = None
            input_data: dict[str, Any] = {}
            for col in input_cols:
                if col in df.columns:
                    val = df[col][i]
                    input_data[col] = val if val is not None else None

            # 判断状态
            if field_stat.get("errors", 0) > 0 and i < field_stat["errors"]:
                status = "error"
            elif default_val is not None and str(output_val) == str(default_val):
                status = "defaulted"
            else:
                status = "matched"

            results.append({
                "row_index": i,
                "input_data": input_data,
                "output_value": output_val,
                "status": status,
            })

        return {
            "results": results,
            "summary": {
                "total": len(test_rows),
                "matched": field_stat.get("matched", 0),
                "defaulted": field_stat.get("defaulted", 0),
                "errors": field_stat.get("errors", 0),
            },
        }

    # ───────────────────────── 私有方法 ─────────────────────────

    @staticmethod
    def _build_filter_conditions(filters: dict[str, Any]) -> list[Any]:
        """将过滤条件字典转为 SQLAlchemy 等值表达式列表。

        Args:
            filters: 过滤条件键值对

        Returns:
            SQLAlchemy 表达式列表
        """
        conditions: list[Any] = []
        for key, value in filters.items():
            column = getattr(Rule, key, None)
            if column is not None and value is not None:
                # field_name 使用 ilike 模糊匹配
                if key == "field_name":
                    conditions.append(column.ilike(f"%{value}%"))
                else:
                    conditions.append(column == value)
        return conditions
