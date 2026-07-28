"""规则执行器 — 核心引擎，对 DataFrame 执行规则转换"""
import math
import polars as pl
from typing import Any
from loguru import logger
from app.engine.parser import RuleConfig, ConditionGroup
from app.engine.dependency import topological_sort


class RuleExecutionStats:
    """规则执行统计"""

    def __init__(self):
        self.field_stats: dict[str, dict] = {}

    def record(self, field: str, matched: int, defaulted: int, errors: int):
        self.field_stats[field] = {
            "matched": matched,
            "defaulted": defaulted,
            "errors": errors,
        }

    def to_dict(self) -> dict:
        return self.field_stats


class RuleExecutor:
    """规则执行器"""

    def __init__(self, rules: list[RuleConfig], lookup_tables: dict[str, dict] | None = None):
        self.rules = [r for r in rules if r.enabled]
        self.lookup_tables = lookup_tables or {}
        self.stats = RuleExecutionStats()

    def execute(self, df: pl.DataFrame) -> tuple[pl.DataFrame, RuleExecutionStats]:
        """执行所有规则"""
        if not self.rules:
            logger.warning("没有启用的规则，返回原始数据")
            return df, self.stats

        try:
            levels = topological_sort(self.rules)
            logger.info(f"规则执行顺序: {len(levels)} 层, 共 {len(self.rules)} 条规则")
            for i, level in enumerate(levels):
                logger.info(f"  Level {i}: {[r.field_name for r in level]}")
        except Exception as e:
            logger.error(f"依赖分析失败: {e}")
            raise

        df = df.with_columns(
            pl.lit(False).alias("_error_flag"),
            pl.lit("").alias("_error_msg"),
        )

        for level in levels:
            for rule in level:
                df = self._execute_rule(df, rule)

        return df, self.stats

    def _execute_rule(self, df: pl.DataFrame, rule: RuleConfig) -> pl.DataFrame:
        logger.debug(f"执行规则: {rule.field_name} ({rule.rule_type})")

        if rule.rule_type == "mapping":
            return self._execute_mapping(df, rule)
        elif rule.rule_type == "cleaning":
            return self._execute_cleaning(df, rule)
        elif rule.rule_type == "lookup":
            return self._execute_lookup(df, rule)
        elif rule.rule_type == "computed":
            return self._execute_computed(df, rule)
        else:
            logger.warning(f"未知规则类型: {rule.rule_type}")
            return df

    # ─── 条件映射 ───────────────────────────────────────────

    def _execute_mapping(self, df: pl.DataFrame, rule: RuleConfig) -> pl.DataFrame:
        target = rule.field_name
        # 记录原始值（用于 keep_original 回退）
        original_exists = target in df.columns
        if original_exists:
            original_values = df[target].clone()
        if not original_exists:
            df = df.with_columns(pl.lit(None).alias(target))
            original_values = None

        matched_count = 0
        sorted_conditions = sorted(rule.conditions, key=lambda c: c.priority)
        not_matched = pl.Series("_nm", [True] * len(df))

        for cg in sorted_conditions:
            mask = self._evaluate_condition_group(df, cg)
            # null → false，避免 null 传播导致 not_matched 变 null
            mask = mask.fill_null(False)
            mask = mask & not_matched

            result_value = self._resolve_result(df, cg)

            df = df.with_columns(
                pl.when(mask)
                .then(result_value)
                .otherwise(pl.col(target))
                .alias(target)
            )

            matched_count += mask.sum()
            not_matched = not_matched & ~mask

        default_val = rule.default_result
        defaulted_count = 0
        if default_val is not None and default_val != "keep_original":
            df = df.with_columns(
                pl.when(not_matched)
                .then(pl.lit(default_val))
                .otherwise(pl.col(target))
                .alias(target)
            )
            defaulted_count = not_matched.sum()
        elif default_val == "keep_original" and original_values is not None:
            # 恢复原始值（未被任何条件命中的行保持输入值）
            df = df.with_columns(
                pl.when(not_matched)
                .then(original_values)
                .otherwise(pl.col(target))
                .alias(target)
            )
            defaulted_count = not_matched.sum()
        else:
            defaulted_count = not_matched.sum()

        self.stats.record(rule.field_name, matched=matched_count, defaulted=defaulted_count, errors=0)
        return df

    def _evaluate_condition_group(self, df: pl.DataFrame, cg: ConditionGroup) -> pl.Series:
        # AND: 初始 True (任何 False 都会让结果变 False)
        # OR:  初始 False (任何 True 都会让结果变 True)
        initial = True if cg.logic == "AND" else False
        mask = pl.Series("_mask", [initial] * len(df))
        for row in cg.rows:
            row_mask = self._evaluate_condition_row(df, row)
            if cg.logic == "AND":
                mask = mask & row_mask
            else:
                mask = mask | row_mask
        return mask

    def _evaluate_condition_row(self, df: pl.DataFrame, row) -> pl.Series:
        col = row.field
        if col not in df.columns:
            return pl.Series("_empty", [False] * len(df))

        col_series = df[col]
        op = row.operator
        val = row.value

        if op == "is_null":
            return col_series.is_null() | (col_series.cast(pl.Utf8) == "")
        if op == "is_not_null":
            return ~(col_series.is_null() | (col_series.cast(pl.Utf8) == ""))
        if op == "eq":
            return col_series.cast(pl.Utf8) == str(val)
        if op == "neq":
            return col_series.cast(pl.Utf8) != str(val)
        if op == "contains":
            return col_series.cast(pl.Utf8).str.contains(str(val), literal=True)
        if op == "not_contains":
            return ~col_series.cast(pl.Utf8).str.contains(str(val), literal=True)
        if op == "matches":
            return col_series.cast(pl.Utf8).str.contains(str(val))
        if op == "starts_with":
            return col_series.cast(pl.Utf8).str.starts_with(str(val))
        if op == "ends_with":
            return col_series.cast(pl.Utf8).str.ends_with(str(val))
        if op in ("gt", "gte", "lt", "lte"):
            num_col = col_series.cast(pl.Float64, strict=False)
            v = float(val)
            if op == "gt":
                return num_col > v
            if op == "gte":
                return num_col >= v
            if op == "lt":
                return num_col < v
            if op == "lte":
                return num_col <= v
        if op == "in":
            if isinstance(val, list):
                vals = val
            elif isinstance(val, str) and "," in val:
                vals = [v.strip() for v in val.split(",")]
            else:
                vals = [val]
            return col_series.cast(pl.Utf8).is_in([str(v) for v in vals])
        if op == "between":
            lo, hi = (val[0], val[1]) if isinstance(val, (list, tuple)) else (val, val)
            num_col = col_series.cast(pl.Float64, strict=False)
            return (num_col >= float(lo)) & (num_col <= float(hi))

        return pl.Series("_unknown", [False] * len(df))

    def _resolve_result(self, df: pl.DataFrame, cg: ConditionGroup) -> pl.Expr | pl.Series:
        if cg.result_type == "constant":
            return pl.lit(cg.result_value)
        elif cg.result_type == "field_value":
            if cg.result_value in df.columns:
                return pl.col(cg.result_value)
            return pl.lit(cg.result_value)
        elif cg.result_type == "null":
            return pl.lit(None)
        return pl.lit(None)

    # ─── 数据清洗 ───────────────────────────────────────────

    def _execute_cleaning(self, df: pl.DataFrame, rule: RuleConfig) -> pl.DataFrame:
        target = rule.field_name
        if target not in df.columns:
            return df

        for step in rule.cleaning_steps:
            action = step.get("action")

            if action == "fill_null":
                source_field = step.get("source_field")
                fill_val = step.get("value") or (step.get("params") or {}).get("fill_value")
                if source_field and source_field in df.columns:
                    # 填充 null
                    df = df.with_columns(
                        pl.col(target).fill_null(pl.col(source_field)).alias(target)
                    )
                    # 同时填充空字符串
                    df = df.with_columns(
                        pl.when(pl.col(target).cast(pl.Utf8) == "")
                        .then(pl.col(source_field))
                        .otherwise(pl.col(target))
                        .alias(target)
                    )
                else:
                    # 填充 null
                    df = df.with_columns(
                        pl.col(target).fill_null(pl.lit(fill_val)).alias(target)
                    )
                    # 同时填充空字符串
                    df = df.with_columns(
                        pl.when(pl.col(target).cast(pl.Utf8) == "")
                        .then(pl.lit(fill_val))
                        .otherwise(pl.col(target))
                        .alias(target)
                    )

            elif action == "replace":
                condition = step.get("condition", {})
                cond_field = condition.get("field")
                cond_op = condition.get("operator")
                cond_val = condition.get("value")
                replacement = step.get("replacement")

                if cond_op == "eq" and cond_field in df.columns:
                    mask = df[cond_field].cast(pl.Utf8) == str(cond_val)
                    df = df.with_columns(
                        pl.when(mask).then(pl.lit(replacement)).otherwise(pl.col(target)).alias(target)
                    )
                elif cond_op == "is_null":
                    mask = pl.col(target).is_null() | (pl.col(target).cast(pl.Utf8) == "")
                    df = df.with_columns(
                        pl.when(mask).then(pl.lit(replacement)).otherwise(pl.col(target)).alias(target)
                    )

            elif action == "trim":
                df = df.with_columns(
                    pl.col(target).cast(pl.Utf8).str.strip_chars().alias(target)
                )

            elif action == "regex_extract":
                pattern = step.get("pattern", "")
                group = step.get("group", 0)
                df = df.with_columns(
                    pl.col(target).cast(pl.Utf8).str.extract(pattern, group).alias(target)
                )

            elif action == "substring":
                start = step.get("start", 0)
                length = step.get("length")
                if length:
                    df = df.with_columns(
                        pl.col(target).cast(pl.Utf8).str.slice(start, length).alias(target)
                    )

        self.stats.record(rule.field_name, matched=len(df), defaulted=0, errors=0)
        return df

    # ─── 字典查找 ───────────────────────────────────────────

    def _execute_lookup(self, df: pl.DataFrame, rule: RuleConfig) -> pl.DataFrame:
        target = rule.field_name
        key_field = rule.lookup_key_field
        lookup_data = self.lookup_tables.get(rule.lookup_table_id, {})

        if target not in df.columns:
            df = df.with_columns(pl.lit(None).alias(target))

        if key_field and key_field in df.columns and lookup_data:
            def do_lookup(key):
                if key is None:
                    return None
                return lookup_data.get(str(key))

            df = df.with_columns(
                pl.col(key_field).map_elements(do_lookup, return_dtype=pl.Utf8).alias(target)
            )

        not_matched = df[target].is_null()
        for fb in rule.lookup_fallbacks:
            # 兼容两种格式：嵌套 condition 对象 或 扁平的 condition_field/condition_operator/condition_value
            cond = fb.get("condition", {})
            cond_field = cond.get("field") or fb.get("condition_field")
            cond_op = cond.get("operator") or fb.get("condition_operator")
            cond_val = cond.get("value") or fb.get("condition_value")
            fallback_val = fb.get("value") or fb.get("fallback_value")

            if cond_field and cond_field in df.columns:
                if cond_op == "eq":
                    mask = (df[cond_field].cast(pl.Utf8) == str(cond_val)) & not_matched
                elif cond_op == "is_null":
                    mask = (df[cond_field].is_null() | (df[cond_field].cast(pl.Utf8) == "")) & not_matched
                else:
                    continue
                df = df.with_columns(
                    pl.when(mask).then(pl.lit(fallback_val)).otherwise(pl.col(target)).alias(target)
                )
                not_matched = not_matched & ~mask

        matched = len(df) - not_matched.sum()
        self.stats.record(rule.field_name, matched=matched, defaulted=not_matched.sum(), errors=0)
        return df

    # ─── 公式计算 ───────────────────────────────────────────

    def _execute_computed(self, df: pl.DataFrame, rule: RuleConfig) -> pl.DataFrame:
        target = rule.field_name
        formula = rule.formula_expression

        if not formula:
            return df

        try:
            from app.engine.formula_engine import evaluate_formula
            result = evaluate_formula(df, formula)
            df = df.with_columns(result.alias(target))
        except Exception as e:
            logger.error(f"公式计算失败 [{rule.field_name}]: {e}")
            df = df.with_columns(pl.lit(None).alias(target))

        self.stats.record(rule.field_name, matched=len(df), defaulted=0, errors=0)
        return df
