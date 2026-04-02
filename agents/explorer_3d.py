"""
3D Explorer Agent - 带详细思考日志
"""

import asyncio
from typing import List, Tuple, Optional
from datetime import datetime

from agents.types_3d import Position3D, CellState3D, AgentRole, ExplorerThought, Direction3D
from agents.messages import Message, MessageType


class ExplorerAgent3D:
    """
    3D 探索者 Agent（详细思考日志版）
    
    每次决策都会记录：
    1. 当前位置和方向
    2. 考虑的所有选项
    3. 排除某些选项的原因
    4. 最终决策和置信度
    """
    
    def __init__(self, agent_id: str, maze_accessor, step_counter: list):
        self.agent_id = agent_id
        self.role = AgentRole.EXPLORER
        self.mailbox: asyncio.Queue = asyncio.Queue()
        self.maze_accessor = maze_accessor
        self.current_task: Optional[asyncio.Task] = None
        self.running = True
        self.exploring = False
        self.step_counter = step_counter  # 共享计数器
        self.thoughts: List[ExplorerThought] = []
        
    async def start(self):
        """启动 Explorer"""
        print(f"[{self.agent_id}] 🚀 Explorer 3D 启动")
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
        print(f"[{self.agent_id}] 🛑 Explorer 3D 停止")
    
    async def handle_message(self, msg: Message):
        """处理接收到的消息"""
        if msg.type == MessageType.EXPLORE_REQUEST:
            await self._handle_explore_request(msg)
        elif msg.type == MessageType.EXPLORE_CANCEL:
            await self._handle_explore_cancel(msg)
    
    async def _handle_explore_request(self, msg: Message):
        """处理探索请求"""
        if self.exploring:
            print(f"[{self.agent_id}] ⚠️ 正在探索中，忽略新请求")
            return
        
        data = msg.content
        from_pos = Position3D(*data["from_pos"])
        direction = data["direction"]
        max_depth = data.get("max_depth", 10)
        
        print(f"\n[{self.agent_id}] 📨 收到探索请求:")
        print(f"    起点：{from_pos}")
        print(f"    方向：{direction}")
        print(f"    最大深度：{max_depth}")
        
        self.exploring = True
        self.current_task = asyncio.create_task(
            self._explore_with_thinking(from_pos, direction, max_depth, msg)
        )
    
    async def _explore_with_thinking(self, from_pos: Position3D, direction: str,
                                      max_depth: int, request_msg: Message):
        """带详细思考日志的探索"""
        
        cells_explored = []
        dead_ends = []
        paths_found = []
        
        direction_offsets = {
            "up": (0, 0, -1),
            "down": (0, 0, 1),
            "left": (-1, 0, 0),
            "right": (1, 0, 0),
            "front": (0, -1, 0),
            "back": (0, 1, 0),
            "forward": (0, 1, 0),  # 默认向后
        }
        
        dx, dy, dz = direction_offsets.get(direction, (0, 1, 0))
        
        current_pos = from_pos
        depth = 0
        
        print(f"\n{'='*80}")
        print(f"  🔍 [{self.agent_id}] 开始探索")
        print(f"{'='*80}")
        
        try:
            while depth < max_depth and self.running and self.exploring:
                self.step_counter[0] += 1
                step = self.step_counter[0]
                
                next_pos = Position3D(
                    current_pos.x + dx,
                    current_pos.y + dy,
                    current_pos.z + dz
                )
                
                # 获取单元格状态
                cell_state = await self.maze_accessor.get_cell(next_pos)
                
                # 记录思考过程
                thought = f"准备移动到 {next_pos}，方向={direction}"
                alternatives = []
                decision = f"继续向 {direction} 移动"
                confidence = 1.0
                
                print(f"\n【步骤 {step:3d}】[{self.agent_id}]")
                print(f"  📍 当前位置：{current_pos}")
                print(f"  🧭 目标方向：{direction}")
                print(f"  🎯 下一个位置：{next_pos}")
                
                if cell_state == CellState3D.WALL:
                    # 遇到墙壁
                    thought = f"检测到墙壁在 {next_pos}"
                    
                    # 考虑其他方向
                    print(f"  ⚠️  检测到墙壁！")
                    print(f"  💭 思考：需要改变方向")
                    
                    # 检查所有可能的方向
                    for dir_name, (ox, oy, oz) in direction_offsets.items():
                        if dir_name == direction:
                            continue
                        alt_pos = Position3D(current_pos.x + ox, current_pos.y + oy, current_pos.z + oz)
                        alt_state = await self.maze_accessor.get_cell(alt_pos)
                        if alt_state != CellState3D.WALL:
                            alternatives.append(dir_name)
                            print(f"     可选方向：{dir_name} → {alt_pos} (状态={alt_state.value})")
                    
                    if alternatives:
                        decision = f"墙壁阻挡，建议尝试方向：{', '.join(alternatives)}"
                        confidence = 0.8
                    else:
                        decision = "死路！所有方向都被阻挡"
                        confidence = 1.0
                        dead_ends.append(current_pos)
                    
                    # 记录思考
                    self.thoughts.append(ExplorerThought(
                        step=step,
                        current_pos=current_pos,
                        direction=direction,
                        cell_state=cell_state,
                        thought=thought,
                        decision=decision,
                        alternatives_considered=alternatives,
                        confidence=confidence,
                    ))
                    
                    break
                    
                elif cell_state == CellState3D.DEAD_END:
                    thought = f"已知死路在 {next_pos}"
                    print(f"  ⚠️  已知死路")
                    dead_ends.append(current_pos)
                    break
                    
                elif cell_state == CellState3D.VISITED:
                    thought = f"已访问位置 {next_pos}，可能有循环"
                    print(f"  ℹ️  已访问过，可能有循环")
                    
                    # 考虑是否继续
                    decision = "继续探索（可能有新发现）"
                    confidence = 0.5
                    
                    cells_explored.append((next_pos, CellState3D.VISITED))
                    depth += 1
                    current_pos = next_pos
                    continue
                    
                else:
                    # 新路径
                    thought = f"发现新路径 {next_pos}，状态={cell_state.value}"
                    print(f"  ✅ 新路径！状态={cell_state.value}")
                    
                    cells_explored.append((next_pos, cell_state))
                    paths_found.append(next_pos)
                    depth += 1
                    current_pos = next_pos
                    
                    # 检查是否到达终点
                    if await self.maze_accessor.is_end(next_pos):
                        print(f"  🎉 到达终点！{next_pos}")
                        thought = f"到达终点 {next_pos}！"
                        decision = "报告路径发现"
                        confidence = 1.0
                        
                        self.thoughts.append(ExplorerThought(
                            step=step,
                            current_pos=current_pos,
                            direction=direction,
                            cell_state=cell_state,
                            thought=thought,
                            decision=decision,
                            confidence=confidence,
                        ))
                        
                        await self._report_path_found(
                            request_msg, cells_explored, dead_ends, paths_found
                        )
                        return
                    
                    # 检查分支
                    neighbors = next_pos.neighbors()
                    valid_neighbors = []
                    for neighbor in neighbors:
                        state = await self.maze_accessor.get_cell(neighbor)
                        if state not in (CellState3D.WALL, CellState3D.DEAD_END, CellState3D.VISITED):
                            valid_neighbors.append(neighbor)
                    
                    if len(valid_neighbors) > 1:
                        print(f"  🔀 发现分支点！{len(valid_neighbors)} 个可选方向")
                        thought = f"分支点 {next_pos}，{len(valid_neighbors)} 个方向可选"
                        alternatives = [str(n) for n in valid_neighbors]
                        decision = "报告 Coordinator 决策"
                        confidence = 0.9
                        
                        self.thoughts.append(ExplorerThought(
                            step=step,
                            current_pos=current_pos,
                            direction=direction,
                            cell_state=cell_state,
                            thought=thought,
                            decision=decision,
                            alternatives_considered=alternatives,
                            confidence=confidence,
                        ))
                        break
                    
                    decision = f"继续向 {direction} 探索"
                    confidence = 0.95
                
                # 记录思考
                self.thoughts.append(ExplorerThought(
                    step=step,
                    current_pos=current_pos,
                    direction=direction,
                    cell_state=cell_state,
                    thought=thought,
                    decision=decision,
                    alternatives_considered=alternatives,
                    confidence=confidence,
                ))
                
                await asyncio.sleep(0.2)  # 模拟思考时间
            
            # 报告探索结果
            await self._report_explore_result(
                request_msg, cells_explored, dead_ends, paths_found
            )
            
        except asyncio.CancelledError:
            print(f"[{self.agent_id}] ❌ 探索被取消")
            raise
        finally:
            self.exploring = False
        
        print(f"\n{'='*80}")
        print(f"  📊 [{self.agent_id}] 探索完成")
        print(f"     探索单元格：{len(cells_explored)}")
        print(f"     发现路径：{len(paths_found)}")
        print(f"     死路：{len(dead_ends)}")
        print(f"     思考记录：{len(self.thoughts)} 条")
        print(f"{'='*80}\n")
    
    async def _report_explore_result(self, request_msg: Message,
                                     cells_explored, dead_ends, paths_found):
        """报告探索结果"""
        from utils.mailbox import send_message
        from agents.messages import ExploreResult
        
        content = ExploreResult(
            from_pos=request_msg.content["from_pos"],
            direction=request_msg.content["direction"],
            cells_explored=[((pos.x, pos.y, pos.z), state.value) for pos, state in cells_explored],
            dead_ends=[(pos.x, pos.y, pos.z) for pos in dead_ends],
            paths_found=[(pos.x, pos.y, pos.z) for pos in paths_found],
        ).to_dict()
        
        msg = request_msg.create_reply(MessageType.EXPLORE_RESULT, content)
        await send_message(msg)
    
    async def _report_path_found(self, request_msg: Message,
                                 cells_explored, dead_ends, paths_found):
        """报告找到路径"""
        from utils.mailbox import send_message
        from agents.messages import PathFound
        
        full_path = [Position3D(*request_msg.content["from_pos"])] + paths_found
        
        content = PathFound(
            path=[(pos.x, pos.y, pos.z) for pos in full_path],
            length=len(full_path),
            confidence=1.0,
            reaches_end=True,
        ).to_dict()
        
        msg = request_msg.create_reply(MessageType.PATH_FOUND, content)
        await send_message(msg)
    
    async def _handle_explore_cancel(self, msg: Message):
        """处理取消探索"""
        print(f"[{self.agent_id}] 🛑 收到取消请求：{msg.content.get('reason', 'unknown')}")
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
