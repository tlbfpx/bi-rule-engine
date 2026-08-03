"""WebSocket 进度推送"""
import re
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from loguru import logger
import json

from app.engine.observer import ETLProgressEvent
from app.engine.executor import get_default_event_bus
from app.patterns.observer import Event

router = APIRouter()

# task_id 格式校验（UUID v4）
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


class ConnectionManager:
    """WebSocket 连接管理器，支持同一 task_id 的多连接订阅。"""

    def __init__(self):
        self.active_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        conns = self.active_connections.setdefault(task_id, set())
        conns.add(websocket)
        logger.info(f"WebSocket 连接: task={task_id}, 当前连接数={len(conns)}")

    def disconnect(self, task_id: str, websocket: WebSocket):
        conns = self.active_connections.get(task_id)
        if conns:
            conns.discard(websocket)
            if not conns:
                del self.active_connections[task_id]
            logger.info(f"WebSocket 断开: task={task_id}, 剩余连接数={len(conns)}")

    async def send_progress(self, task_id: str, data: dict):
        """向该 task_id 的所有订阅连接广播进度。"""
        conns = self.active_connections.get(task_id)
        if not conns:
            return
        message = json.dumps(data, default=str)
        dead = []
        # 遍历 set 的快照副本，避免并发修改导致 RuntimeError
        for ws in list(conns):
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.debug(f"WebSocket 发送失败，将清理: {e}")
                dead.append(ws)
        # 清理已断开的连接
        for ws in dead:
            conns.discard(ws)
        if not conns:
            self.active_connections.pop(task_id, None)


manager = ConnectionManager()


class ETLProgressListener:
    """ETL 进度事件监听器 — 将 EventBus 事件转发到 WebSocket。

    EventBus 的 publish 是同步调用的（在工作线程中执行），
    因此这里用 asyncio.run_coroutine_threadsafe 把 async send_progress 投递回 event loop。
    """

    def __init__(self):
        self._loop = None

    def set_loop(self, loop):
        self._loop = loop

    def on_event(self, event: Event) -> None:
        if not isinstance(event, ETLProgressEvent):
            return
        if self._loop is None or not self._loop.is_running():
            return
        data = {
            "type": "etl_progress",
            "run_id": event.run_id,
            "job_id": event.job_id,
            "phase": event.phase,
            "message": event.message,
            "input_rows": event.input_rows,
            "output_rows": event.output_rows,
            "progress": event.progress,
        }
        asyncio_future = asyncio.run_coroutine_threadsafe(
            manager.send_progress(event.run_id, data),
            self._loop,
        )
        # 设置短超时，防止 WS 发送阻塞工作线程
        try:
            asyncio_future.result(timeout=5)
        except Exception as e:
            logger.debug(f"WS 进度转发失败 [run={event.run_id}]: {e}")


_progress_listener = ETLProgressListener()


def init_progress_listener(loop) -> None:
    """在应用启动时注册 EventBus 监听器。应在 lifespan 中调用。"""
    import asyncio
    _progress_listener.set_loop(loop)
    bus = get_default_event_bus()
    bus.subscribe("etl_progress", _progress_listener)
    logger.info("ETL 进度事件监听器已注册")


@router.websocket("/tasks/{task_id}/progress")
async def task_progress(
    websocket: WebSocket,
    task_id: str,
    token: str | None = Query(default=None),
):
    # 校验 task_id 格式（UUID），防止恶意枚举
    if not _UUID_RE.match(task_id):
        await websocket.close(code=1008, reason="无效的 task_id")
        return

    # TODO: 生产环境应校验 token 或 cookie，确认用户有权查看该 task
    # 当前阶段仅做格式校验，后续接入认证后在此处验证

    await manager.connect(task_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)
