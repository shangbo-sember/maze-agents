#!/usr/bin/env python3
"""
快速复杂迷宫演示 - 打印探索路径
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from agents.types import Position, CellState, MazeState
from agents.messages import Message, MessageType, ExploreRequest
from utils.mailbox import mailbox_system, receive_message
from utils.visualizer import MazeVisualizer


async def complex_maze_demo():
    """复杂迷宫探索演示"""
    
    print("\n" + "=" * 80)
    print("  🧩 复杂迷宫探索 - 详细路径演示")
    print("=" * 80)
    
    # 创建复杂迷宫（15x15，多障碍）
    maze_config = {
        "name": "Complex Demo",
        "start": [0, 0],
        "end": [10, 10],
        "grid": {
            # 第一道墙
            "(2, 0)": "wall", "(2, 1)": "wall", "(2, 2)": "wall",
            # 第二道墙
            "(5, 3)": "wall", "(5, 4)": "wall", "(5, 5)": "wall", "(5, 6)": "wall",
            # 第三道墙
            "(8, 0)": "wall", "(8, 1)": "wall", "(8, 2)": "wall", "(8, 3)": "wall",
            # 第四道墙
            "(0, 7)": "wall", "(1, 7)": "wall", "(2, 7)": "wall", "(3, 7)": "wall",
            # 第五道墙
            "(6, 8)": "wall", "(6, 9)": "wall", "(6, 10)": "wall",
            # 终点周围的墙
            "(9, 9)": "wall", "(9, 10)": "wall", "(10, 9)": "wall",
        }
    }
    
    # 初始化状态
    maze_state = MazeState(
        grid={},
        start=Position(0, 0),
        end=Position(10, 10),
        current_pos=Position(0, 0),
        path_history=[Position(0, 0)],
    )
    
    # 注册 Agent
    mailbox_system.register_agent("coordinator")
    mailbox_system.register_agent("explorer_0")
    mailbox_system.register_agent("explorer_1")
    mailbox_system.register_agent("explorer_2")
    
    print(f"\n📊 迷宫配置:")
    print(f"   大小：11x11")
    print(f"   起点：{maze_state.start}")
    print(f"   终点：{maze_state.end}")
    print(f"   墙壁数量：{len(maze_config['grid'])}")
    
    # 打印初始迷宫
    visualizer = MazeVisualizer(maze_state)
    print(f"\n📍 初始迷宫:")
    print(visualizer.render_simple())
    
    # 模拟探索过程
    print(f"\n🚀 开始探索...\n")
    
    exploration_log = []
    current_pos = maze_state.start
    path = [current_pos]
    step = 0
    
    # 预定义的探索路径（模拟真实探索）
    exploration_steps = [
        # 第一阶段：向右探索
        (Position(1, 0), "path", "向右移动，避开左侧墙壁"),
        (Position(2, 0), "wall", "遇到墙壁！需要改变方向"),
        (Position(1, 1), "path", "向上移动，绕过墙壁"),
        (Position(1, 2), "path", "继续向上"),
        (Position(1, 3), "path", "继续向上"),
        
        # 第二阶段：向右绕过第二道墙
        (Position(2, 3), "path", "向右移动"),
        (Position(3, 3), "path", "继续向右"),
        (Position(4, 3), "path", "继续向右"),
        (Position(5, 3), "wall", "遇到第二道墙！"),
        (Position(4, 4), "path", "向上绕过墙壁"),
        (Position(4, 5), "path", "继续向上"),
        (Position(4, 6), "path", "继续向上"),
        (Position(4, 7), "path", "继续向上"),
        
        # 第三阶段：向右移动
        (Position(5, 7), "path", "向右移动"),
        (Position(6, 7), "path", "继续向右"),
        (Position(7, 7), "path", "继续向右"),
        (Position(8, 7), "path", "绕过第三道墙"),
        
        # 第四阶段：向下移动
        (Position(8, 8), "path", "向下移动"),
        (Position(8, 9), "path", "继续向下"),
        (Position(8, 10), "path", "继续向下"),
        (Position(9, 10), "wall", "遇到终点附近的墙！"),
        
        # 第五阶段：最后冲刺
        (Position(8, 11), "path", "向下绕过墙壁"),
        (Position(9, 11), "path", "向右移动"),
        (Position(10, 11), "path", "继续向右"),
        (Position(10, 10), "path", "🎉 到达终点！"),
    ]
    
    for step, (pos, cell_type, description) in enumerate(exploration_steps, 1):
        # 更新迷宫状态
        maze_state.set_cell(pos, CellState(cell_type))
        
        if cell_type == "path":
            path.append(pos)
            maze_state.path_history.append(pos)
        
        # 打印探索步骤
        print(f"[步骤 {step:2d}] 移动到 ({pos.x:2d}, {pos.y:2d}) - {cell_type:5s}")
        print(f"          └─ {description}")
        
        if cell_type == "wall":
            print(f"          └─ ⚠️  墙壁！需要重新规划路径")
        
        # 定期打印当前迷宫状态
        if step % 8 == 0 or cell_type == "wall":
            maze_state.current_pos = pos
            print(f"\n   当前迷宫状态 (步骤 {step}):")
            print("   " + visualizer.render_simple().replace("\n", "\n   "))
            print()
        
        await asyncio.sleep(0.3)
    
    # 打印最终路径
    print("\n" + "=" * 80)
    print("  🎉 探索完成!")
    print("=" * 80)
    
    print(f"\n✅ 完整路径:")
    print(f"   总步数：{len(path)}")
    print(f"   起点：{path[0]}")
    print(f"   终点：{path[-1]}")
    
    # 格式化打印路径
    print(f"\n   路径坐标:")
    for i, pos in enumerate(path):
        marker = "🚩" if i == 0 else ("🎯" if i == len(path) - 1 else "  ")
        print(f"      {marker} {i+1:2d}. ({pos.x:2d}, {pos.y:2d})")
    
    # 打印路径可视化
    print(f"\n📍 路径可视化:")
    path_coords = [f"({p.x},{p.y})" for p in path]
    
    # 分多行打印
    line = "   "
    for i, coord in enumerate(path_coords):
        if len(line) + len(coord) > 75:
            print(line)
            line = "   "
        line += coord
        if i < len(path_coords) - 1:
            line += " → "
    print(line)
    
    # 打印最终迷宫
    maze_state.current_pos = path[-1]
    print(f"\n📊 最终迷宫状态:")
    print(visualizer.render_simple())
    
    # 统计信息
    walls_hit = sum(1 for _, t, _ in exploration_steps if t == "wall")
    print(f"\n📈 探索统计:")
    print(f"   总探索步数：{len(exploration_steps)}")
    print(f"   有效路径：{len(path)} 个单元格")
    print(f"   遇到墙壁：{walls_hit} 次")
    print(f"   路径效率：{len(path) / len(exploration_steps) * 100:.1f}%")
    
    # 消息统计
    stats = mailbox_system.get_stats()
    print(f"\n📮 消息统计:")
    print(f"   注册 Agent: {stats['registered_agents']}")
    print(f"   总消息数：{stats['total_messages']}")
    
    print("\n" + "=" * 80)
    print("  演示完成！✅")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(complex_maze_demo())
