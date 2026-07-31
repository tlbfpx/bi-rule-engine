"""规则配置工厂 — Factory Pattern，统一 RuleConfig 的创建入口。

通过 FactoryRegistry 注册不同来源的解析策略（orm / dict），
新增来源只需注册新的工厂，无需修改本类（开闭原则）。
"""
from __future__ import annotations

from typing import Any

from app.patterns.factory import FactoryRegistry, IFactory
from app.engine.parser import RuleParser, RuleConfig


class _OrmRuleConfigFactory(IFactory[RuleConfig]):
    """从 ORM Rule 对象创建 RuleConfig 的工厂策略"""

    def create(self, **kwargs: Any) -> RuleConfig:
        rule_orm = kwargs["rule_orm"]
        return RuleParser.parse_rule(rule_orm)


class _DictRuleConfigFactory(IFactory[RuleConfig]):
    """从字典创建 RuleConfig 的工厂策略"""

    def create(self, **kwargs: Any) -> RuleConfig:
        data = kwargs["data"]
        return RuleParser.parse(data)


class RuleConfigFactory:
    """规则配置工厂 — 通过 FactoryRegistry 注册不同解析策略"""

    def __init__(self) -> None:
        self.registry: FactoryRegistry[RuleConfig] = FactoryRegistry()
        self.registry.register("orm", _OrmRuleConfigFactory())
        self.registry.register("dict", _DictRuleConfigFactory())

    def create_from_orm(self, rule_orm: Any) -> RuleConfig:
        """从 ORM Rule 对象创建 RuleConfig"""
        return self.registry.create("orm", rule_orm=rule_orm)

    def create_from_dict(self, data: dict) -> RuleConfig:
        """从字典创建 RuleConfig"""
        return self.registry.create("dict", data=data)
