"""
WebSocket Manager for Real-time Updates
Provides WebSocket connections for live job status, notifications, and real-time data.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Any
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from starlette.routing import Route, Router
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types."""
    JOB_STATUS = "job_status"
    NOTIFICATION = "notification"
    MARKET_UPDATE = "market_update"
    RECOMMENDATION = "recommendation"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    Supports user-specific and broadcast messaging.
    """
    
    def __init__(self):
        # Active connections: user_id -> set of websockets
        self._connections: Dict[str, Set[WebSocket]] = {}
        # Room connections: room_id -> set of websockets
        self._rooms: Dict[str, Set[WebSocket]] = {}
        # All active connections for broadcasting
        self._all_connections: Set[WebSocket] = set()
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        async with self._lock:
            self._all_connections.add(websocket)
            
            if user_id:
                if user_id not in self._connections:
                    self._connections[user_id] = set()
                self._connections[user_id].add(websocket)
                
                logger.info(f"User {user_id} connected. Total: {len(self._connections[user_id])}")
    
    async def disconnect(self, websocket: WebSocket, user_id: Optional[str] = None):
        """Remove a WebSocket connection."""
        async with self._lock:
            self._all_connections.discard(websocket)
            
            if user_id and user_id in self._connections:
                self._connections[user_id].discard(websocket)
                if not self._connections[user_id]:
                    del self._connections[user_id]
            
            # Remove from all rooms
            for room_id in list(self._rooms.keys()):
                self._rooms[room_id].discard(websocket)
                if not self._rooms[room_id]:
                    del self._rooms[room_id]
    
    async def join_room(self, websocket: WebSocket, room_id: str):
        """Add connection to a room."""
        async with self._lock:
            if room_id not in self._rooms:
                self._rooms[room_id] = set()
            self._rooms[room_id].add(websocket)
    
    async def leave_room(self, websocket: WebSocket, room_id: str):
        """Remove connection from a room."""
        async with self._lock:
            if room_id in self._rooms:
                self._rooms[room_id].discard(websocket)
                if not self._rooms[room_id]:
                    del self._rooms[room_id]
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user."""
        message["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        async with self._lock:
            if user_id in self._connections:
                disconnected = set()
                for websocket in self._connections[user_id]:
                    try:
                        if websocket.client_state == WebSocketState.CONNECTED:
                            await websocket.send_json(message)
                        else:
                            disconnected.add(websocket)
                    except Exception as e:
                        logger.warning(f"Failed to send to user {user_id}: {e}")
                        disconnected.add(websocket)
                
                # Clean up disconnected
                for ws in disconnected:
                    self._connections[user_id].discard(ws)
    
    async def broadcast_to_room(self, message: dict, room_id: str):
        """Broadcast message to all users in a room."""
        message["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        async with self._lock:
            if room_id not in self._rooms:
                return
            
            disconnected = set()
            for websocket in self._rooms[room_id]:
                try:
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json(message)
                    else:
                        disconnected.add(websocket)
                except Exception as e:
                    logger.warning(f"Failed to broadcast to room {room_id}: {e}")
                    disconnected.add(websocket)
            
            # Clean up disconnected
            for ws in disconnected:
                self._rooms[room_id].discard(ws)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        message["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        async with self._lock:
            disconnected = set()
            for websocket in self._all_connections:
                try:
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json(message)
                    else:
                        disconnected.add(websocket)
                except Exception as e:
                    logger.warning(f"Failed to broadcast: {e}")
                    disconnected.add(websocket)
            
            for ws in disconnected:
                self._all_connections.discard(ws)
    
    def get_connected_users(self) -> list:
        """Get list of connected user IDs."""
        return list(self._connections.keys())
    
    def get_connection_count(self, user_id: Optional[str] = None) -> int:
        """Get connection count for user or total."""
        if user_id:
            return len(self._connections.get(user_id, set()))
        return len(self._all_connections)


# Global connection manager
manager = ConnectionManager()


# WebSocket endpoint
async def websocket_endpoint(websocket: WebSocket, user_id: Optional[str] = None):
    """
    WebSocket endpoint for real-time updates.
    
    Query params:
        user_id: Optional user ID for user-specific messages
    
    Example:
        ws://localhost:8000/ws?user_id=123
    """
    user_id = user_id or websocket.query_params.get("user_id", "")
    
    await manager.connect(websocket, user_id)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": MessageType.NOTIFICATION.value,
            "message": "Connected to Career Navigator",
            "user_id": user_id
        })
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == MessageType.HEARTBEAT.value:
                    # Respond to heartbeat
                    await websocket.send_json({
                        "type": MessageType.HEARTBEAT.value,
                        "status": "alive"
                    })
                    
                elif message_type == "join_room":
                    room_id = message.get("room_id")
                    if room_id:
                        await manager.join_room(websocket, room_id)
                        
                elif message_type == "leave_room":
                    room_id = message.get("room_id")
                    if room_id:
                        await manager.leave_room(websocket, room_id)
                        
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received")
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(websocket, user_id)


# Helper functions for sending updates
async def notify_job_status(user_id: str, job_id: str, status: str, progress: Optional[int] = None):
    """Send job status update to user."""
    message = {
        "type": MessageType.JOB_STATUS.value,
        "job_id": job_id,
        "status": status,
        "progress": progress
    }
    await manager.send_personal_message(message, user_id)


async def notify_analysis_complete(user_id: str, job_id: str, result: dict):
    """Send analysis completion notification."""
    message = {
        "type": MessageType.JOB_STATUS.value,
        "job_id": job_id,
        "status": "completed",
        "result": result
    }
    await manager.send_personal_message(message, user_id)


async def notify_error(user_id: str, error_message: str, code: Optional[str] = None):
    """Send error notification to user."""
    message = {
        "type": MessageType.ERROR.value,
        "error": error_message,
        "code": code
    }
    await manager.send_personal_message(message, user_id)


async def broadcast_market_update(data: dict):
    """Broadcast market data updates to all connected clients."""
    message = {
        "type": MessageType.MARKET_UPDATE.value,
        "data": data
    }
    await manager.broadcast(message)


async def send_recommendation(user_id: str, recommendation: dict):
    """Send job/career recommendation to user."""
    message = {
        "type": MessageType.RECOMMENDATION.value,
        "recommendation": recommendation
    }
    await manager.send_personal_message(message, user_id)


# WebSocket router
ws_router = APIRouter()

@ws_router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint."""
    await websocket_endpoint(websocket)

@ws_router.websocket("/ws/{user_id}")
async def ws_user_endpoint(websocket: WebSocket, user_id: str):
    """User-specific WebSocket endpoint."""
    await websocket_endpoint(websocket, user_id)
