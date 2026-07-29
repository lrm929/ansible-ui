import asyncio
import json
import threading
from typing import Dict, Optional, Set

from fastapi import WebSocket


class WebSocketManager:
    """task_id -> WebSocket 集合,支持从工作线程安全广播。"""

    def __init__(self):
        self._connections: Dict[int, Set[WebSocket]] = {}
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    async def connect(self, task_id: int, websocket: WebSocket):
        await websocket.accept()
        with self._lock:
            self._connections.setdefault(task_id, set()).add(websocket)

    def disconnect(self, task_id: int, websocket: WebSocket):
        with self._lock:
            conns = self._connections.get(task_id)
            if conns is not None:
                conns.discard(websocket)
                if not conns:
                    self._connections.pop(task_id, None)

    async def _send_async(self, task_id: int, message: dict):
        with self._lock:
            conns = list(self._connections.get(task_id, set()))
        if not conns:
            return
        text = json.dumps(message, ensure_ascii=False)
        dead = []
        for ws in conns:
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(task_id, ws)

    async def _close_all_async(self, task_id: int):
        with self._lock:
            conns = list(self._connections.pop(task_id, set()))
        for ws in conns:
            try:
                await ws.close()
            except Exception:
                pass

    def _run_coro(self, coro):
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        try:
            asyncio.run_coroutine_threadsafe(coro, loop)
        except RuntimeError:
            pass

    def broadcast(self, task_id: int, message: dict):
        """线程安全广播:可从任意线程调用。"""
        self._run_coro(self._send_async(task_id, message))

    def broadcast_log(self, task_id: int, line: str):
        self.broadcast(task_id, {"type": "log", "line": line})

    def broadcast_end(self, task_id: int, status: str):
        self.broadcast(task_id, {"type": "status", "status": status})
        self.broadcast(task_id, {"type": "end"})
        # 任务结束后由服务端关闭连接
        self._run_coro(self._close_all_async(task_id))


ws_manager = WebSocketManager()
