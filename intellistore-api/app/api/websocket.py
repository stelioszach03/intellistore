"""
WebSocket endpoints for real-time updates
"""

import asyncio
import json
import time
from typing import Dict, Set

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.websockets import WebSocketState

from app.api.auth import get_current_user, UserInfo

router = APIRouter()
logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user: str, channel: str = "general"):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        # Add to channel
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        
        # Add to user connections
        if user not in self.user_connections:
            self.user_connections[user] = set()
        self.user_connections[user].add(websocket)
        
        logger.info("WebSocket connected", user=user, channel=channel)
    
    def disconnect(self, websocket: WebSocket, user: str, channel: str = "general"):
        """Remove a WebSocket connection"""
        # Remove from channel
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            if not self.active_connections[channel]:
                del self.active_connections[channel]
        
        # Remove from user connections
        if user in self.user_connections:
            self.user_connections[user].discard(websocket)
            if not self.user_connections[user]:
                del self.user_connections[user]
        
        logger.info("WebSocket disconnected", user=user, channel=channel)
    
    async def send_personal_message(self, message: dict, user: str):
        """Send a message to a specific user"""
        if user in self.user_connections:
            disconnected = set()
            for websocket in self.user_connections[user]:
                try:
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_text(json.dumps(message))
                    else:
                        disconnected.add(websocket)
                except Exception as e:
                    logger.error("Failed to send personal message", user=user, error=str(e))
                    disconnected.add(websocket)
            
            # Clean up disconnected websockets
            for ws in disconnected:
                self.user_connections[user].discard(ws)
    
    async def broadcast_to_channel(self, message: dict, channel: str = "general"):
        """Broadcast a message to all connections in a channel"""
        if channel in self.active_connections:
            disconnected = set()
            for websocket in self.active_connections[channel]:
                try:
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_text(json.dumps(message))
                    else:
                        disconnected.add(websocket)
                except Exception as e:
                    logger.error("Failed to broadcast message", channel=channel, error=str(e))
                    disconnected.add(websocket)
            
            # Clean up disconnected websockets
            for ws in disconnected:
                self.active_connections[channel].discard(ws)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all active connections"""
        for channel in list(self.active_connections.keys()):
            await self.broadcast_to_channel(message, channel)
    
    def get_connection_count(self, channel: str = None) -> int:
        """Get the number of active connections"""
        if channel:
            return len(self.active_connections.get(channel, set()))
        return sum(len(connections) for connections in self.active_connections.values())


# Global connection manager
manager = ConnectionManager()


async def get_current_user_ws(token: str = Query(...)):
    """Get current user for WebSocket connections"""
    # In a real implementation, you would validate the JWT token here
    # For demo purposes, we'll extract username from token
    try:
        # Simple token validation (in production, use proper JWT validation)
        if token.startswith("user-"):
            username = token.replace("user-", "")
            return UserInfo(username=username, roles=["user"])
        elif token == "admin-token":
            return UserInfo(username="admin", roles=["admin", "user"])
        else:
            raise Exception("Invalid token")
    except Exception:
        raise Exception("Authentication failed")


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...),
    channel: str = Query(default="general")
):
    """WebSocket endpoint for real-time notifications"""
    try:
        # Authenticate user
        user = await get_current_user_ws(token)
        
        # Connect to WebSocket
        await manager.connect(websocket, user.username, channel)
        
        # Send welcome message
        welcome_message = {
            "type": "connection",
            "message": "Connected to IntelliStore notifications",
            "user": user.username,
            "channel": channel,
            "timestamp": time.time()
        }
        await websocket.send_text(json.dumps(welcome_message))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    # Respond to ping with pong
                    pong_message = {
                        "type": "pong",
                        "timestamp": time.time()
                    }
                    await websocket.send_text(json.dumps(pong_message))
                
                elif message.get("type") == "subscribe":
                    # Subscribe to additional channels
                    new_channel = message.get("channel", "general")
                    await manager.connect(websocket, user.username, new_channel)
                    
                    response = {
                        "type": "subscribed",
                        "channel": new_channel,
                        "timestamp": time.time()
                    }
                    await websocket.send_text(json.dumps(response))
                
                elif message.get("type") == "get_status":
                    # Send current system status
                    status_message = {
                        "type": "status",
                        "data": {
                            "active_connections": manager.get_connection_count(),
                            "user_connections": len(manager.user_connections),
                            "channels": list(manager.active_connections.keys())
                        },
                        "timestamp": time.time()
                    }
                    await websocket.send_text(json.dumps(status_message))
                
                else:
                    logger.warning("Unknown message type", 
                                 message_type=message.get("type"),
                                 user=user.username)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                error_message = {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": time.time()
                }
                await websocket.send_text(json.dumps(error_message))
            except Exception as e:
                logger.error("Error handling WebSocket message", 
                           user=user.username, 
                           error=str(e))
                error_message = {
                    "type": "error",
                    "message": "Internal server error",
                    "timestamp": time.time()
                }
                await websocket.send_text(json.dumps(error_message))
    
    except Exception as e:
        logger.error("WebSocket connection failed", error=str(e))
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1008, reason="Authentication failed")
    
    finally:
        # Clean up connection
        try:
            user = await get_current_user_ws(token)
            manager.disconnect(websocket, user.username, channel)
        except:
            pass


@router.websocket("/logs")
async def websocket_logs(
    websocket: WebSocket,
    token: str = Query(...),
    log_level: str = Query(default="INFO")
):
    """WebSocket endpoint for real-time log streaming"""
    try:
        # Authenticate user (admin only for logs)
        user = await get_current_user_ws(token)
        if "admin" not in user.roles:
            await websocket.close(code=1008, reason="Admin access required")
            return
        
        await manager.connect(websocket, user.username, "logs")
        
        # Send welcome message
        welcome_message = {
            "type": "log_stream_started",
            "log_level": log_level,
            "user": user.username,
            "timestamp": time.time()
        }
        await websocket.send_text(json.dumps(welcome_message))
        
        # Simulate log streaming (in production, this would connect to actual log stream)
        log_counter = 0
        while True:
            try:
                # Wait for client messages or send periodic logs
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                    message = json.loads(data)
                    
                    if message.get("type") == "change_log_level":
                        log_level = message.get("log_level", "INFO")
                        response = {
                            "type": "log_level_changed",
                            "log_level": log_level,
                            "timestamp": time.time()
                        }
                        await websocket.send_text(json.dumps(response))
                
                except asyncio.TimeoutError:
                    # Send a sample log entry
                    log_counter += 1
                    sample_log = {
                        "type": "log_entry",
                        "level": log_level,
                        "timestamp": time.time(),
                        "service": "intellistore-api",
                        "message": f"Sample log entry #{log_counter}",
                        "metadata": {
                            "request_id": f"req-{log_counter}",
                            "user": "system"
                        }
                    }
                    await websocket.send_text(json.dumps(sample_log))
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error("Error in log streaming", user=user.username, error=str(e))
                break
    
    except Exception as e:
        logger.error("Log WebSocket connection failed", error=str(e))
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1008, reason="Authentication failed")
    
    finally:
        try:
            user = await get_current_user_ws(token)
            manager.disconnect(websocket, user.username, "logs")
        except:
            pass


# Utility functions for sending notifications
async def send_notification(notification_type: str, message: str, data: dict = None, user: str = None, channel: str = "general"):
    """Send a notification to WebSocket clients"""
    notification = {
        "type": "notification",
        "notification_type": notification_type,
        "message": message,
        "data": data or {},
        "timestamp": time.time()
    }
    
    if user:
        await manager.send_personal_message(notification, user)
    else:
        await manager.broadcast_to_channel(notification, channel)


async def send_object_uploaded_notification(bucket_name: str, object_key: str, user: str, size: int):
    """Send notification when an object is uploaded"""
    await send_notification(
        notification_type="object_uploaded",
        message=f"Object {object_key} uploaded to bucket {bucket_name}",
        data={
            "bucket_name": bucket_name,
            "object_key": object_key,
            "size": size,
            "user": user
        },
        user=user
    )


async def send_tier_migration_notification(bucket_name: str, object_key: str, from_tier: str, to_tier: str, user: str = None):
    """Send notification when an object is migrated between tiers"""
    await send_notification(
        notification_type="tier_migration",
        message=f"Object {object_key} migrated from {from_tier} to {to_tier}",
        data={
            "bucket_name": bucket_name,
            "object_key": object_key,
            "from_tier": from_tier,
            "to_tier": to_tier
        },
        user=user,
        channel="general"
    )


async def send_hot_object_detected_notification(bucket_name: str, object_key: str, confidence: float):
    """Send notification when ML detects a hot object"""
    await send_notification(
        notification_type="hot_object_detected",
        message=f"Hot object detected: {object_key} (confidence: {confidence:.2f})",
        data={
            "bucket_name": bucket_name,
            "object_key": object_key,
            "confidence": confidence,
            "prediction": "hot"
        },
        channel="general"
    )


async def send_storage_node_down_notification(node_id: str, node_addr: str):
    """Send notification when a storage node goes down"""
    await send_notification(
        notification_type="storage_node_down",
        message=f"Storage node {node_id} is offline",
        data={
            "node_id": node_id,
            "node_addr": node_addr,
            "severity": "warning"
        },
        channel="general"
    )


async def send_system_alert_notification(alert_name: str, severity: str, description: str):
    """Send notification for system alerts"""
    await send_notification(
        notification_type="system_alert",
        message=f"{severity.upper()}: {alert_name}",
        data={
            "alert_name": alert_name,
            "severity": severity,
            "description": description
        },
        channel="general"
    )


# Background task to send periodic status updates
async def periodic_status_updates():
    """Send periodic status updates to connected clients"""
    while True:
        try:
            await asyncio.sleep(30)  # Every 30 seconds
            
            if manager.get_connection_count() > 0:
                status_update = {
                    "type": "status_update",
                    "data": {
                        "timestamp": time.time(),
                        "active_connections": manager.get_connection_count(),
                        "system_status": "healthy",
                        "uptime": time.time() - 1000000  # Demo uptime
                    },
                    "timestamp": time.time()
                }
                
                await manager.broadcast_to_channel(status_update, "general")
        
        except Exception as e:
            logger.error("Error sending periodic status update", error=str(e))


# Background task will be started by FastAPI startup event