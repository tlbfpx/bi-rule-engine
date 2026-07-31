"""WebSocket 进度推送"""
import re
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from loguru import logger
import json

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
