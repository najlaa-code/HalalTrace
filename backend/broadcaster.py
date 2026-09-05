import asyncio
from fastapi import WebSocket
from pydantic import BaseModel

class DashboardBroadcaster:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()