import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_mongodb
from app.core.dependencies import get_ws_user

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, channel: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(channel, []).append(ws)

    def disconnect(self, channel: str, ws: WebSocket):
        if channel in self.active:
            self.active[channel] = [w for w in self.active[channel] if w != ws]

    async def broadcast(self, channel: str, data: dict):
        connections = self.active.get(channel, [])
        dead = []
        for ws in connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(channel, ws)


manager = ConnectionManager()


@router.websocket("/ws/dashboard")
async def ws_dashboard(
    websocket: WebSocket,
    token: str | None = Query(None),
    api_key: str | None = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    try:
        user = await get_ws_user(token=token, api_key=api_key, db=db)
    except Exception:
        await websocket.close(code=4001)
        return

    await manager.connect("dashboard", websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Heartbeat / ping
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect("dashboard", websocket)


@router.websocket("/ws/agents/{agent_id}/logs")
async def ws_agent_logs(
    websocket: WebSocket,
    agent_id: str,
    token: str | None = Query(None),
    api_key: str | None = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    try:
        user = await get_ws_user(token=token, api_key=api_key, db=db)
    except Exception:
        await websocket.close(code=4001)
        return

    channel = f"agent_logs:{agent_id}"
    await manager.connect(channel, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(channel, websocket)


@router.websocket("/ws/system/logs")
async def ws_system_logs(
    websocket: WebSocket,
    token: str | None = Query(None),
    api_key: str | None = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
):
    try:
        user = await get_ws_user(token=token, api_key=api_key, db=db)
    except Exception:
        await websocket.close(code=4001)
        return

    await manager.connect("system_logs", websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect("system_logs", websocket)
