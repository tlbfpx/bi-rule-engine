"""WebSocket 进度推送"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
import json

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[task_id] = websocket
        logger.info(f"WebSocket 连接: task={task_id}")

    def disconnect(self, task_id: str):
        self.active_connections.pop(task_id, None)
        logger.info(f"WebSocket 断开: task={task_id}")

    async def send_progress(self, task_id: str, data: dict):
        ws = self.active_connections.get(task_id)
        if ws:
            await ws.send_text(json.dumps(data, default=str))


manager = ConnectionManager()


@router.websocket("/tasks/{task_id}/progress")
async def task_progress(websocket: WebSocket, task_id: str):
    await manager.connect(task_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(task_id)
