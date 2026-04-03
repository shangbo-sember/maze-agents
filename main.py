#!/usr/bin/env python3
"""
Maze Agents - 多 Agent 迷宫求解系统

基于 Claude Code 架构灵感
"""

import asyncio
import argparse
import signal
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from agents.types import MazeState, Position, CellState
from agents.coordinator import CoordinatorAgent
from agents.explorer import ExplorerAgent
from agents.memory import MemoryAgent
from agents.verifier import VerifierAgent
from utils.mailbox import mailbox_system, receive_message, broadcast_message
from utils.visualizer import MazeVisualizer, LiveRenderer
from mazes import load_maze, create_random_maze
from config import config


class MazeSolver:
    """迷宫求解器"""
    
    def __init__(self, maze_config: dict, enable_render: bool = True):
        self.maze_config = maze_config
        self.enable_render = enable_render
        self.running = False
        
        # 初始化 Agent
        self.coordinator = CoordinatorAgent("coordinator")
        self.memory = MemoryAgent("memory")
        self.verifier = VerifierAgent("verifier")
        self.explorers = []
        
        # 渲染器
        self.renderer = None
        
        # 结果
        self.solution = None
        self.start_time = None
        self.end_time = None
    
    async def initialize(self):
        """初始化"""
        print("\n" + "=" * 60)
        print("  🧩 Maze Agents - 多 Agent 迷宫求解系统")
        print("=" * 60)
        
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
        
        # 注册 Agent 到邮箱系统
        mailbox_system.register_agent("coordinator")
        mailbox_system.register_agent("memory")
        mailbox_system.register_agent("verifier")
        
        # 设置 Verifier 的 maze_accessor
        self.verifier.maze_accessor = self.memory
        
        # 初始化渲染
        if self.enable_render:
            self.renderer = LiveRenderer(maze_state)
        
        print(f"\n迷宫配置:")
        print(f"  起点：{maze_state.start}")
        print(f"  终点：{maze_state.end}")
        print(f"  预定义墙壁：{len(self.maze_config.get('grid', {}))}")
        print()
        
        return maze_state
    
    async def spawn_explorer(self, explorer_id: int = None):
        """动态创建 Explorer"""
        if explorer_id is None:
            explorer_id = len(self.explorers)
        
        explorer = ExplorerAgent(
            f"explorer_{explorer_id}",
            maze_accessor=self.memory,
        )
        
        # 让新 Explorer 知道已存在的其他 Explorer（启用协作）
        for existing in self.explorers:
            explorer.known_explorers.add(existing.agent_id)
            # 同步已知的 Explorer 列表
            existing.known_explorers.add(f"explorer_{explorer_id}")
        
        mailbox_system.register_agent(f"explorer_{explorer_id}")
        self.explorers.append(explorer)
        
        print(f"[系统] 创建 {explorer.agent_id}，已知 Explorer: {explorer.known_explorers}")
        
        return explorer
    
    async def run(self, max_explorers: int = 10, timeout: float = 60.0):
        """运行求解器"""
        self.running = True
        self.start_time = datetime.now()
        
        # 初始化
        maze_state = await self.initialize()
        
        # 启动 Coordinator
        coordinator_task = asyncio.create_task(
            self.coordinator.run(),
            name="coordinator"
        )
        
        # 启动 Memory
        memory_task = asyncio.create_task(
            self.memory.run(),
            name="memory"
        )
        
        # 启动 Verifier
        verifier_task = asyncio.create_task(
            self.verifier.run(),
            name="verifier"
        )
        
        # 启动初始 Explorer
        explorer_tasks = []
        for i in range(min(3, max_explorers)):
            explorer = await self.spawn_explorer(i)
            task = asyncio.create_task(explorer.run(), name=f"explorer_{i}")
            explorer_tasks.append(task)
        
        # 启动渲染
        if self.enable_render:
            await self.renderer.start()
        
        # 启动 Coordinator
        await self.coordinator.start(maze_state)
        
        # 动态创建 Explorer 的管理器
        async def explorer_manager():
            explorer_count = len(self.explorers)
            while self.running and explorer_count < max_explorers:
                # 检查 Coordinator 是否有新请求
                msg = await receive_message("coordinator", timeout=1.0)
                if msg and msg.type.value.startswith("explore"):
                    explorer = await self.spawn_explorer(explorer_count)
                    task = asyncio.create_task(explorer.run(), name=f"explorer_{explorer_count}")
                    explorer_tasks.append(task)
                    explorer_count += 1
                await asyncio.sleep(0.2)
        
        manager_task = asyncio.create_task(explorer_manager(), name="explorer_manager")
        
        # 监听完成信号
        print("开始求解...\n")
        print(f"[系统] 启动 {min(3, max_explorers)} 个初始 Explorer\n")
        
        iteration = 0
        try:
            while self.running:
                iteration += 1
                if iteration % 10 == 0:
                    print(f"[系统] 迭代 {iteration}, 已访问={len(self.memory.visited)}, Explorer={len(self.explorers)}")
                # 检查超时
                elapsed = (datetime.now() - self.start_time).total_seconds()
                if elapsed > timeout:
                    print(f"\n⏱️  超时 ({timeout}秒)")
                    break
                
                # 监听消息
                msg = await receive_message("coordinator", timeout=0.5)
                if msg:
                    if msg.type == MessageType.MAZE_SOLVED:
                        self.solution = msg.content["solution"]
                        self.end_time = datetime.now()
                        break
                    elif msg.type == MessageType.MAZE_UNSOLVABLE:
                        self.end_time = datetime.now()
                        break
                
                # 更新渲染
                if self.renderer:
                    self.renderer.update(self.coordinator.maze_state)
                
                await asyncio.sleep(0.1)
            
        except asyncio.CancelledError:
            print("\n求解被取消")
        
        finally:
            self.running = False
            
            # 停止所有任务
            for task in [coordinator_task, memory_task, verifier_task, manager_task]:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            for task in explorer_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            if self.renderer:
                await self.renderer.stop()
        
        # 打印结果
        await self._print_results()
    
    async def _print_results(self):
        """打印结果"""
        print("\n" + "=" * 60)
        print("  求解结果")
        print("=" * 60)
        
        if self.solution:
            print(f"\n✅ 迷宫已解决!")
            print(f"  路径长度：{len(self.solution)}")
            print(f"  路径：{self.solution}")
            
            # 打印统计
            if self.start_time and self.end_time:
                duration = (self.end_time - self.start_time).total_seconds()
                print(f"  耗时：{duration:.2f}秒")
            
            # 打印邮箱统计
            stats = mailbox_system.get_stats()
            print(f"  消息总数：{stats['total_messages']}")
            print(f"  Explorer 数量：{len(self.explorers)}")
            
            # 打印 Explorer 协作统计
            print(f"\n🤝 Explorer 协作统计:")
            for explorer in self.explorers:
                if hasattr(explorer, 'get_collaboration_stats'):
                    stats = explorer.get_collaboration_stats()
                    if stats['help_requests_sent'] > 0 or stats['help_requests_received'] > 0 or stats['shared_maps_count'] > 0:
                        print(f"    {explorer.agent_id}:")
                        print(f"      认识的 Explorer: {stats['known_explorers']}")
                        print(f"      发送求助：{stats['help_requests_sent']} 次")
                        print(f"      收到求助：{stats['help_requests_received']} 次")
                        print(f"      共享地图：{stats['shared_maps_count']} 个")
            
        elif self.coordinator.maze_state.is_unsolvable:
            print(f"\n❌ 迷宫无解")
        else:
            print(f"\n⏱️  求解未完成")
        
        # 保存渲染
        if self.renderer:
            visualizer = self.renderer.visualizer
            visualizer.save_render()
        
        print("\n" + "=" * 60)


