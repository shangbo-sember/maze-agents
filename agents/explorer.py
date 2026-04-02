"""
Explorer Agent - 路径探索
"""

import asyncio
from typing import List, Tuple, Optional
from datetime import datetime

from .types import Position, CellState, AgentRole
from .messages import Message, MessageType, ExploreRequest, ExploreResult


class ExplorerAgent:
    """
    探索者 Agent
    
    职责：
    1. 接收 Coordinator 的探索指令
    2. 深度优先探索路径
    3. 报告探索结果
    4. 检测死路
    """
    
    def __init__(self, agent_id: str, maze_accessor):
        self.agent_id = agent_id
        self.role = AgentRole.EXPLORER
        self.mailbox: asyncio.Queue = asyncio.Queue()
        self.maze_accessor = maze_accessor  # 用于读取迷宫状态
        self.current_task: Optional[asyncio.Task] = None
        self.running = True
        self.exploring = False
        
    async def start(self):
        """启动 Explorer"""
        print(f"[{self.agent_id}] Explorer 启动")
        self.running = True
    
    async def stop(self):
        """停止 Explorer"""
        self.running = False
        self.exploring = False
        if self.current_task:
            self.current_task.cancel()
            try:
                await self.current_task
            except asyncio.CancelledError:
                pass
        print(f"[{self.agent_id}] Explorer 停止")
    
    async def handle_message(self, msg: Message):
        """处理接收到的消息"""
        
        if msg.type == MessageType.EXPLORE_REQUEST:
            await self._handle_explore_request(msg)
            
        elif msg.type == MessageType.EXPLORE_CANCEL:
            await self._handle_explore_cancel(msg)
    
    async def _handle_explore_request(self, msg: Message):
        """处理探索请求"""
        if self.exploring:
            print(f"[{self.agent_id}] 正在探索中，忽略新请求")
            return
        
        data = ExploreRequest.from_dict(msg.content)
        
        from_pos = Position(*data.from_pos)
        direction = data.direction
        max_depth = data.max_depth
        
        print(f"[{self.agent_id}] 收到探索请求：从 {from_pos} 向 {direction} (深度={max_depth})")
        
        # 启动探索任务
        self.exploring = True
        self.current_task = asyncio.create_task(
            self._explore(from_pos, direction, max_depth, msg)
        )
    
    async def _explore(self, from_pos: Position, direction: str, 
                       max_depth: int, request_msg: Message):
        """执行深度探索"""
        
        cells_explored = []
        dead_ends = []
        paths_found = []
        
        # 将方向转换为位置偏移
        direction_offsets = {
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "right": (1, 0),
            "forward": (0, 0),  # 特殊处理
        }
        
        dx, dy = direction_offsets.get(direction, (0, 0))
        
        # 如果是 forward，需要推断方向
        if direction == "forward":
            # 从路径历史推断
            path_history = await self.maze_accessor.get_path_history()
            if len(path_history) >= 2:
                prev = Position(*path_history[-2])
                curr = Position(*path_history[-1])
                dx = curr.x - prev.x
                dy = curr.y - prev.y
            else:
                dx, dy = 0, 1  # 默认向下
        
        current_pos = from_pos
        depth = 0
        
        try:
            while depth < max_depth and self.running and self.exploring:
                # 移动到下一个位置
                next_pos = Position(current_pos.x + dx, current_pos.y + dy)
                
                # 检查迷宫状态
                cell_state = await self.maze_accessor.get_cell(next_pos)
                
                if cell_state == CellState.WALL:
                    # 遇到墙壁，当前是死路
                    print(f"[{self.agent_id}] 遇到墙壁：{current_pos}")
                    dead_ends.append(current_pos)
                    break
                    
                elif cell_state == CellState.DEAD_END:
                    # 已知死路
                    print(f"[{self.agent_id}] 已知死路：{current_pos}")
                    dead_ends.append(current_pos)
                    break
                    
                elif cell_state == CellState.VISITED:
                    # 已访问过，可能是循环
                    cells_explored.append((next_pos, CellState.VISITED))
                    depth += 1
                    current_pos = next_pos
                    continue
                    
                else:
                    # 新路径
                    cells_explored.append((next_pos, CellState.PATH))
                    paths_found.append(next_pos)
                    depth += 1
                    current_pos = next_pos
                    
                    # 检查是否到达终点
                    if await self.maze_accessor.is_end(next_pos):
                        print(f"[{self.agent_id}] 到达终点！{next_pos}")
                        await self._report_path_found(
                            request_msg, 
                            cells_explored,
                            dead_ends,
                            paths_found
                        )
                        return
                    
                    # 检查是否有多个方向可选
                    neighbors = next_pos.neighbors()
                    valid_neighbors = []
                    for neighbor in neighbors:
                        state = await self.maze_accessor.get_cell(neighbor)
                        if state not in (CellState.WALL, CellState.DEAD_END, CellState.VISITED):
                            valid_neighbors.append(neighbor)
                    
                    if len(valid_neighbors) > 1:
                        # 有分支，报告给 Coordinator 决策
                        print(f"[{self.agent_id}] 发现分支：{next_pos}, 可选方向={len(valid_neighbors)}")
                        break
            
            # 报告探索结果
            await self._report_explore_result(
                request_msg,
                cells_explored,
                dead_ends,
                paths_found
            )
            
        except asyncio.CancelledError:
            print(f"[{self.agent_id}] 探索被取消")
            raise
        finally:
            self.exploring = False
    
    async def _report_explore_result(self, request_msg: Message,
                                     cells_explored: List[Tuple[Position, CellState]],
                                     dead_ends: List[Position],
                                     paths_found: List[Position]):
        """报告探索结果"""
        from utils.mailbox import send_message
        
        content = ExploreResult(
            from_pos=request_msg.content["from_pos"],
            direction=request_msg.content["direction"],
            cells_explored=[((pos.x, pos.y), state.value) for pos, state in cells_explored],
            dead_ends=[(pos.x, pos.y) for pos in dead_ends],
            paths_found=[(pos.x, pos.y) for pos in paths_found],
        ).to_dict()
        
        msg = request_msg.create_reply(MessageType.EXPLORE_RESULT, content)
        
        await send_message(msg)
        
        print(f"[{self.agent_id}] 报告探索结果：探索={len(cells_explored)}, 死路={len(dead_ends)}, 路径={len(paths_found)}")
    
    async def _report_path_found(self, request_msg: Message,
                                 cells_explored: List[Tuple[Position, CellState]],
                                 dead_ends: List[Position],
                                 paths_found: List[Position]):
        """报告找到路径"""
        from utils.mailbox import send_message
        from .messages import PathFound
        
        # 构建完整路径
        full_path = [Position(*request_msg.content["from_pos"])] + paths_found
        
        content = PathFound(
            path=[(pos.x, pos.y) for pos in full_path],
            length=len(full_path),
            confidence=1.0,
            reaches_end=True,
        ).to_dict()
        
        msg = request_msg.create_reply(MessageType.PATH_FOUND, content)
        
        await send_message(msg)
        
        print(f"[{self.agent_id}] 报告找到路径：长度={len(full_path)}")
    
    async def _handle_explore_cancel(self, msg: Message):
        """处理取消探索"""
        print(f"[{self.agent_id}] 收到取消请求：{msg.content.get('reason', 'unknown')}")
        
        if self.current_task:
            self.current_task.cancel()
            try:
                await self.current_task
            except asyncio.CancelledError:
                pass
        
        self.exploring = False
    
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
