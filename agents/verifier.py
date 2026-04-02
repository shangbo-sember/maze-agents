"""
Verifier Agent - 死路验证
"""

import asyncio
from typing import List, Tuple, Set
from datetime import datetime

from .types import Position, CellState, AgentRole
from .messages import Message, MessageType


class VerifierAgent:
    """
    验证者 Agent
    
    职责：
    1. 验证疑似死路
    2. 确认路径有效性
    3. 检测循环路径
    """
    
    def __init__(self, agent_id: str = "verifier", maze_accessor=None):
        self.agent_id = agent_id
        self.role = AgentRole.VERIFIER
        self.mailbox: asyncio.Queue = asyncio.Queue()
        self.maze_accessor = maze_accessor
        self.running = True
        self.verified_dead_ends: Set[Position] = set()
        
    async def start(self):
        """启动 Verifier"""
        print(f"[{self.agent_id}] Verifier 启动")
        self.running = True
    
    async def stop(self):
        """停止 Verifier"""
        self.running = False
        print(f"[{self.agent_id}] Verifier 停止")
    
    async def handle_message(self, msg: Message):
        """处理接收到的消息"""
        
        if msg.type == MessageType.VERIFY_PATH:
            await self._handle_verify_path(msg)
    
    async def _handle_verify_path(self, msg: Message):
        """处理路径验证请求"""
        content = msg.content
        
        path = [Position(*p) for p in content.get("path", [])]
        verify_type = content.get("verify_type", "dead_end")  # "dead_end" or "path"
        
        print(f"[{self.agent_id}] 验证请求：类型={verify_type}, 路径长度={len(path)}")
        
        if verify_type == "dead_end":
            result = await self._verify_dead_end(path)
        else:
            result = await self._verify_path(path)
        
        # 发送验证结果
        response = msg.create_reply(MessageType.VERIFY_RESULT, result)
        
        from utils.mailbox import send_message
        await send_message(response)
    
    async def _verify_dead_end(self, path: List[Position]) -> dict:
        """验证死路"""
        if not path:
            return {
                "success": False,
                "error": "Empty path",
                "is_dead_end": False,
            }
        
        end_pos = path[-1]
        
        # 检查所有方向
        neighbors = end_pos.neighbors()
        blocked_directions = []
        
        for neighbor in neighbors:
            # 检查是否是来时的方向
            if len(path) > 1 and neighbor == path[-2]:
                continue
            
            # 检查邻居状态
            if self.maze_accessor:
                state = await self.maze_accessor.get_cell(neighbor)
            else:
                state = CellState.UNKNOWN
            
            if state in (CellState.WALL, CellState.DEAD_END, CellState.VISITED):
                blocked_directions.append(neighbor)
        
        # 如果所有方向都被阻塞，确认是死路
        is_dead_end = len(blocked_directions) == len(neighbors) - (1 if len(path) > 1 else 0)
        
        if is_dead_end:
            self.verified_dead_ends.add(end_pos)
        
        return {
            "success": True,
            "is_dead_end": is_dead_end,
            "position": (end_pos.x, end_pos.y),
            "blocked_directions": [(p.x, p.y) for p in blocked_directions],
            "confidence": 1.0 if is_dead_end else 0.5,
        }
    
    async def _verify_path(self, path: List[Position]) -> dict:
        """验证路径有效性"""
        if not path:
            return {
                "success": False,
                "error": "Empty path",
                "is_valid": False,
            }
        
        # 检查路径连续性
        for i in range(len(path) - 1):
            curr = path[i]
            next_pos = path[i + 1]
            
            # 检查是否相邻
            if curr.distance_to(next_pos) != 1:
                return {
                    "success": True,
                    "is_valid": False,
                    "reason": f"Non-adjacent positions: {curr} -> {next_pos}",
                    "error_position": (next_pos.x, next_pos.y),
                }
            
            # 检查是否有墙壁
            if self.maze_accessor:
                state = await self.maze_accessor.get_cell(next_pos)
                if state == CellState.WALL:
                    return {
                        "success": True,
                        "is_valid": False,
                        "reason": "Path goes through wall",
                        "error_position": (next_pos.x, next_pos.y),
                    }
        
        # 检查是否有循环
        positions_set = set((p.x, p.y) for p in path)
        has_loop = len(positions_set) < len(path)
        
        if has_loop:
            return {
                "success": True,
                "is_valid": False,
                "reason": "Path contains loop",
            }
        
        return {
            "success": True,
            "is_valid": True,
            "length": len(path),
            "has_loop": has_loop,
        }
    
    async def run(self):
        """运行循环"""
        from utils.mailbox import receive_message
        
        await self.start()
        
        while self.running:
            try:
                msg = await receive_message(self.agent_id, timeout=0.5)
                if msg:
                    await self.handle_message(msg)
            except asyncio.CancelledError:
                break
            await asyncio.sleep(0.1)
        
        await self.stop()
