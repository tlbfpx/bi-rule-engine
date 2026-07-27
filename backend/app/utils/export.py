"""数据导出工具 — Excel/CSV 导出"""
import os
import polars as pl
from loguru import logger
from app.config import get_settings

settings = get_settings()


def export_to_excel(df: pl.DataFrame, filename: str, stats: dict | None = None) -> str:
    """导出为 Excel 文件，包含数据和统计 sheet"""
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    filepath = os.path.join(settings.STORAGE_DIR, f"{filename}.xlsx")

    # Polars 写入主数据 sheet
    df.write_excel(filepath, worksheet="转换结果", autofit=True)

    # 如果提供了统计信息，追加统计 sheet
    if stats:
        import openpyxl
        wb = openpyxl.load_workbook(filepath)
        ws = wb.create_sheet("执行统计")
        ws.append(["字段名", "匹配数", "默认值数", "错误数"])
        for field, s in stats.items():
            ws.append([field, s.get("matched", 0), s.get("defaulted", 0), s.get("errors", 0)])
        wb.save(filepath)

    logger.info(f"导出 Excel: {filepath} ({len(df)} 行)")
    return filepath


def export_to_csv(df: pl.DataFrame, filename: str) -> str:
    """导出为 CSV 文件"""
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    filepath = os.path.join(settings.STORAGE_DIR, f"{filename}.csv")
    df.write_csv(filepath)
    logger.info(f"导出 CSV: {filepath} ({len(df)} 行)")
    return filepath
