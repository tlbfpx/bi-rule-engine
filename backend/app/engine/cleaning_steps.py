"""清洗步骤处理器 — 策略模式，每类清洗动作独立实现。

新增清洗动作只需：1) 实现 CleaningStepHandler 协议 2) 注册到 CLEANING_STEP_REGISTRY。
"""
import polars as pl
from typing import Protocol
from app.engine.constants import CleaningAction
from app.engine.operators import evaluate_condition


class CleaningStepHandler(Protocol):
    """清洗步骤处理器协议 — (DataFrame, 目标列名, 步骤配置) → 新 DataFrame"""

    def execute(self, df: pl.DataFrame, target: str, step: dict) -> pl.DataFrame: ...


class FillNullStep:
    """填充空值 — 支持从其他列填充或用固定值填充"""

    def execute(self, df: pl.DataFrame, target: str, step: dict) -> pl.DataFrame:
        source_field = step.get("source_field")
        fill_val = step.get("value") or (step.get("params") or {}).get("fill_value")

        if source_field and source_field in df.columns:
            df = df.with_columns(
                pl.col(target).fill_null(pl.col(source_field)).alias(target)
            )
            df = df.with_columns(
                pl.when(pl.col(target).cast(pl.Utf8) == "")
                .then(pl.col(source_field))
                .otherwise(pl.col(target))
                .alias(target)
            )
        else:
            df = df.with_columns(
                pl.col(target).fill_null(pl.lit(fill_val)).alias(target)
            )
            df = df.with_columns(
                pl.when(pl.col(target).cast(pl.Utf8) == "")
                .then(pl.lit(fill_val))
                .otherwise(pl.col(target))
                .alias(target)
            )
        return df


class ReplaceStep:
    """条件替换 — 满足条件时用指定值替��目标列"""

    def execute(self, df: pl.DataFrame, target: str, step: dict) -> pl.DataFrame:
        condition = step.get("condition", {})
        cond_field = condition.get("field")
        cond_op = condition.get("operator")
        cond_val = condition.get("value")
        replacement = step.get("replacement")

        # is_null/is_not_null 在目标列上评估，其余操作符在 cond_field 上评估
        if cond_op in ("is_null", "is_not_null"):
            eval_field = target
        elif cond_field and cond_field in df.columns:
            eval_field = cond_field
        else:
            return df

        mask = evaluate_condition(df[eval_field], cond_op, cond_val)
        return df.with_columns(
            pl.when(mask).then(pl.lit(replacement)).otherwise(pl.col(target)).alias(target)
        )


class TrimStep:
    """去除首尾空白"""

    def execute(self, df: pl.DataFrame, target: str, step: dict) -> pl.DataFrame:
        return df.with_columns(
            pl.col(target).cast(pl.Utf8).str.strip_chars().alias(target)
        )


class RegexExtractStep:
    """正则提取"""

    def execute(self, df: pl.DataFrame, target: str, step: dict) -> pl.DataFrame:
        pattern = step.get("pattern", "")
        group = step.get("group", 0)
        return df.with_columns(
            pl.col(target).cast(pl.Utf8).str.extract(pattern, group).alias(target)
        )


class SubstringStep:
    """子串截取"""

    def execute(self, df: pl.DataFrame, target: str, step: dict) -> pl.DataFrame:
        start = step.get("start", 0)
        length = step.get("length")
        if length:
            return df.with_columns(
                pl.col(target).cast(pl.Utf8).str.slice(start, length).alias(target)
            )
        return df


# ───────────────────────── 注册表 ─────────────────────────

CLEANING_STEP_REGISTRY: dict[str, CleaningStepHandler] = {
    CleaningAction.FILL_NULL: FillNullStep(),
    CleaningAction.REPLACE: ReplaceStep(),
    CleaningAction.TRIM: TrimStep(),
    CleaningAction.REGEX_EXTRACT: RegexExtractStep(),
    CleaningAction.SUBSTRING: SubstringStep(),
}
