"""规则处理器 — 策略模式，每类规则类型独立实现。

新增规则类型只需：1) 实现 RuleHandler 协议 2) 注册到 RULE_HANDLER_REGISTRY。
条件评估统一委托给 operators.evaluate_condition，消除 executor 中的重复实现。
"""
import polars as pl
from typing import Protocol, TYPE_CHECKING

from app.engine.parser import RuleConfig, ConditionGroup
from app.engine.constants import RuleType, DefaultResult
from app.engine.operators import evaluate_condition
from app.engine.result_resolvers import RESULT_RESOLVER_REGISTRY
from app.engine.cleaning_steps import CLEANING_STEP_REGISTRY

if TYPE_CHECKING:
    from app.engine.executor import RuleExecutionStats


# ───────────────────────── 条件评估工具函数 ─────────────────────────


def _evaluate_condition_row(df: pl.DataFrame, row) -> pl.Series:
    """评估单行条件 — 统一委托给 operators.evaluate_condition。列不存在返回全 False。"""
    col = row.field
    if col not in df.columns:
        return pl.Series("_empty", [False] * len(df))
    return evaluate_condition(df[col], row.operator, row.value)


def evaluate_condition_group(df: pl.DataFrame, cg: ConditionGroup) -> pl.Series:
    """评估条件组 — AND: 初始 True, OR: 初始 False，逐行组合后返回布尔 mask"""
    initial = True if cg.logic == "AND" else False
    mask = pl.Series("_mask", [initial] * len(df))
    for row in cg.rows:
        row_mask = _evaluate_condition_row(df, row)
        if cg.logic == "AND":
            mask = mask & row_mask
        else:
            mask = mask | row_mask
    return mask


# ───────────────────────── 规则处理器 ─────────────────────────


class RuleHandler(Protocol):
    """规则处理器协议 — (DataFrame, RuleConfig, lookup_tables, stats) → 新 DataFrame"""

    def execute(
        self,
        df: pl.DataFrame,
        rule: RuleConfig,
        lookup_tables: dict[str, dict],
        stats: "RuleExecutionStats",
    ) -> pl.DataFrame: ...


class MappingHandler:
    """条件映射 — 按优先级评估多组条件，命中后赋值；支持 keep_original 默认值"""

    def execute(self, df, rule, lookup_tables, stats):
        target = rule.field_name

        original_exists = target in df.columns
        if original_exists:
            original_values = df[target].clone()
        else:
            df = df.with_columns(pl.lit(None).alias(target))
            original_values = None

        matched_count = 0
        sorted_conditions = sorted(rule.conditions, key=lambda c: c.priority)
        not_matched = pl.Series("_nm", [True] * len(df))

        for cg in sorted_conditions:
            mask = evaluate_condition_group(df, cg)
            mask = mask.fill_null(False)
            mask = mask & not_matched

            result_value = RESULT_RESOLVER_REGISTRY.get(
                cg.result_type, lambda _df, _cg: pl.lit(None)
            )(df, cg)

            df = df.with_columns(
                pl.when(mask)
                .then(result_value)
                .otherwise(pl.col(target))
                .alias(target)
            )

            matched_count += int(mask.sum())
            not_matched = not_matched & ~mask

        # 处理默认值
        default_val = rule.default_result
        defaulted_count = 0
        if default_val is not None and default_val != DefaultResult.KEEP_ORIGINAL:
            df = df.with_columns(
                pl.when(not_matched)
                .then(pl.lit(default_val))
                .otherwise(pl.col(target))
                .alias(target)
            )
            defaulted_count = int(not_matched.sum())
        elif default_val == DefaultResult.KEEP_ORIGINAL and original_values is not None:
            df = df.with_columns(
                pl.when(not_matched)
                .then(original_values)
                .otherwise(pl.col(target))
                .alias(target)
            )
            defaulted_count = int(not_matched.sum())
        else:
            defaulted_count = int(not_matched.sum())

        stats.record(rule.field_name, matched=matched_count, defaulted=defaulted_count, errors=0)
        return df


