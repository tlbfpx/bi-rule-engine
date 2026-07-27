"""
企业级日志系统模块

功能：
1. trace_id 管理（contextvars，异步安全）
2. 结构化 JSON 日志（通过 patcher 注入）
3. 分级日志文件（access / error / app）
4. setup_logging 一键初始化
"""
import contextvars
import json
import os
import sys
import uuid

from loguru import logger

# ── trace_id 上下文变量（每个请求/任务独立） ──
_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trace_id", default=""
)


def generate_trace_id() -> str:
    """生成 16 位十六进制 trace_id，足够唯一且节省空间"""
    return uuid.uuid4().hex[:16]


def get_trace_id() -> str:
    """获取当前上下文的 trace_id"""
    return _trace_id_var.get()


def set_trace_id(trace_id: str) -> None:
    """设置当前上下文的 trace_id"""
    _trace_id_var.set(trace_id)


def _build_json_patcher(record: "loguru.Record") -> None:
    """
    loguru patcher：注入结构化字段，并将整条日志预序列化为 JSON。
    这样 handler 只需用 format="{extra[json_line]}" 即可输出 JSON 行。
    """
    # 注入追踪字段
    record["extra"]["trace_id"] = get_trace_id()
    record["extra"]["module_name"] = record["name"]

    # 构建 JSON 条目
    ts = record["time"]
    timestamp = ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond // 1000:03d}Z"

    entry = {
        "timestamp": timestamp,
        "level": record["level"].name,
        "trace_id": record["extra"].get("trace_id", ""),
        "module": record["extra"].get("module_name", record["name"]),
        "function": record["function"],
        "line": record["line"],
        "message": record["message"],
    }

    # 异常信息
    if record["exception"]:
        entry["exception"] = str(record["exception"])

    record["extra"]["json_line"] = json.dumps(entry, ensure_ascii=False, default=str)


def _make_access_filter():
    """访问日志过滤器：只匹配 log_type == 'access' 的记录"""
    def _filter(record):
        return record["extra"].get("log_type") == "access"
    return _filter


def _make_app_filter():
    """业务日志过滤器：排除 access 类型的记录"""
    def _filter(record):
        return record["extra"].get("log_type") != "access"
    return _filter


def setup_logging(settings) -> None:
    """
    初始化日志系统，替代原有的简单 logger.add() 配置。

    日志文件：
    - access.log: HTTP 访问日志（JSON 行格式）
    - error.log: ERROR 及以上级别（JSON 行格式）
    - app.log: 所有业务日志（JSON 行格式）
    """
    # 确保日志目录存在
    os.makedirs(settings.LOG_DIR, exist_ok=True)

    # 移除 loguru 默认 handler
    logger.remove()

    # 全局 patcher（在添加 handler 之前配置）
    logger.configure(patcher=_build_json_patcher)

    # 开发环境：控制台彩色输出
    if settings.DEBUG:
        logger.add(
            sys.stderr,
            level=settings.LOG_LEVEL,
            format=(
                "<green>{time:HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{extra[trace_id]}</cyan> | "
                "{name}:{function}:{line} | "
                "{message}"
            ),
        )

    # 访问日志（仅 access 类型）
    logger.add(
        os.path.join(settings.LOG_DIR, "access.log"),
        level="INFO",
        filter=_make_access_filter(),
        format="{extra[json_line]}",
        rotation=settings.LOG_ACCESS_ROTATION,
        retention=settings.LOG_ACCESS_RETENTION,
        enqueue=True,
    )

    # 错误日志（ERROR 及以上）
    logger.add(
        os.path.join(settings.LOG_DIR, "error.log"),
        level="ERROR",
        format="{extra[json_line]}",
        rotation=settings.LOG_ERROR_ROTATION,
        retention=settings.LOG_ERROR_RETENTION,
        enqueue=True,
    )

    # 业务日志（非 access 类型，默认级别）
    logger.add(
        os.path.join(settings.LOG_DIR, "app.log"),
        level=settings.LOG_LEVEL,
        filter=_make_app_filter(),
        format="{extra[json_line]}",
        rotation=settings.LOG_APP_ROTATION,
        retention=settings.LOG_APP_RETENTION,
        enqueue=True,
    )

    logger.info(
        "日志系统已初始化: level={}, dir={}",
        settings.LOG_LEVEL,
        settings.LOG_DIR,
    )
