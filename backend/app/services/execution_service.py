"""执行服务 — 把 DataFrame 跑过全部启用规则并落库为 ExecutionTask。

文件读取（CSV/XLSX → df）属 HTTP 关注点，留在路由；此处只负责业务执行。
"""
import time
import polars as pl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule
from app.models.lookup_table import LookupTable
from app.models.task import ExecutionTask
from app.engine.parser import RuleParser
from app.engine.executor import RuleExecutor


async def execute_dataframe(
    db: AsyncSession,
    df: pl.DataFrame,
    source_name: str,
) -> dict:
    """对 DataFrame 跑全部启用规则，落 ExecutionTask，返回结果摘要 + 预览。"""
    start_time = time.time()
    input_rows = len(df)

    rules_result = await db.execute(
        select(Rule).where(Rule.enabled == True).order_by(Rule.priority.asc())  # noqa: E712
    )
    rules = rules_result.scalars().all()
    lt_result = await db.execute(select(LookupTable))
    lookup_tables = {str(t.id): t.data for t in lt_result.scalars().all()}

    rule_configs = [RuleParser.parse(r.to_dict()) for r in rules]
    executor = RuleExecutor(rule_configs, lookup_tables)
    result_df, stats = executor.execute(df)

    duration_ms = int((time.time() - start_time) * 1000)

    task = ExecutionTask(
        task_name=source_name,
        status="completed",
        input_rows=input_rows,
        output_rows=len(result_df),
        stats=stats.to_dict(),
        duration_ms=duration_ms,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    return {
        "task_id": str(task.id),
        "status": "completed",
        "input_rows": input_rows,
        "output_rows": len(result_df),
        "error_rows": 0,
        "stats": stats.to_dict(),
        "duration_ms": duration_ms,
        "preview_rows": result_df.head(20).to_dicts(),
        "columns": result_df.columns,
    }
