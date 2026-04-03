"""
协作迷宫 Agent - 每个 Agent 独立运行
"""

import asyncio
import random
from typing import Optional, List, Dict
from datetime import datetime

from .types import (
    AgentState, Position, MazeConfig, StateMessage, MessageType,
    Gate, GateType, SkillType, CellState, CollaborationHub
)
from .skills import SkillExecutor, GateGenerator, SkillResult


class MazeAgent:
    """
    迷宫 Agent
    
    特点：
    - 独立上下文（不共享内存）
    - 只能通过 Hub 通信
    - 有自己的 skill 池
    - 处理自己的迷宫
    """
    
    def __init__(self, agent_id: str, config: MazeConfig, hub: CollaborationHub):
        self.agent_id = agent_id
        self.config = config
        self.hub = hub
        
        # Skill 执行器和关卡生成器（必须在迷宫初始化前）
        self.skill_executor = SkillExecutor(agent_id)
        self.gate_generator = GateGenerator(difficulty=2)
        
        # 独立状态（不共享）
        self.state = AgentState(
            agent_id=agent_id,
            maze_id=config.maze_id,
            current_pos=config.start_pos,
            path_history=[config.start_pos],
            available_skills=self._get_agent_skills(),
        )
        
        # 迷宫网格
        self.grid: Dict[Position, CellState] = {}
        self._initialize_maze()
        
        # 运行状态
        self.running = False
        self.steps = 0
        self.max_steps = 500
        
        # 日志
        self.thought_log: List[Dict] = []
    
    def _get_agent_skills(self) -> List[SkillType]:
        """获取 Agent 的初始 skill（每个 Agent 不同）"""
        skill_map = {
            "agent_1": [SkillType.MATH_COMPUTATION],
            "agent_2": [SkillType.LOGICAL_REASONING],
            "agent_3": [SkillType.CIPHER_DECRYPTION],
            "agent_4": [SkillType.PATTERN_RECOGNITION],
        }
        return skill_map.get(self.agent_id, [SkillType.MATH_COMPUTATION])
    
    def _initialize_maze(self):
        """初始化迷宫网格"""
        for x in range(self.config.width):
            for y in range(self.config.height):
                pos = Position(x, y)
                
                # 随机生成关卡
                if random.random() < self.config.gate_density:
                    gate_type = self._random_gate_type()
                    gate = self.gate_generator.generate_gate((x, y), gate_type)
                    
                    cell = CellState(
                        pos=pos,
                        gate=gate,
                        required_skill=gate.required_skill,
                    )
                else:
                    cell = CellState(pos=pos)
                
                self.grid[pos] = cell
    
    def _random_gate_type(self) -> GateType:
        """随机关卡类型"""
        types = [GateType.MATH, GateType.LOGIC, GateType.CIPHER, GateType.PUZZLE]
        
        # 10% 概率生成协作关卡
        if random.random() < 0.1:
            return GateType.COLLABORATION
        
        return random.choice(types)
    
    async def run(self):
        """运行 Agent"""
        self.running = True
        print(f"\n🤖 [{self.agent_id}] 启动")
        print(f"   迷宫：{self.config.width}x{self.config.height}")
        print(f"   起点：{self.state.current_pos}")
        print(f"   终点：{self.config.end_pos}")
        print(f"   初始 skills: {[s.value for s in self.state.available_skills]}")
        
        step = 0
        while self.running and step < self.max_steps:
            step += 1
            self.steps = step
            
            # 检查是否到达终点
            if self.state.current_pos == self.config.end_pos:
                await self._on_maze_solved()
                break
            
            # 处理 Hub 消息
            await self._process_hub_messages()
            
            # 执行一步
            await self._take_step()
            
            # 发送状态更新
            await self._send_state_update()
            
            await asyncio.sleep(0.3)
        
        self.running = False
        print(f"\n🏁 [{self.agent_id}] 停止，总步数：{step}")
    
    async def _process_hub_messages(self):
        """处理 Hub 消息"""
        messages = self.hub.get_messages_for(self.agent_id)
        
        for msg in messages:
            await self._handle_message(msg)
        
        self.hub.clear_processed(self.agent_id)
    
    async def _handle_message(self, msg: StateMessage):
        """处理单条消息"""
        print(f"\n📨 [{self.agent_id}] 收到消息:")
        print(f"   类型：{msg.message_type.value}")
        print(f"   发送者：{msg.sender_id}")
        
        if msg.message_type == MessageType.HELP_REQUEST:
            # 其他 Agent 请求帮助
            await self._handle_help_request(msg)
        
        elif msg.message_type == MessageType.SKILL_SHARE:
            # 收到共享的 skill
            await self._handle_skill_share(msg)
        
        elif msg.message_type == MessageType.HELP_RESPONSE:
            # 收到帮助响应
            if msg.shared_skill:
                self.state.shared_skills[msg.sender_id] = msg.shared_skill
                print(f"   ✅ 收到来自 {msg.sender_id} 的 skill: {msg.shared_skill.value}")
    
    async def _handle_help_request(self, msg: StateMessage):
        """处理帮助请求"""
        if msg.required_skill and msg.required_skill in self.state.available_skills:
            # 我有需要的 skill，分享
            share_msg = StateMessage(
                message_type=MessageType.SKILL_SHARE,
                sender_id=self.agent_id,
                receiver_id=msg.sender_id,
                shared_skill=msg.required_skill,
                help_request=f"Sharing {msg.required_skill.value} skill",
            )
            self.hub.send_to(share_msg, msg.sender_id)
            print(f"   ✅ 分享 skill {msg.required_skill.value} 给 {msg.sender_id}")
    
    async def _handle_skill_share(self, msg: StateMessage):
        """处理 skill 分享"""
        if msg.shared_skill:
            self.state.shared_skills[msg.sender_id] = msg.shared_skill
            print(f"   ✅ 学会新 skill: {msg.shared_skill.value} (来自 {msg.sender_id})")
    
    async def _take_step(self):
        """执行一步"""
        current_cell = self.grid.get(self.state.current_pos)
        
        # 检查是否有未解决的关卡
        if current_cell and current_cell.gate and not current_cell.gate.is_solved:
            solved = await self._solve_gate(current_cell.gate)
            if not solved:
                # 卡住了，请求帮助
                await self._request_help(current_cell.gate)
                return
        
        # 移动到下一个位置
        next_pos = self._choose_next_position()
        
        if next_pos:
            self._log_thought(
                step=self.steps,
                thought=f"从 {self.state.current_pos} 移动到 {next_pos}",
                decision="move",
                data={"from": str(self.state.current_pos), "to": str(next_pos)}
            )
            
            self.state.current_pos = next_pos
            self.state.path_history.append(next_pos)
            
            if next_pos in self.grid:
                self.grid[next_pos].is_visited = True
    
    async def _solve_gate(self, gate: Gate) -> bool:
        """解决关卡"""
        print(f"\n🔒 [{self.agent_id}] 遇到关卡:")
        print(f"   位置：{gate.gate_id}")
        print(f"   类型：{gate.gate_type.value}")
        print(f"   难度：{gate.difficulty}")
        print(f"   描述：{gate.description}")
        
        # 检查是否需要协作
        if gate.requires_collaboration:
            print(f"   ⚠️  需要协作！")
            return False
        
        # 检查是否有需要的 skill
        required_skill = gate.required_skill
        has_skill = (
            required_skill in self.state.available_skills or
            required_skill in [s for s in self.state.shared_skills.values()]
        )
        
        if not has_skill:
            print(f"   ❌ 缺少 skill: {required_skill.value if required_skill else 'unknown'}")
            return False
        
        # 执行 skill
        if gate.question:
            result = self.skill_executor.execute(required_skill, gate.question)
            
            self._log_thought(
                step=self.steps,
                thought=f"解决关卡 {gate.gate_id}",
                decision="use_skill",
                data={
                    "skill": required_skill.value,
                    "success": result.success,
                    "message": result.message,
                }
            )
            
            if result.success:
                gate.is_solved = True
                self.state.solved_gates.append(gate.gate_id)
                print(f"   ✅ 关卡解决！{result.message}")
                return True
            else:
                print(f"   ❌ 解决失败：{result.message}")
                return False
        
        # 没有具体问题，直接解决
        gate.is_solved = True
        self.state.solved_gates.append(gate.gate_id)
        print(f"   ✅ 关卡解决！")
        return True
    
    async def _request_help(self, gate: Gate):
        """请求帮助"""
        self.state.is_stuck = True
        self.state.stuck_at = self.state.current_pos
        self.state.help_requests += 1
        
        help_msg = StateMessage(
            message_type=MessageType.HELP_REQUEST,
            sender_id=self.agent_id,
            required_skill=gate.required_skill,
            help_request=f"Stuck at {self.state.current_pos}, need {gate.required_skill.value if gate.required_skill else 'help'}",
            current_pos=(self.state.current_pos.x, self.state.current_pos.y),
        )
        
        self.hub.broadcast(help_msg)
        
        print(f"\n🆘 [{self.agent_id}] 请求帮助:")
        print(f"   位置：{self.state.current_pos}")
        print(f"   需要：{gate.required_skill.value if gate.required_skill else 'help'}")
    
    def _choose_next_position(self) -> Optional[Position]:
        """选择下一个位置"""
        current = self.state.current_pos
        neighbors = current.neighbors()
        
        # 过滤有效位置
        valid = []
        for neighbor in neighbors:
            if 0 <= neighbor.x < self.config.width and 0 <= neighbor.y < self.config.height:
                if neighbor not in [p for p in self.state.path_history[-5:]]:  # 避免短循环
                    valid.append(neighbor)
        
        if not valid:
            # 回溯
            if len(self.state.path_history) > 1:
                return self.state.path_history[-2]
            return None
        
        # 优先选择未访问的
        unvisited = [n for n in valid if n in self.grid and not self.grid[n].is_visited]
        if unvisited:
            return random.choice(unvisited)
        
        return random.choice(valid)
    
    async def _send_state_update(self):
        """发送状态更新"""
        progress = len(self.state.solved_gates) / max(1, len(self.grid)) * 100
        
        state_msg = StateMessage(
            message_type=MessageType.PROGRESS_REPORT,
            sender_id=self.agent_id,
            current_pos=(self.state.current_pos.x, self.state.current_pos.y),
            is_stuck=self.state.is_stuck,
            progress_percent=progress,
        )
        
        self.hub.send_to(state_msg, "hub")
    
    async def _on_maze_solved(self):
        """迷宫解决"""
        print(f"\n🎉 [{self.agent_id}] 迷宫解决!")
        print(f"   总步数：{self.steps}")
        print(f"   解决关卡：{len(self.state.solved_gates)}")
        print(f"   路径长度：{len(self.state.path_history)}")
        
        solved_msg = StateMessage(
            message_type=MessageType.MAZE_SOLVED,
            sender_id=self.agent_id,
            coordination_data={
                "steps": self.steps,
                "gates_solved": len(self.state.solved_gates),
                "path_length": len(self.state.path_history),
            }
        )
        
        self.hub.broadcast(solved_msg)
    
    def _log_thought(self, step: int, thought: str, decision: str, data: Dict = None):
        """记录思考日志"""
        self.thought_log.append({
            "step": step,
            "timestamp": datetime.now().isoformat(),
            "thought": thought,
            "decision": decision,
            "data": data or {},
        })
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "agent_id": self.agent_id,
            "maze_size": f"{self.config.width}x{self.config.height}",
            "steps": self.steps,
            "gates_solved": len(self.state.solved_gates),
            "path_length": len(self.state.path_history),
            "help_requests": self.state.help_requests,
            "skills_used": self.skill_executor.skill_usage_count,
            "shared_skills": len(self.state.shared_skills),
        }
