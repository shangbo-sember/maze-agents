#!/usr/bin/env python3
"""
快速演示版本 - 使用小迷宫
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from agents.types import MazeState, Position, CellState
from agents.coordinator import CoordinatorAgent
from agents.explorer import ExplorerAgent
from agents.memory import MemoryAgent
from utils.mailbox import mailbox_system, receive_message, broadcast_message
from utils.visualizer import MazeVisualizer
from agents.messages import MessageType


async def demo():
    """演示迷宫求解"""
    
    print("\n" + "=" * 60)
    print("  🧩 Maze Agents 快速演示")
    print("=" * 60)
    
    # 创建小迷宫配置
    maze_config = {
        "name": "Demo Maze",
        "start": [0, 0],
        "end": [4, 4],
        "grid": {
            "(1, 0)": "wall",
            "(1, 1)": "wall",
            "(1, 2)": "wall",
            "(3, 2)": "wall",
            "(3, 3)": "wall",
            "(3, 4)": "wall",
        }
    }
    
    # 初始化 Memory
    memory = MemoryAgent("memory")
    await memory.initialize(maze_config)
    
    # 创建 MazeState
    maze_state = MazeState(
        grid={},
        start=memory.start,
        end=memory.end,
        current_pos=memory.start,
        path_history=[memory.start],
    )
    
    # 注册 Agent
    mailbox_system.register_agent("coordinator")
    mailbox_system.register_agent("memory")
    
    # 创建 Coordinator
    coordinator = CoordinatorAgent("coordinator")
    
    print(f"\n迷宫配置:")
    print(f"  大小：5x5")
    print(f"  起点：{maze_state.start}")
    print(f"  终点：{maze_state.end}")
    print(f"  墙壁：{len(maze_config['grid'])}")
    print()
    
    # 渲染初始状态
    visualizer = MazeVisualizer(maze_state)
    print("初始迷宫:")
    print(visualizer.render_simple())
    print()
    
    # 启动 Coordinator
    await coordinator.start(maze_state)
    
    # 创建 2 个 Explorer
    explorers = []
    for i in range(2):
        explorer = ExplorerAgent(f"explorer_{i}", maze_accessor=memory)
        mailbox_system.register_agent(f"explorer_{i}")
        explorers.append(explorer)
    
    # 启动任务
    coordinator_task = asyncio.create_task(coordinator.run())
    explorer_tasks = [asyncio.create_task(e.run()) for e in explorers]
    memory_task = asyncio.create_task(memory.run())
    
    print("开始求解...\n")
    
    start_time = datetime.now()
    solved = False
    
    try:
        while not solved:
            # 检查超时
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > 15:
                print("⏱️  超时 (15 秒)")
                break
            
            # 监听消息
            msg = await receive_message("coordinator", timeout=0.5)
            if msg:
                if msg.type == MessageType.MAZE_SOLVED:
                    solved = True
                    print(f"\n{'='*50}")
                    print(f"🎉 迷宫已解决!")
                    print(f"路径长度：{msg.content['length']}")
                    print(f"路径：{msg.content['solution']}")
                    print(f"{'='*50}\n")
                    
                    # 更新最终状态
                    solution_positions = [Position(*p) for p in msg.content['solution']]
                    for pos in solution_positions:
                        maze_state.set_cell(pos, CellState.SOLUTION)
                    maze_state.solution = solution_positions
                    maze_state.is_solved = True
                    
                    # 渲染最终状态
                    visualizer.maze_state = maze_state
                    print("解决路径:")
                    print(visualizer.render_simple())
                    print()
                    break
                
                elif msg.type == MessageType.EXPLORE_RESULT:
                    cells = len(msg.content.get('cells_explored', []))
                    paths = len(msg.content.get('paths_found', []))
                    if cells > 0 or paths > 0:
                        print(f"[探索] 探索={cells}, 找到路径={paths}")
            
            # 定期渲染状态
            visualizer.maze_state = coordinator.maze_state
            if elapsed % 2 < 0.5:
                dead_ends = sum(1 for s in maze_state.grid.values() if s == CellState.DEAD_END)
                print(f"[状态] 已访问={len(maze_state.path_history)}, 死路={dead_ends}")
            
            await asyncio.sleep(0.1)
    
    except asyncio.CancelledError:
        print("\n求解被取消")
    
    finally:
        # 停止所有任务
        coordinator.running = False
        memory.running = False
        for e in explorers:
            e.running = False
        
        for task in [coordinator_task, memory_task] + explorer_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    # 统计
    stats = mailbox_system.get_stats()
    print(f"\n统计信息:")
    print(f"  消息总数：{stats['total_messages']}")
    print(f"  Explorer 数量：{len(explorers)}")
    print(f"  耗时：{elapsed:.2f}秒")
    print()


if __name__ == "__main__":
    asyncio.run(demo())
