"""
Memory Agent - 状态管理
"""

import asyncio
from typing import Dict, Set, List, Optional, Tuple
from datetime import datetime

from .types import Position, CellState, MazeState, AgentRole
from .messages import Message, MessageType, StateUpdate, StateResponse


class MemoryAgent:
    """
    记忆 Agent
    
    职责：
    1. 维护全局迷宫状态
    2. 处理状态查询
    3. 处理状态更新
    4. 提供路径历史
    """
    
    def __init__(self, agent_id: str = "memory"):
        self.agent_id = agent_id
        self.role = AgentRole.MEMORY
        self.mailbox: asyncio.Queue = asyncio.Queue()
        self.running = True
        
        # 持久化状态
        self.grid: Dict[Position, CellState] = {}
        self.visited: Set[Position] = set()
        self.path_history: List[Position] = []
        self.start: Optional[Position] = None
        self.end: Optional[Position] = None
        self.current_pos: Optional[Position] = None
        
    async def initialize(self, maze_config: dict):
        """初始化迷宫状态"""
        self.start = Position(*maze_config.get("start", (0, 0)))
        self.end = Position(*maze_config.get("end", (9, 9)))
        self.current_pos = self.start
        self.path_history = [self.start]
        
        # 初始化网格（从配置或文件加载）
        grid_config = maze_config.get("grid", {})
        for pos_str, state in grid_config.items():
            # 解析位置字符串 "(x, y)" -> Position
            import ast
            pos_tuple = ast.literal_eval(pos_str)
            pos = Position(*pos_tuple)
            self.grid[pos] = CellState(state)
        
        print(f"[{self.agent_id}] Memory 初始化完成，起点={self.start}, 终点={self.end}")
    
    async def handle_message(self, msg: Message):
        """处理接收到的消息"""
        
        if msg.type == MessageType.STATE_UPDATE:
            await self._handle_state_update(msg)
            
        elif msg.type == MessageType.STATE_QUERY:
            await self._handle_state_query(msg)
    
    async def _handle_state_update(self, msg: Message):
        """处理状态更新"""
        from .messages import StateUpdate
        
        data = StateUpdate.from_dict(msg.content)
        
        # 更新单元格状态
        for pos_tuple, state in data.updated_cells.items():
            pos = Position(*pos_tuple)
            self.grid[pos] = CellState(state)
        
        # 更新当前位置
        if data.new_current_pos:
            new_pos = Position(*data.new_current_pos)
            self.path_history.append(new_pos)
            self.visited.add(new_pos)
            self.current_pos = new_pos
        
        # 添加路径
        for pos_tuple in data.path_added:
            pos = Position(*pos_tuple)
            self.visited.add(pos)
        
        # 添加死路
        for pos_tuple in data.dead_ends_added:
            pos = Position(*pos_tuple)
            self.grid[pos] = CellState.DEAD_END
        
        print(f"[{self.agent_id}] 状态更新：当前位置={self.current_pos}, 已访问={len(self.visited)}")
    
    async def _handle_state_query(self, msg: Message):
        """处理状态查询"""
        content = msg.content
        query_type = content.get("query_type", "unknown")
        
        response_data = {"query_type": query_type}
        
        try:
            if query_type == "get_cell":
                pos = Position(*content["position"])
                state = self.grid.get(pos, CellState.UNKNOWN)
                response_data["result"] = {"cell_state": state.value}
                
            elif query_type == "is_visited":
                pos = Position(*content["position"])
                response_data["result"] = {"is_visited": pos in self.visited}
                
            elif query_type == "get_neighbors":
                pos = Position(*content["position"])
                neighbors = []
                for neighbor in pos.neighbors():
                    state = self.grid.get(neighbor, CellState.UNKNOWN)
                    if state != CellState.WALL:
                        neighbors.append((neighbor.x, neighbor.y))
                response_data["result"] = {"neighbors": neighbors}
                
            elif query_type == "get_path_history":
                response_data["result"] = {
                    "path_history": [(pos.x, pos.y) for pos in self.path_history]
                }
                
            elif query_type == "get_unexplored":
                current = self.path_history[-1] if self.path_history else self.start
                unexplored = []
                for neighbor in current.neighbors():
                    state = self.grid.get(neighbor, CellState.UNKNOWN)
                    if state == CellState.UNKNOWN:
                        unexplored.append((neighbor.x, neighbor.y))
                response_data["result"] = {"unexplored": unexplored}
                
            elif query_type == "get_current_pos":
                response_data["result"] = {
                    "current_pos": (self.current_pos.x, self.current_pos.y) if self.current_pos else None
                }
                
            elif query_type == "is_end":
                pos = Position(*content["position"])
                response_data["result"] = {"is_end": self.end and pos == self.end}
            
            else:
                response_data["success"] = False
                response_data["error"] = f"Unknown query type: {query_type}"
                
        except Exception as e:
            response_data["success"] = False
            response_data["error"] = str(e)
        
        # 发送响应
        response_msg = msg.create_reply(MessageType.STATE_RESPONSE, response_data)
        
        from utils.mailbox import send_message
        await send_message(response_msg)
    
    # ============ 供 Explorer 使用的方法 ============
    
    async def get_cell(self, pos: Position) -> CellState:
        """获取单元格状态"""
        return self.grid.get(pos, CellState.UNKNOWN)
    
    async def is_end(self, pos: Position) -> bool:
        """检查是否是终点"""
        return self.end is not None and pos == self.end
    
    async def get_path_history(self) -> List[Tuple[int, int]]:
        """获取路径历史"""
        return [(pos.x, pos.y) for pos in self.path_history]
    
    async def get_current_pos(self) -> Optional[Tuple[int, int]]:
        """获取当前位置"""
        if self.current_pos:
            return (self.current_pos.x, self.current_pos.y)
        return None
    
    # ============ 状态导出 ============
    
    def get_maze_state(self) -> MazeState:
        """获取完整迷宫状态"""
        return MazeState(
            grid=self.grid.copy(),
            start=self.start,
            end=self.end,
            current_pos=self.current_pos,
            path_history=self.path_history.copy(),
        )
    
    async def run(self):
        """运行循环"""
        from utils.mailbox import receive_message
        
        print(f"[{self.agent_id}] Memory 启动")
        
        while self.running:
            try:
                msg = await receive_message(self.agent_id, timeout=0.5)
                if msg:
                    await self.handle_message(msg)
            except asyncio.CancelledError:
                break
            await asyncio.sleep(0.1)
        
        print(f"[{self.agent_id}] Memory 停止")
