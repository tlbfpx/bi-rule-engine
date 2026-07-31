"""输入校验服务 — Chain of Responsibility Pattern。

通过责任链模式将不同维度的校验逻辑解耦为独立的 Handler，
按顺序执行：规则类型 → 字段名 → 条件配置。

新增校验规则只需实现 IHandler 并注册到 ValidationChain，无需修改现有代码（开闭原则）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.patterns.chain import HandlerChain, IHandler

__all__ = [
    "ValidationContext",
    "ValidationResult",
    "ValidationChain",
    "RuleTypeValidator",
    "FieldNameValidator",
    "ConditionValidator",
]


# ───────────────────────── 校验上下文与结果 ─────────────────────────


@dataclass
class ValidationContext:
    """校验上下文 — 在责任链中传递的可变状态。

    Attributes:
        rule_type: 规则类型（mapping/cleaning/lookup/computed）
        config: 规则配置字典
        field_name: 规则目标字段名
        errors: 校验过程中收集的错误信息列表
    """

    rule_type: str
    config: dict
    field_name: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """是否校验通过（无错误）。"""
        return len(self.errors) == 0


@dataclass
class ValidationResult:
    """校验结果。

    Attributes:
        is_valid: 是否校验通过
        errors: 错误信息列表
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)


# ───────────────────────── 校验器 ─────────────────────────


class RuleTypeValidator(IHandler[ValidationContext]):
    """规则类型校验器 — 验证 rule_type 在白名单内。

    合法类型：mapping, cleaning, lookup, computed
    """

    _VALID_TYPES: frozenset[str] = frozenset({
        "mapping", "cleaning", "lookup", "computed",
    })

    def handle(self, context: ValidationContext) -> bool:
        """校验规则类型。

        Args:
            context: 校验上下文

        Returns:
            True（始终继续链，即使有错误也允许后续校验器运行）
        """
        if not context.rule_type:
            context.errors.append("规则类型不能为空")
        elif context.rule_type not in self._VALID_TYPES:
            context.errors.append(
                f"无效的规则类型: {context.rule_type}，"
                f"合法值: {sorted(self._VALID_TYPES)}"
            )
        return True


class FieldNameValidator(IHandler[ValidationContext]):
    """字段名校验器 — 验证 field_name 符合标识符规范。

    规则：字母或下划线开头，仅含字母、数字、下划线。
    防止 SQL 注入和非法列名。
    """

    _FIELD_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

    def handle(self, context: ValidationContext) -> bool:
        """校验字段名。

        Args:
            context: 校验上下文

        Returns:
            True（始终继续链）
        """
        if not context.field_name:
            context.errors.append("字段名不能为空")
        elif not self._FIELD_PATTERN.match(context.field_name):
            context.errors.append(
                f"无效的字段名: {context.field_name}，"
                f"需匹配 {self._FIELD_PATTERN.pattern}"
            )
        return True


class ConditionValidator(IHandler[ValidationContext]):
    """条件配置校验器 — 针对不同规则类型验证 config 结构。

    - mapping: 验证 conditions 结构（每组有 rows, result_type）
    - cleaning: 验证 cleaning_steps 结构（每步有 action）
    - lookup: 验证 lookup_table_id, lookup_key_field 存在
    - computed: 验证 formula_expression 非空
    """

    _REQUIRED_CONDITION_KEYS: frozenset[str] = frozenset({"rows", "result_type"})

    def handle(self, context: ValidationContext) -> bool:
        """根据规则类型校验配置结构。

        Args:
            context: 校验上下文

        Returns:
            True（始终继续链）
        """
        config = context.config
        rule_type = context.rule_type

        if rule_type == "mapping":
            self._validate_mapping(config, context)
        elif rule_type == "cleaning":
            self._validate_cleaning(config, context)
        elif rule_type == "lookup":
            self._validate_lookup(config, context)
        elif rule_type == "computed":
            self._validate_computed(config, context)

        return True

    def _validate_mapping(self, config: dict, context: ValidationContext) -> None:
        """校验 mapping 规则配置。"""
        conditions = config.get("conditions", [])
        if not conditions:
            context.errors.append("mapping 规则至少需要一个条件组")
            return

        for i, cg in enumerate(conditions):
            if not isinstance(cg, dict):
                context.errors.append(f"条件组 {i} 必须是字典")
                continue
            rows = cg.get("rows", [])
            if not rows:
                context.errors.append(f"条件组 {i} 至少需要一行条件")
            result_type = cg.get("result_type")
            if result_type and result_type not in ("constant", "field_value", "null"):
                context.errors.append(
                    f"条件组 {i} 的 result_type 无效: {result_type}"
                )

    def _validate_cleaning(self, config: dict, context: ValidationContext) -> None:
        """校验 cleaning 规则配置。"""
        steps = config.get("cleaning_steps", [])
        if not steps:
            context.errors.append("cleaning 规则至少需要一个清洗步骤")
            return

        valid_actions = {
            "fill_null", "replace", "trim", "regex_extract", "substring",
        }
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                context.errors.append(f"清洗步骤 {i} 必须是字典")
                continue
            action = step.get("action")
            if not action:
                context.errors.append(f"清洗步骤 {i} 缺少 action 字段")
            elif action not in valid_actions:
                context.errors.append(
                    f"清洗步骤 {i} 的 action 无效: {action}，"
                    f"合法值: {sorted(valid_actions)}"
                )

    def _validate_lookup(self, config: dict, context: ValidationContext) -> None:
        """校验 lookup 规则配置。"""
        if not config.get("lookup_table_id"):
            context.errors.append("lookup 规则必须指定 lookup_table_id")
        if not config.get("lookup_key_field"):
            context.errors.append("lookup 规则必须指定 lookup_key_field")

    def _validate_computed(self, config: dict, context: ValidationContext) -> None:
        """校验 computed 规则配置。"""
        formula = config.get("formula_expression")
        if not formula or not str(formula).strip():
            context.errors.append("computed 规则必须指定 formula_expression")


# ───────────────────────── 验证链 ─────────────────────────


class ValidationChain:
    """验证链 — Chain of Responsibility。

    注册标准校验器并按顺序执行。调用方也可添加自定义校验器。

    Usage:
        chain = ValidationChain()
        result = await chain.validate("mapping", config, "field_name")
        if not result.is_valid:
            raise ValidationException(detail=result.errors)
    """

    def __init__(self) -> None:
        self.chain: HandlerChain[ValidationContext] = HandlerChain()
        # 注册标准验证器
        self.chain.add_handler(RuleTypeValidator())
        self.chain.add_handler(FieldNameValidator())
        self.chain.add_handler(ConditionValidator())

    def add_handler(self, handler: IHandler[ValidationContext]) -> "ValidationChain":
        """添加自定义校验器到链尾。

        Args:
            handler: 校验器实例

        Returns:
            self，支持链式调用
        """
        self.chain.add_handler(handler)
        return self

    async def validate(
        self,
        rule_type: str,
        config: dict,
        field_name: str = "",
    ) -> ValidationResult:
        """执行校验链。

        Args:
            rule_type: 规则类型
            config: 规则配置字典
            field_name: 规则目标字段名

        Returns:
            校验结果 ValidationResult
        """
        context = ValidationContext(
            rule_type=rule_type,
            config=config,
            field_name=field_name,
        )
        self.chain.execute(context)
        return ValidationResult(
            is_valid=context.is_valid,
            errors=list(context.errors),
        )
