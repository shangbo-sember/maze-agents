"""
Explorer Agent - 路径探索

支持与其他 Explorer 协作：
- 遇到死路时向其他 Explorer 求助
- 分享已探索的地图信息
- 响应其他 Explorer 的协作请求
"""

import asyncio
from typing import List, Tuple, Optional, Dict, Set
from datetime import datetime

from .types import Position, CellState, AgentRole
from .messages import Message, MessageType, ExploreRequest, ExploreResult, ExploreResult, DeadEndReport


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
        
        # 协作相关
        self.known_explorers: Set[str] = set()  # 已知的其他 Explorer ID
        self.shared_maps: Dict[str, List[Tuple[Tuple[int, int], str]]] = {}  # 其他 Explorer 分享的地图
        self.help_requests_sent: int = 0  # 发送的求助次数
        self.help_requests_received: int = 0  # 收到的求助次数
        self.collaboration_enabled = True  # 是否启用协作
        
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
            
        # 协作相关消息
        elif msg.type == MessageType.HELP_REQUEST:
            await self._handle_help_request(msg)
            
        elif msg.type == MessageType.HELP_RESPONSE:
            await self._handle_help_response(msg)
            
        elif msg.type == MessageType.MAP_SHARE:
            await self._handle_map_share(msg)
    
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
                    
                    # 尝试向其他 Explorer 求助
                    if self.collaboration_enabled and len(self.known_explorers) > 0:
                        await self._request_help(current_pos, direction, "wall_blocked")
                    
                    break
                    
                elif cell_state == CellState.DEAD_END:
                    # 已知死路
                    print(f"[{self.agent_id}] 已知死路：{current_pos}")
                    dead_ends.append(current_pos)
                    
                    # 尝试向其他 Explorer 求助
                    if self.collaboration_enabled and len(self.known_explorers) > 0:
                        await self._request_help(current_pos, direction, "dead_end")
                    
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
                        
                        # 同时向其他 Explorer 分享这个发现
                        if self.collaboration_enabled:
                            await self._share_discovery(next_pos, valid_neighbors)
                        
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
    
    # ========== 协作功能 ==========
    
    async def _request_help(self, position: Position, direction: str, reason: str):
        """向其他 Explorer 发送求助消息"""
        from utils.mailbox import broadcast_message, send_message
        
        self.help_requests_sent += 1
        
        content = {
            "position": (position.x, position.y),
            "direction": direction,
            "reason": reason,
            "requester_id": self.agent_id,
            "timestamp": datetime.now().isoformat(),
        }
        
        # 广播求助消息（所有 Explorer 都能收到）
        msg = Message(
            type=MessageType.HELP_REQUEST,
            sender_id=self.agent_id,
            receiver_id="broadcast",
            timestamp=datetime.now(),
            content=content,
        )
        
        await broadcast_message(msg)
        print(f"[{self.agent_id}] 🆘 发送求助：位置={position}, 原因={reason}")
    
    async def _handle_help_request(self, msg: Message):
        """处理其他 Explorer 的求助"""
        from utils.mailbox import send_message
        
        # 忽略自己的求助
        if msg.sender_id == self.agent_id:
            return
        
        self.help_requests_received += 1
        requester_id = msg.sender_id
        position = Position(*msg.content["position"])
        reason = msg.content["reason"]
        
        print(f"[{self.agent_id}] 📨 收到求助：{requester_id} 在 {position} ({reason})")
        
        # 记录求助者，以后可以主动分享
        self.known_explorers.add(requester_id)
        
        # 检查自己是否有有用的信息可以分享
        if requester_id in self.shared_maps:
            shared_data = self.shared_maps[requester_id]
            # 找到离求助位置最近的已知路径
            nearby_paths = [
                (pos, state) for pos, state in shared_data
                if abs(pos[0] - position.x) <= 2 and abs(pos[1] - position.y) <= 2
            ]
            
            if nearby_paths:
                await self._send_help_response(requester_id, nearby_paths)
                return
        
        # 如果没有具体信息，发送鼓励消息
        response_content = {
            "requester_id": requester_id,
            "helper_id": self.agent_id,
            "has_useful_info": False,
            "message": "收到求助，但我这边也没有附近的路径信息，加油！",
        }
        
        response_msg = msg.create_reply(MessageType.HELP_RESPONSE, response_content)
        await send_message(response_msg)
        print(f"[{self.agent_id}] → {requester_id}: 发送鼓励消息")
    
    async def _send_help_response(self, requester_id: str, nearby_paths: List[Tuple[Tuple[int, int], str]]):
        """发送有帮助的响应"""
        from utils.mailbox import send_message
        
        response_content = {
            "requester_id": requester_id,
            "helper_id": self.agent_id,
            "has_useful_info": True,
            "nearby_paths": [
                {"position": pos, "state": state} for pos, state in nearby_paths
            ],
            "message": f"发现 {len(nearby_paths)} 个附近的路径点，供你参考！",
        }
        
        # 创建回复消息
        msg = Message(
            type=MessageType.HELP_RESPONSE,
            sender_id=self.agent_id,
            receiver_id=requester_id,
            timestamp=datetime.now(),
            content=response_content,
        )
        
        await send_message(msg)
        print(f"[{self.agent_id}] → {requester_id}: 发送 {len(nearby_paths)} 个路径点")
    
    async def _handle_help_response(self, msg: Message):
        """处理收到的帮助响应"""
        helper_id = msg.sender_id
        has_info = msg.content.get("has_useful_info", False)
        message = msg.content.get("message", "")
        
        print(f"[{self.agent_id}] 📨 收到 {helper_id} 的帮助响应：{message}")
        
        if has_info:
            nearby_paths = msg.content.get("nearby_paths", [])
            print(f"[{self.agent_id}] 获得 {len(nearby_paths)} 个路径点信息")
            # 这里可以处理获得的路径信息，用于后续探索
    
    async def _share_discovery(self, position: Position, valid_neighbors: List[Position]):
        """分享新发现（分支点）"""
        from utils.mailbox import broadcast_message
        
        content = {
            "discovery_type": "branch_point",
            "position": (position.x, position.y),
            "valid_neighbors": [(p.x, p.y) for p in valid_neighbors],
            "discoverer_id": self.agent_id,
            "timestamp": datetime.now().isoformat(),
        }
        
        msg = Message(
            type=MessageType.MAP_SHARE,
            sender_id=self.agent_id,
            receiver_id="broadcast",
            timestamp=datetime.now(),
            content=content,
        )
        
        await broadcast_message(msg)
        print(f"[{self.agent_id}] 📢 分享发现：分支点 {position}, {len(valid_neighbors)} 个方向")
    
    async def _handle_map_share(self, msg: Message):
        """处理其他 Explorer 分享的地图信息"""
        if msg.sender_id == self.agent_id:
            return
        
        sender_id = msg.sender_id
        self.known_explorers.add(sender_id)
        
        discovery_type = msg.content.get("discovery_type", "unknown")
        
        if discovery_type == "branch_point":
            position = tuple(msg.content["position"])
            valid_neighbors = [tuple(p) for p in msg.content["valid_neighbors"]]
            
            # 保存分享的信息
            if sender_id not in self.shared_maps:
                self.shared_maps[sender_id] = []
            
            self.shared_maps[sender_id].append((position, "branch"))
            for neighbor in valid_neighbors:
                self.shared_maps[sender_id].append((neighbor, "path"))
            
            print(f"[{self.agent_id}] 📥 收到 {sender_id} 分享的分支点：{position}")
    
    def get_collaboration_stats(self) -> dict:
        """获取协作统计"""
        return {
            "known_explorers": list(self.known_explorers),
            "help_requests_sent": self.help_requests_sent,
            "help_requests_received": self.help_requests_received,
            "shared_maps_count": len(self.shared_maps),
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
        
        # 打印协作统计
        stats = self.get_collaboration_stats()
        print(f"\n[{self.agent_id}] 📊 协作统计:")
        print(f"   认识的 Explorer: {stats['known_explorers']}")
        print(f"   发送求助：{stats['help_requests_sent']} 次")
        print(f"   收到求助：{stats['help_requests_received']} 次")
        print(f"   共享地图：{stats['shared_maps_count']} 个")