# 导入 MessageType
from agents.messages import MessageType


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="多 Agent 迷宫求解系统")
    parser.add_argument("--maze", type=str, default="sample_maze.json",
                        help="迷宫配置文件")
    parser.add_argument("--random", action="store_true",
                        help="使用随机迷宫")
    parser.add_argument("--size", type=int, default=10,
                        help="随机迷宫大小")
    parser.add_argument("--density", type=float, default=0.2,
                        help="随机迷宫墙壁密度")
    parser.add_argument("--explorers", type=int, default=10,
                        help="最大 Explorer 数量")
    parser.add_argument("--timeout", type=float, default=60.0,
                        help="超时时间（秒）")
    parser.add_argument("--no-render", action="store_true",
                        help="禁用实时渲染")
    
    args = parser.parse_args()
    
    # 加载迷宫配置
    if args.random:
        maze_config = create_random_maze(args.size, args.density)
        print(f"使用随机迷宫：{args.size}x{args.size}, 密度={args.density}")
    else:
        try:
            maze_config = load_maze(args.maze)
            print(f"使用迷宫配置：{args.maze}")
        except FileNotFoundError:
            print(f"迷宫文件不存在：{args.maze}")
            maze_config = create_random_maze(args.size, args.density)
    
    # 创建求解器
    solver = MazeSolver(maze_config, enable_render=not args.no_render)
    
    # 设置信号处理
    def signal_handler(sig, frame):
        print("\n收到中断信号，正在停止...")
        solver.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # 运行
    await solver.run(
        max_explorers=args.explorers,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    asyncio.run(main())
