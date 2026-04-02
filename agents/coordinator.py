"""
Coordinator Agent - 决策中心
"""

import asyncio
from typing import Dict, List, Optional, Set
from collections import deque
from datetime import datetime

from .types import Position, CellState, MazeState, AgentRole
from .messages import Message, MessageType, ExploreRequest, ExploreResult, PathFound


class CoordinatorAgent:
    """
    协调器 Agent
    
    职责：
    1. 接收 Explorer 的探索结果
    2. 决策下一步探索方向
    3. 管理 Explorer 池
    4. 汇总路径信息
    5. 判断迷宫是否可解
    """
    
    def __init__(self, agent_id: str = "coordinator"):
        self.agent_id = agent_id
        self.role = AgentRole.COORDINATOR
        self.mailbox: deque = deque()
        self.explorers: Dict[str, str] = {}  # explorer_id -> status
        self.pending_requests: Dict[str, Message] = {}
        self.known_paths: List[List[Position]] = []
        self.dead_ends: Set[Position] = set()
        self.explorer_counter = 0
        self.running = False
        self.maze_state: Optional[MazeState] = None
        
    async def start(self, maze_state: MazeState):
        """启动协调器"""
        self.maze_state = maze_state
        self.running = True
        
        print(f"[{self.agent_id}] 启动 Coordinator，起点={maze_state.start}, 终点={maze_state.end}")
        
        # 初始探索：从起点向四个方向派出 Explorer
        await self._initial_exploration()
    
    async def _initial_exploration(self):
        """初始探索"""
        start_pos = self.maze_state.start
        
        for direction in ["up", "down", "left", "right"]:
            await self.spawn_explorer(start_pos, direction, priority=10)
    
    async def spawn_explorer(self, from_pos: Position, direction: str, priority: int = 0) -> str:
        """派出 Explorer"""
        # 检查 Explorer 数量限制
        if len([e for e, s in self.explorers.items() if s == "exploring"]) >= 10:
            print(f"[{self.agent_id}] Explorer 数量已达上限，等待...")
            return ""
        
        explorer_id = f"explorer_{self.explorer_counter}"
        self.explorer_counter += 1
        
        content = ExploreRequest(
            from_pos=(from_pos.x, from_pos.y),
            direction=direction,
            max_depth=15,
            priority=priority,
        ).to_dict()
        
        msg = Message(
            type=MessageType.EXPLORE_REQUEST,
            sender_id=self.agent_id,
            receiver_id=explorer_id,
            timestamp=datetime.now(),
            content=content,
        )
        
        self.explorers[explorer_id] = "exploring"
        self.pending_requests[explorer_id] = msg
        
        # 发送到 Explorer 邮箱
        from utils.mailbox import send_message
        await send_message(msg)
        
        print(f"[{self.agent_id}] 派出 {explorer_id} 从 {from_pos} 向 {direction} 探索")
        
        return explorer_id
    
    async def handle_message(self, msg: Message):
        """处理接收到的消息"""
        
        if msg.type == MessageType.EXPLORE_RESULT:
            await self._handle_explore_result(msg)
            
        elif msg.type == MessageType.DEAD_END_REPORT:
            await self._handle_dead_end_report(msg)
            
        elif msg.type == MessageType.PATH_FOUND:
            await self._handle_path_found(msg)
            
        elif msg.type == MessageType.STATE_RESPONSE:
            await self._handle_state_response(msg)
    
    async def _handle_explore_result(self, msg: Message):
        """处理探索结果"""
        data = ExploreResult.from_dict(msg.content)
        
        # 更新 Explorer 状态
        self.explorers[msg.sender_id] = "idle"
        
        # 更新已知地图
        for pos_tuple, state in data.cells_explored:
            pos = Position(*pos_tuple)
            self.maze_state.set_cell(pos, CellState(state))
        
        # 记录死路
        for pos_tuple in data.dead_ends:
            pos = Position(*pos_tuple)
            self.dead_ends.add(pos)
            self.maze_state.set_cell(pos, CellState.DEAD_END)
        
        # 记录找到的路径
        if data.paths_found:
            current_path = [Position(*data.from_pos)]
            for pos_tuple in data.paths_found:
                current_path.append(Position(*pos_tuple))
            self.known_paths.append(current_path)
        
        # 决策下一步
        await self._decide_next_move(msg.sender_id)
    
    async def _handle_dead_end_report(self, msg: Message):
        """处理死路报告"""
        from .messages import DeadEndReport
        data = DeadEndReport.from_dict(msg.content)
        
        pos = Position(*data.position)
        self.dead_ends.add(pos)
        self.maze_state.set_cell(pos, CellState.DEAD_END)
        
        print(f"[{self.agent_id}] 死路报告：{pos}, 原因={data.reason}")
        
        # 可能需要回溯
        await self._handle_backtrack(pos)
    
    async def _handle_path_found(self, msg: Message):
        """处理找到路径"""
        from .messages import PathFound
        data = PathFound.from_dict(msg.content)
        
        path = [Position(*p) for p in data.path]
        self.known_paths.append(path)
        
        print(f"[{self.agent_id}] 找到路径，长度={data.length}, 到达终点={data.reaches_end}")
        
        # 检查是否到达终点
        if data.reaches_end or path[-1] == self.maze_state.end:
            await self._maze_solved(path)
        else:
            # 继续从路径末端探索
            await self.spawn_explorer(path[-1], "forward", priority=5)
    
    async def _handle_state_response(self, msg: Message):
        """处理状态响应"""
        # 处理 Memory 返回的查询结果
        pass
    
    async def _decide_next_move(self, explorer_id: str):
        """决策下一步"""
        if not self.maze_state:
            return
        
        current_pos = self.maze_state.current_pos
        
        # 获取可行方向（排除死路和已访问）
        available_directions = []
        for neighbor in current_pos.neighbors():
            if neighbor not in self.dead_ends:
                state = self.maze_state.get_cell(neighbor)
                if state not in (CellState.WALL, CellState.DEAD_END):
                    available_directions.append(neighbor)
        
        if not available_directions:
            # 需要回溯
            await self._handle_backtrack(current_pos)
            return
        
        # 启发式选择：优先选择离终点更近的方向
        end_pos = self.maze_state.end
        best_direction = min(
            available_directions,
            key=lambda p: p.distance_to(end_pos)
        )
        
        # 派出新的 Explorer
        direction = current_pos.direction_to(best_direction)
        await self.spawn_explorer(current_pos, direction, priority=5)
    
    async def _handle_backtrack(self, pos: Position):
        """处理回溯"""
        path_history = self.maze_state.path_history
        
        if len(path_history) > 1:
            # 回溯到上一个位置
            prev_pos = path_history[-2]
            self.maze_state.current_pos = prev_pos
            
            print(f"[{self.agent_id}] 回溯从 {pos} 到 {prev_pos}")
            
            # 通知 Memory 更新状态
            await self._update_state()
        else:
            # 无法回溯，可能无解
            print(f"[{self.agent_id}] 无法回溯，迷宫可能无解")
            await self._maze_unsolvable()
    
    async def _update_state(self):
        """更新状态到 Memory"""
        from .messages import StateUpdate
        from utils.mailbox import send_message
        
        content = StateUpdate(
            updated_cells={},
            new_current_pos=(self.maze_state.current_pos.x, self.maze_state.current_pos.y),
        ).to_dict()
        
        msg = Message(
            type=MessageType.STATE_UPDATE,
            sender_id=self.agent_id,
            receiver_id="memory",
            timestamp=datetime.now(),
            content=content,
        )
        
        await send_message(msg)
    
    async def _maze_solved(self, solution: List[Position]):
        """迷宫已解决"""
        self.maze_state.solution = solution
        self.maze_state.is_solved = True
        
        print(f"\n{'='*50}")
        print(f"🎉 迷宫已解决！")
        print(f"路径长度：{len(solution)}")
        print(f"路径：{[(p.x, p.y) for p in solution]}")
        print(f"{'='*50}\n")
        
        # 广播解决消息
        from utils.mailbox import broadcast_message
        
        msg = Message(
            type=MessageType.MAZE_SOLVED,
            sender_id=self.agent_id,
            receiver_id="broadcast",
            timestamp=datetime.now(),
            content={
                "solution": [(p.x, p.y) for p in solution],
                "length": len(solution),
            }
        )
        await broadcast_message(msg)
        
        # 停止所有 Explorer
        await self._stop_all_explorers()
    
    async def _maze_unsolvable(self):
        """迷宫无解"""
        self.maze_state.is_unsolvable = True
        
        print(f"\n{'='*50}")
        print(f"❌ 迷宫无解")
        print(f"{'='*50}\n")
        
        from utils.mailbox import broadcast_message
        
        msg = Message(
            type=MessageType.MAZE_UNSOLVABLE,
            sender_id=self.agent_id,
            receiver_id="broadcast",
            timestamp=datetime.now(),
            content={"reason": "all_paths_exhausted"}
        )
        await broadcast_message(msg)
        
        await self._stop_all_explorers()
    
    async def _stop_all_explorers(self):
        """停止所有 Explorer"""
        from utils.mailbox import send_message
        
        for explorer_id in list(self.explorers.keys()):
            msg = Message(
                type=MessageType.EXPLORE_CANCEL,
                sender_id=self.agent_id,
                receiver_id=explorer_id,
                timestamp=datetime.now(),
                content={"reason": "maze_completed"}
            )
            await send_message(msg)
            self.explorers[explorer_id] = "stopped"
        
        self.running = False
    
    async def run(self):
        """运行循环"""
        from utils.mailbox import receive_message
        
        while self.running:
            msg = await receive_message(self.agent_id, timeout=0.5)
            if msg:
                await self.handle_message(msg)
            await asyncio.sleep(0.1)
