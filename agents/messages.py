"""
消息定义
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import uuid


class MessageType(Enum):
    """消息类型"""
    
    # Coordinator → Explorer
    EXPLORE_REQUEST = "explore_request"
    EXPLORE_CANCEL = "explore_cancel"
    
    # Explorer → Coordinator
    EXPLORE_RESULT = "explore_result"
    DEAD_END_REPORT = "dead_end_report"
    PATH_FOUND = "path_found"
    
    # Coordinator → Memory
    STATE_UPDATE = "state_update"
    STATE_QUERY = "state_query"
    
    # Memory → Coordinator
    STATE_RESPONSE = "state_response"
    
    # Coordinator → Verifier
    VERIFY_PATH = "verify_path"
    
    # Verifier → Coordinator
    VERIFY_RESULT = "verify_result"
    
    # System
    MAZE_SOLVED = "maze_solved"
    MAZE_UNSOLVABLE = "maze_unsolvable"
    
    # Explorer 间通信
    HELP_REQUEST = "help_request"
    HELP_RESPONSE = "help_response"
    MAP_SHARE = "map_share"  # 分享地图/发现


@dataclass
class Message:
    """Agent 间消息"""
    type: MessageType
    sender_id: str
    receiver_id: str
    timestamp: datetime
    content: Dict[str, Any]
    read: bool = False
    
    # 用于追踪消息链
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    
    def mark_read(self):
        """标记为已读"""
        self.read = True
    
    def create_reply(self, msg_type: MessageType, content: Dict[str, Any]) -> 'Message':
        """创建回复消息"""
        return Message(
            type=msg_type,
            sender_id=self.receiver_id,
            receiver_id=self.sender_id,
            timestamp=datetime.now(),
            content=content,
            correlation_id=self.correlation_id or self.message_id,
            reply_to=self.message_id,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "type": self.type.value,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "read": self.read,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建"""
        return cls(
            message_id=data["message_id"],
            type=MessageType(data["type"]),
            sender_id=data["sender_id"],
            receiver_id=data["receiver_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            content=data["content"],
            read=data.get("read", False),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
        )


# ============ 具体消息内容 ============

@dataclass
class ExploreRequest:
    """探索请求"""
    from_pos: Tuple[int, int]
    direction: str  # "up", "down", "left", "right"
    max_depth: int = 10
    priority: int = 0  # 优先级，越高越优先
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_pos": self.from_pos,
            "direction": self.direction,
            "max_depth": self.max_depth,
            "priority": self.priority,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExploreRequest':
        return cls(
            from_pos=tuple(data["from_pos"]),
            direction=data["direction"],
            max_depth=data.get("max_depth", 10),
            priority=data.get("priority", 0),
        )


@dataclass
class ExploreResult:
    """探索结果"""
    from_pos: Tuple[int, int]
    direction: str
    cells_explored: List[Tuple[Tuple[int, int], str]]  # [(pos, state), ...]
    dead_ends: List[Tuple[int, int]]
    paths_found: List[Tuple[int, int]]
    explorer_status: str = "success"  # "success", "timeout", "cancelled"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_pos": self.from_pos,
            "direction": self.direction,
            "cells_explored": self.cells_explored,
            "dead_ends": self.dead_ends,
            "paths_found": self.paths_found,
            "explorer_status": self.explorer_status,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExploreResult':
        return cls(
            from_pos=tuple(data["from_pos"]),
            direction=data["direction"],
            cells_explored=[tuple(item) for item in data["cells_explored"]],
            dead_ends=[tuple(pos) for pos in data["dead_ends"]],
            paths_found=[tuple(pos) for pos in data["paths_found"]],
            explorer_status=data.get("explorer_status", "success"),
        )


@dataclass
class DeadEndReport:
    """死路报告"""
    position: Tuple[int, int]
    tried_directions: List[str]
    reason: str  # "all_paths_blocked", "visited_before", "wall_hit"
    confidence: float = 1.0  # 0-1，死路置信度
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": self.position,
            "tried_directions": self.tried_directions,
            "reason": self.reason,
            "confidence": self.confidence,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeadEndReport':
        return cls(
            position=tuple(data["position"]),
            tried_directions=data["tried_directions"],
            reason=data["reason"],
            confidence=data.get("confidence", 1.0),
        )


@dataclass
class PathFound:
    """找到路径"""
    path: List[Tuple[int, int]]
    length: int
    confidence: float  # 0-1，路径可信度
    reaches_end: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "length": self.length,
            "confidence": self.confidence,
            "reaches_end": self.reaches_end,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PathFound':
        return cls(
            path=[tuple(p) for p in data["path"]],
            length=data["length"],
            confidence=data.get("confidence", 1.0),
            reaches_end=data.get("reaches_end", False),
        )


@dataclass
class StateUpdate:
    """状态更新"""
    updated_cells: Dict[Tuple[int, int], str]
    new_current_pos: Optional[Tuple[int, int]] = None
    path_added: List[Tuple[int, int]] = field(default_factory=list)
    dead_ends_added: List[Tuple[int, int]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "updated_cells": {str(k): v for k, v in self.updated_cells.items()},
            "new_current_pos": self.new_current_pos,
            "path_added": self.path_added,
            "dead_ends_added": self.dead_ends_added,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateUpdate':
        import ast
        return cls(
            updated_cells={
                tuple(ast.literal_eval(k)): v 
                for k, v in data.get("updated_cells", {}).items()
            },
            new_current_pos=tuple(data["new_current_pos"]) if data.get("new_current_pos") else None,
            path_added=[tuple(p) for p in data.get("path_added", [])],
            dead_ends_added=[tuple(p) for p in data.get("dead_ends_added", [])],
        )


@dataclass
class StateResponse:
    """状态响应"""
    query_type: str
    result: Any
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_type": self.query_type,
            "result": self.result,
            "success": self.success,
            "error": self.error,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateResponse':
        return cls(
            query_type=data["query_type"],
            result=data["result"],
            success=data.get("success", True),
            error=data.get("error"),
        )