class CleaningHandler:
    """数据清洗 — 按顺序执行清洗步骤，委托给 CLEANING_STEP_REGISTRY"""

    def execute(self, df, rule, lookup_tables, stats):
        target = rule.field_name
        if target not in df.columns:
            return df

        for step in rule.cleaning_steps:
            action = step.get("action")
            handler = CLEANING_STEP_REGISTRY.get(action)
            if handler:
                df = handler.execute(df, target, step)

        stats.record(rule.field_name, matched=len(df), defaulted=0, errors=0)
        return df


class LookupHandler:
    """字典查找 — 根据 key_field 查 lookup_table，按优先级回退"""

    def execute(self, df, rule, lookup_tables, stats):
        target = rule.field_name
        key_field = rule.lookup_key_field
        lookup_data = lookup_tables.get(rule.lookup_table_id, {})

        if target not in df.columns:
            df = df.with_columns(pl.lit(None).alias(target))

        if key_field and key_field in df.columns and lookup_data:
            def do_lookup(key):
                if key is None:
                    return None
                # 规范化 key：数值型去掉末尾 ".0" 以匹配 JSON 字符串 key
                key_str = str(key)
                if key_str.endswith(".0") and key_str.replace(".", "", 1).lstrip("-").isdigit():
                    key_str = key_str[:-2]
                return lookup_data.get(key_str)

            df = df.with_columns(
                pl.col(key_field).map_elements(do_lookup, return_dtype=pl.Utf8).alias(target)
            )

        # 回退条件 — 统一使用 operators.evaluate_condition
        not_matched = df[target].is_null()
        for fb in rule.lookup_fallbacks:
            cond = fb.get("condition", {})
            cond_field = cond.get("field") or fb.get("condition_field")
            cond_op = cond.get("operator") or fb.get("condition_operator")
            cond_val = cond.get("value") or fb.get("condition_value")
            fallback_val = fb.get("value") or fb.get("fallback_value")

            if cond_field and cond_field in df.columns:
                mask = evaluate_condition(df[cond_field], cond_op, cond_val)
                mask = mask & not_matched
                df = df.with_columns(
                    pl.when(mask)
                    .then(pl.lit(fallback_val))
                    .otherwise(pl.col(target))
                    .alias(target)
                )
                not_matched = not_matched & ~mask

        matched = len(df) - int(not_matched.sum())
        stats.record(rule.field_name, matched=matched, defaulted=int(not_matched.sum()), errors=0)
        return df


class ComputedHandler:
    """公式计算 — 委托给 formula_engine 编译执行"""

    def execute(self, df, rule, lookup_tables, stats):
        target = rule.field_name
        formula = rule.formula_expression

        if not formula:
            stats.record(rule.field_name, matched=0, defaulted=0, errors=len(df))
            return df

        try:
            from app.engine.formula_engine import evaluate_formula

            result = evaluate_formula(df, formula)
            df = df.with_columns(result.alias(target))
            stats.record(rule.field_name, matched=len(df), defaulted=0, errors=0)
        except ValueError as e:
            # 公式语法/编译错误 — 记录到统计但��静默吞
            from loguru import logger

            logger.opt(exception=True).error(f"公式编译失败 [{rule.field_name}]: {e}")
            df = df.with_columns(pl.lit(None).alias(target) if target not in df.columns else df[target])
            stats.record(rule.field_name, matched=0, defaulted=0, errors=len(df))
        except Exception:
            from loguru import logger

            logger.opt(exception=True).error(f"公式执行异常 [{rule.field_name}]")
            df = df.with_columns(pl.lit(None).alias(target) if target not in df.columns else df[target])
            stats.record(rule.field_name, matched=0, defaulted=0, errors=len(df))
        return df


# ───────────────────────── 注册表 ─────────────────────────

RULE_HANDLER_REGISTRY: dict[str, RuleHandler] = {
    RuleType.MAPPING: MappingHandler(),
    RuleType.CLEANING: CleaningHandler(),
    RuleType.LOOKUP: LookupHandler(),
    RuleType.COMPUTED: ComputedHandler(),
}
