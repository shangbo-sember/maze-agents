#!/usr/bin/env python3
"""
详细演示版本 - 复杂迷宫 + 完整路径探索过程打印
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Set, Dict

sys.path.insert(0, str(Path(__file__).parent))

from agents.types import MazeState, Position, CellState
from agents.coordinator import CoordinatorAgent
from agents.explorer import ExplorerAgent
from agents.memory import MemoryAgent
from utils.mailbox import mailbox_system, receive_message, broadcast_message
from utils.visualizer import MazeVisualizer
from agents.messages import MessageType, ExploreResult, PathFound
from mazes import load_maze


class VerboseMazeSolver:
    """详细输出的迷宫求解器"""
    
    def __init__(self, maze_config: dict):
        self.maze_config = maze_config
        self.coordinator = CoordinatorAgent("coordinator")
        self.memory = MemoryAgent("memory")
        self.explorers = []
        self.explorer_tasks = []
        self.running = False
        
        # 路径追踪
        self.all_explored_cells: Set[tuple] = set()
        self.all_paths: List[List[tuple]] = []
        self.dead_ends_found: Set[tuple] = set()
        self.iteration = 0
        
        # 性能统计
        self.start_time = None
        self.messages_sent = 0
        self.messages_received = 0
    
    async def initialize(self):
        """初始化"""
        print("\n" + "=" * 80)
        print("  🧩 Maze Agents - 复杂迷宫求解（详细模式）")
        print("=" * 80)
        
        # 初始化 Memory
        await self.memory.initialize(self.maze_config)
        
        # 创建 MazeState
        maze_state = MazeState(
            grid={},
            start=self.memory.start,
            end=self.memory.end,
            current_pos=self.memory.start,
            path_history=[self.memory.start],
        )
        
        # 注册 Agent
        mailbox_system.register_agent("coordinator")
        mailbox_system.register_agent("memory")
        
        # 设置 Verifier
        verifier = None  # 简化版本暂不使用
        
        print(f"\n📊 迷宫配置:")
        print(f"   大小：15x15")
        print(f"   起点：{maze_state.start}")
        print(f"   终点：{maze_state.end}")
        print(f"   预定义墙壁：{len(self.maze_config.get('grid', {}))}")
        print(f"   难度：{self.maze_config.get('difficulty', 'unknown')}")
        
        return maze_state
    
    def print_maze_state(self, maze_state: MazeState, title: str = "当前迷宫状态"):
        """打印迷宫状态"""
        print(f"\n{'─' * 80}")
        print(f"  {title}")
        print(f"{'─' * 80}")
        
        visualizer = MazeVisualizer(maze_state)
        print(visualizer.render_simple())
        
        # 统计信息
        explored = sum(1 for s in maze_state.grid.values() if s != CellState.UNKNOWN)
        dead_ends = sum(1 for s in maze_state.grid.values() if s == CellState.DEAD_END)
        paths = sum(1 for s in maze_state.grid.values() if s == CellState.PATH)
        
        print(f"\n📈 统计：已探索={explored}, 路径={paths}, 死路={dead_ends}")
        print(f"   当前位置：{maze_state.current_pos}")
        print(f"   路径历史长度：{len(maze_state.path_history)}")
    
    async def spawn_explorer(self, explorer_id: int = None):
        """动态创建 Explorer"""
        if explorer_id is None:
            explorer_id = len(self.explorers)
        
        explorer = ExplorerAgent(
            f"explorer_{explorer_id}",
            maze_accessor=self.memory,
        )
        
        mailbox_system.register_agent(f"explorer_{explorer_id}")
        self.explorers.append(explorer)
        
        return explorer
    
    async def run(self, max_explorers: int = 15, timeout: float = 120.0):
        """运行求解器"""
        self.running = True
        self.start_time = datetime.now()
        
        # 初始化
        maze_state = await self.initialize()
        
        # 启动 Agent 任务
        coordinator_task = asyncio.create_task(self.coordinator.run(), name="coordinator")
        memory_task = asyncio.create_task(self.memory.run(), name="memory")
        
        # 启动初始 Explorer（4 个方向）
        explorer_tasks = []
        for i in range(min(4, max_explorers)):
            explorer = await self.spawn_explorer(i)
            task = asyncio.create_task(explorer.run(), name=f"explorer_{i}")
            explorer_tasks.append(task)
        
        # 启动 Coordinator
        await self.coordinator.start(maze_state)
        
        # 打印初始状态
        self.print_maze_state(maze_state, "初始迷宫状态")
        
        # 动态创建 Explorer 的管理器
        async def explorer_manager():
            explorer_count = len(self.explorers)
            while self.running and explorer_count < max_explorers:
                msg = await receive_message("coordinator", timeout=1.0)
                if msg and msg.type.value.startswith("explore"):
                    explorer = await self.spawn_explorer(explorer_count)
                    task = asyncio.create_task(explorer.run(), name=f"explorer_{explorer_count}")
                    explorer_tasks.append(task)
                    explorer_count += 1
                await asyncio.sleep(0.2)
        
        manager_task = asyncio.create_task(explorer_manager(), name="explorer_manager")
        
        print(f"\n🚀 开始求解...")
        print(f"   启动 {min(4, max_explorers)} 个初始 Explorer")
        print(f"   最大 Explorer 数量：{max_explorers}")
        print(f"   超时时间：{timeout}秒\n")
        
        solved = False
        try:
            while self.running:
                self.iteration += 1
                
                # 检查超时
                elapsed = (datetime.now() - self.start_time).total_seconds()
                if elapsed > timeout:
                    print(f"\n⏱️  超时 ({timeout}秒)")
                    break
                
                # 监听消息
                msg = await receive_message("coordinator", timeout=0.5)
                if msg:
                    self.messages_received += 1
                    await self._handle_message(msg, maze_state)
                    
                    if msg.type == MessageType.MAZE_SOLVED:
                        solved = True
                        break
                    elif msg.type == MessageType.MAZE_UNSOLVABLE:
                        break
                
                # 定期输出状态
                if self.iteration % 5 == 0:
                    dead_ends = sum(1 for s in maze_state.grid.values() if s == CellState.DEAD_END)
                    paths = sum(1 for s in maze_state.grid.values() if s == CellState.PATH)
                    print(f"[迭代 {self.iteration:3d}] 已访问={len(maze_state.path_history):3d}, "
                          f"路径={paths:2d}, 死路={dead_ends:2d}, "
                          f"Explorer={len(self.explorers):2d}, 消息={self.messages_received:3d}")
                
                await asyncio.sleep(0.1)
        
        except asyncio.CancelledError:
            print("\n求解被取消")
        
        finally:
            self.running = False
            
            # 停止所有任务
            for task in [coordinator_task, memory_task, manager_task] + explorer_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # 打印最终结果
        if solved:
            self._print_success(maze_state)
        elif maze_state.is_unsolvable:
            self._print_unsolvable()
        else:
            self._print_timeout()
        
        # 打印完整探索路径
        self._print_exploration_history()
    
    async def _handle_message(self, msg, maze_state):
        """处理消息并打印详细信息"""
        
        if msg.type == MessageType.EXPLORE_RESULT:
            data = ExploreResult.from_dict(msg.content)
            
            # 记录探索的单元格
            for pos_tuple, state in data.cells_explored:
                if pos_tuple not in self.all_explored_cells:
                    self.all_explored_cells.add(pos_tuple)
                    maze_state.set_cell(Position(*pos_tuple), CellState(state))
            
            # 记录死路
            for pos_tuple in data.dead_ends:
                if pos_tuple not in self.dead_ends_found:
                    self.dead_ends_found.add(pos_tuple)
                    maze_state.set_cell(Position(*pos_tuple), CellState.DEAD_END)
            
            # 记录路径
            if data.paths_found:
                path = [data.from_pos] + data.paths_found
                self.all_paths.append(path)
                for pos_tuple in data.paths_found:
                    maze_state.set_cell(Position(*pos_tuple), CellState.PATH)
            
            # 打印探索详情
            print(f"\n🔍 [探索] {msg.sender_id}:")
            print(f"   起点：{data.from_pos}, 方向：{data.direction}")
            print(f"   探索单元格：{len(data.cells_explored)} 个")
            for pos, state in data.cells_explored[:5]:  # 只显示前 5 个
                print(f"     → {pos}: {state}")
            if len(data.cells_explored) > 5:
                print(f"     ... 还有 {len(data.cells_explored) - 5} 个")
            
            if data.dead_ends:
                print(f"   发现死路：{data.dead_ends}")
            
            if data.paths_found:
                print(f"   找到路径：{data.paths_found}")
        
        elif msg.type == MessageType.PATH_FOUND:
            data = PathFound.from_dict(msg.content)
            print(f"\n🎯 [路径找到] {msg.sender_id}:")
            print(f"   路径长度：{data.length}")
            print(f"   路径：{data.path}")
            print(f"   到达终点：{data.reaches_end}")
            print(f"   置信度：{data.confidence:.0%}")
        
        elif msg.type == MessageType.DEAD_END_REPORT:
            print(f"\n❌ [死路报告] {msg.sender_id}:")
            print(f"   位置：{msg.content.get('position')}")
            print(f"   原因：{msg.content.get('reason')}")
            print(f"   尝试方向：{msg.content.get('tried_directions')}")
    
    def _print_success(self, maze_state: MazeState):
        """打印成功结果"""
        print("\n" + "=" * 80)
        print("  🎉 迷宫已解决!")
        print("=" * 80)
        
        solution = self.coordinator.maze_state.solution
        if solution:
            print(f"\n✅ 解决方案:")
            print(f"   路径长度：{len(solution)}")
            print(f"   路径坐标：")
            
            # 格式化打印路径
            for i, pos in enumerate(solution):
                if isinstance(pos, Position):
                    print(f"      {i+1:2d}. ({pos.x:2d}, {pos.y:2d})")
                else:
                    print(f"      {i+1:2d}. {pos}")
            
            # 打印路径可视化
            print(f"\n📍 路径可视化:")
            path_strs = []
            for p in solution[:10]:
                if isinstance(p, Position):
                    path_strs.append(f"({p.x},{p.y})")
                else:
                    path_strs.append(f"({p[0]},{p[1]})")
            print("   " + " → ".join(path_strs))
            if len(solution) > 10:
                last_p = solution[-1]
                if isinstance(last_p, Position):
                    print("   ... → " + f"({last_p.x},{last_p.y})")
                else:
                    print("   ... → " + f"({last_p[0]},{last_p[1]})")
        
        # 打印最终迷宫状态
        self.print_maze_state(maze_state, "最终迷宫状态（含解决方案）")
    
    def _print_unsolvable(self):
        """打印无解结果"""
        print("\n" + "=" * 80)
        print("  ❌ 迷宫无解")
        print("=" * 80)
    
    def _print_timeout(self):
        """打印超时结果"""
        print("\n" + "=" * 80)
        print("  ⏱️  求解超时")
        print("=" * 80)
    
    def _print_exploration_history(self):
        """打印完整探索历史"""
        print("\n" + "=" * 80)
        print("  📊 探索历史统计")
        print("=" * 80)
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        print(f"\n⏱️  耗时：{elapsed:.2f}秒")
        print(f"📧 消息接收：{self.messages_received}条")
        print(f"🔍 探索单元格：{len(self.all_explored_cells)}个")
        print(f"🛤️  发现路径：{len(self.all_paths)}条")
        print(f"❌ 发现死路：{len(self.dead_ends_found)}个")
        print(f"🤖 Explorer 总数：{len(self.explorers)}个")
        
        # 打印邮箱统计
        stats = mailbox_system.get_stats()
        print(f"\n📮 邮箱系统统计:")
        print(f"   注册 Agent: {stats['registered_agents']}")
        print(f"   活跃 Agent: {stats['active_agents']}")
        print(f"   总消息数：{stats['total_messages']}")
        print(f"   待处理消息：{stats['pending_messages']}")
        
        print("\n" + "=" * 80)


async def main():
    """主函数"""
    print("\n加载复杂迷宫配置...")
    
    try:
        maze_config = load_maze("complex_maze.json")
        print(f"✓ 加载成功：{maze_config['name']}")
    except FileNotFoundError:
        print("✗ 复杂迷宫文件不存在，使用随机迷宫")
        from mazes import create_random_maze
        maze_config = create_random_maze(size=15, wall_density=0.3)
    
    # 创建求解器
    solver = VerboseMazeSolver(maze_config)
    
    # 运行
    await solver.run(
        max_explorers=15,
        timeout=90.0,
    )


if __name__ == "__main__":
    asyncio.run(main())
