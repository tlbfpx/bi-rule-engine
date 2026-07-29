"""规则领域服务 — 从 API 路由下沉的业务逻辑。

路由层只做参数解析与 HTTP 关注点，业务逻辑集中于此，便于复用与单测。
"""
import polars as pl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.rule import Rule
from app.models.lookup_table import LookupTable
from app.engine.parser import RuleParser
from app.engine.executor import RuleExecutor


async def test_rule(db: AsyncSession, rule_id: str, test_rows: list[dict]) -> dict:
    """对单条规则用测试数据试跑，返回逐行结果 + 汇总统计。"""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    rule_config = RuleParser.parse_rule(rule)

    # 构建测试 DataFrame：补全缺失的列（cleaning 目标列 / computed 依赖列和输出列）
    df = pl.DataFrame(test_rows)
    missing_cols = set()
    if rule_config.rule_type == "cleaning":
        if rule_config.field_name not in df.columns:
            missing_cols.add(rule_config.field_name)
    if rule_config.rule_type == "computed":
        if rule_config.field_name not in df.columns:
            missing_cols.add(rule_config.field_name)
        for dep in rule_config.depends_on:
            if dep not in df.columns:
                missing_cols.add(dep)
    # 通用：所有依赖列
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

    results = []
    for i in range(len(result_df)):
        # 安全读取：computed 规则无 formula 时列可能未被创建
        if rule.field_name in result_df.columns:
            output_val = result_df[rule.field_name][i]
        else:
            output_val = None
        input_data = {}
        for col in input_cols:
            if col in df.columns:
                val = df[col][i]
                # Polars null → Python None
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
