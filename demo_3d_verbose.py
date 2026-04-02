#!/usr/bin/env python3
"""
3D 迷宫详细演示 - 带完整思考日志
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from agents.types_3d import Position3D, CellState3D, MazeState3D, Direction3D
from agents.explorer_3d import ExplorerAgent3D
from utils.mailbox import mailbox_system, receive_message
from utils.visualizer import MazeVisualizer


class MemoryAgent3D:
    """3D Memory Agent"""
    
    def __init__(self, agent_id: str = "memory_3d"):
        self.agent_id = agent_id
        self.mailbox: asyncio.Queue = asyncio.Queue()
        self.running = True
        self.grid: Dict[Position3D, CellState3D] = {}
        self.visited: set = set()
        self.path_history: List[Position3D] = []
        self.start: Position3D = None
        self.end: Position3D = None
        self.current_pos: Position3D = None
    
    async def initialize(self, maze_config: dict):
        """初始化 3D 迷宫"""
        dims = maze_config["dimensions"]
        self.start = Position3D(*maze_config["start"])
        self.end = Position3D(*maze_config["end"])
        self.current_pos = self.start
        self.path_history = [self.start]
        
        # 加载 3D 网格
        grid_config = maze_config.get("grid", {})
        for z_key, layer in grid_config.items():
            z = int(z_key.split("_")[1])
            for pos_str, state in layer.items():
                import ast
                x, y = ast.literal_eval(pos_str)
                pos = Position3D(x, y, z)
                self.grid[pos] = CellState3D(state)
        
        print(f"\n[Memory] 3D 迷宫初始化:")
        print(f"  尺寸：{dims['width']}x{dims['depth']}x{dims['height']}")
        print(f"  起点：{self.start}")
        print(f"  终点：{self.end}")
        print(f"  单元格总数：{dims['width'] * dims['depth'] * dims['height']}")
        print(f"  墙壁数量：{len(self.grid)}")
    
    async def get_cell(self, pos: Position3D) -> CellState3D:
        """获取单元格状态"""
        return self.grid.get(pos, CellState3D.UNKNOWN)
    
    async def is_end(self, pos: Position3D) -> bool:
        """检查是否是终点"""
        return self.end is not None and pos == self.end
    
    async def get_path_history(self) -> List[Tuple[int, int, int]]:
        """获取路径历史"""
        return [(p.x, p.y, p.z) for p in self.path_history]
    
    async def run(self):
        """运行循环"""
        from utils.mailbox import receive_message
        
        print(f"[{self.agent_id}] 🧠 Memory 3D 启动")
        
        while self.running:
            try:
                msg = await receive_message(self.agent_id, timeout=0.5)
                if msg:
                    # 处理状态更新
                    if msg.type.value == "state_update":
                        content = msg.content
                        for pos_str, state in content.get("updated_cells", {}).items():
                            import ast
                            pos = Position3D(*ast.literal_eval(pos_str))
                            self.grid[pos] = CellState3D(state)
            except asyncio.CancelledError:
                break
            await asyncio.sleep(0.1)
        
        print(f"[{self.agent_id}] 🛑 Memory 3D 停止")


class Visualizer3D:
    """3D 迷宫可视化"""
    
    SYMBOLS = {
        CellState3D.UNKNOWN: " ?",
        CellState3D.PATH: " .",
        CellState3D.WALL: " #",
        CellState3D.DEAD_END: " X",
        CellState3D.VISITED: " *",
        CellState3D.SOLUTION: " +",
    }
    
    def __init__(self, maze_state: MazeState3D):
        self.maze_state = maze_state
    
    def render_layer(self, z: int) -> str:
        """渲染单个层面"""
        lines = []
        lines.append(f"\n  ═══════════════════════════ 层面 Z={z} ═══════════════════════════")
        
        # 找到边界
        all_positions = [p for p in self.maze_state.grid.keys() if p.z == z]
        if self.maze_state.start and self.maze_state.start.z == z:
            all_positions.append(self.maze_state.start)
        if self.maze_state.end and self.maze_state.end.z == z:
            all_positions.append(self.maze_state.end)
        
        if not all_positions:
            return f"\n  [层面 Z={z} 无数据]"
        
        min_x = min(p.x for p in all_positions)
        max_x = max(p.x for p in all_positions)
        min_y = min(p.y for p in all_positions)
        max_y = max(p.y for p in all_positions)
        
        for y in range(min_y, max_y + 1):
            line = f"  Y={y:2d} │"
            for x in range(min_x, max_x + 1):
                pos = Position3D(x, y, z)
                
                if self.maze_state.start and pos == self.maze_state.start:
                    line += " S"
                elif self.maze_state.end and pos == self.maze_state.end:
                    line += " E"
                elif self.maze_state.current_pos and pos == self.maze_state.current_pos:
                    line += " @"
                else:
                    state = self.maze_state.get_cell(pos)
                    line += self.SYMBOLS[state]
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def render_all_layers(self) -> str:
        """渲染所有层面"""
        lines = []
        lines.append("\n" + "═" * 80)
        lines.append("  🧊 3D 迷宫状态")
        lines.append("═" * 80)
        
        # 确定 Z 范围
        min_z = 0
        max_z = 4
        
        for z in range(min_z, max_z + 1):
            lines.append(self.render_layer(z))
        
        lines.append("\n" + "─" * 80)
        lines.append(f"  当前位置：{self.maze_state.current_pos}")
        lines.append(f"  路径长度：{len(self.maze_state.path_history)}")
        
        if self.maze_state.is_solved:
            lines.append("  状态：✅ 已解决")
        else:
            lines.append("  状态：🔄 探索中...")
        
        lines.append("═" * 80)
        
        return "\n".join(lines)


async def demo_3d_maze():
    """3D 迷宫详细演示"""
    
    print("\n" + "=" * 80)
    print("  🧊 3D 迷宫探索 - 详细思考日志演示")
    print("=" * 80)
    
    # 加载 3D 迷宫配置
    config_file = Path(__file__).parent / "mazes" / "maze_3d_config.json"
    with open(config_file, "r") as f:
        maze_config = json.load(f)
    
    print(f"\n📊 加载迷宫：{maze_config['name']}")
    print(f"   描述：{maze_config['description']}")
    
    # 初始化 Memory
    memory = MemoryAgent3D("memory_3d")
    await memory.initialize(maze_config)
    
    # 创建 MazeState3D
    maze_state = MazeState3D(
        grid={},
        start=memory.start,
        end=memory.end,
        current_pos=memory.start,
        path_history=[memory.start],
    )
    
    # 注册 Agent
    mailbox_system.register_agent("explorer_3d_0")
    
    # 创建 Explorer
    step_counter = [0]
    explorer = ExplorerAgent3D("explorer_3d_0", maze_accessor=memory, step_counter=step_counter)
    
    # 创建可视化
    visualizer = Visualizer3D(maze_state)
    
    # 打印初始状态
    print(visualizer.render_all_layers())
    
    # 模拟探索过程
    print("\n🚀 开始 3D 探索...\n")
    
    # 预定义的 3D 探索路径
    exploration_path = [
        # 第 0 层探索
        (Position3D(1, 0, 0), "right", "path"),
        (Position3D(2, 0, 0), "right", "wall"),
        (Position3D(1, 1, 0), "back", "path"),
        (Position3D(1, 2, 0), "back", "wall"),
        (Position3D(1, 1, 0), "front", "path"),
        (Position3D(0, 1, 0), "left", "path"),
        (Position3D(0, 0, 0), "left", "path"),
        
        # 上楼到第 1 层
        (Position3D(3, 3, 0), "stairs", "path"),
        (Position3D(3, 3, 1), "up", "path"),
        
        # 第 1 层探索
        (Position3D(4, 3, 1), "right", "wall"),
        (Position3D(3, 4, 1), "back", "path"),
        (Position3D(3, 5, 1), "back", "wall"),
        (Position3D(4, 4, 1), "right", "path"),
        (Position3D(5, 4, 1), "right", "path"),
        (Position3D(6, 4, 1), "right", "path"),
        (Position3D(6, 5, 1), "back", "path"),
        (Position3D(6, 6, 1), "back", "path"),
        
        # 上楼到第 2 层
        (Position3D(6, 6, 2), "up", "path"),
        
        # 第 2 层探索
        (Position3D(5, 6, 2), "left", "wall"),
        (Position3D(6, 5, 2), "front", "wall"),
        (Position3D(6, 7, 2), "back", "path"),
        (Position3D(5, 7, 2), "left", "path"),
        (Position3D(4, 7, 2), "left", "path"),
        (Position3D(3, 7, 2), "left", "path"),
        (Position3D(2, 7, 2), "left", "path"),
        (Position3D(1, 7, 2), "left", "path"),
        (Position3D(1, 6, 2), "front", "wall"),
        (Position3D(1, 7, 1), "down", "path"),
        
        # 上楼到第 3 层
        (Position3D(1, 1, 2), "stairs", "path"),
        (Position3D(1, 1, 3), "up", "path"),
        
        # 第 3 层探索
        (Position3D(2, 1, 3), "right", "path"),
        (Position3D(3, 1, 3), "right", "path"),
        (Position3D(3, 2, 3), "back", "wall"),
        (Position3D(3, 0, 3), "front", "wall"),
        (Position3D(4, 1, 3), "right", "path"),
        (Position3D(5, 1, 3), "right", "path"),
        (Position3D(5, 2, 3), "back", "wall"),
        (Position3D(5, 0, 3), "front", "wall"),
        (Position3D(6, 1, 3), "right", "path"),
        (Position3D(7, 1, 3), "right", "path"),
        (Position3D(7, 2, 3), "back", "path"),
        (Position3D(7, 3, 3), "back", "path"),
        (Position3D(7, 4, 3), "back", "wall"),
        (Position3D(7, 3, 2), "down", "path"),
        
        # 最终上楼到第 4 层
        (Position3D(5, 5, 3), "stairs", "path"),
        (Position3D(5, 5, 4), "up", "path"),
        
        # 第 4 层冲刺到终点
        (Position3D(6, 5, 4), "right", "path"),
        (Position3D(7, 5, 4), "right", "path"),
        (Position3D(7, 6, 4), "back", "path"),
        (Position3D(7, 7, 4), "back", "path"),  # 终点！
    ]
    
    # 模拟探索步骤
    for step, (pos, direction, cell_type) in enumerate(exploration_path, 1):
        print(f"\n{'='*80}")
        print(f"【步骤 {step:3d}】Explorer 3D 思考过程")
        print(f"{'='*80}")
        
        # 更新状态
        maze_state.set_cell(pos, CellState3D(cell_type))
        maze_state.path_history.append(pos)
        maze_state.current_pos = pos
        
        # 模拟思考
        print(f"📍 当前位置：{pos}")
        print(f"🧭 移动方向：{direction}")
        print(f"🔍 检测结果：{cell_type}")
        
        if cell_type == "wall":
            print(f"⚠️  思考：遇到墙壁！需要改变方向")
            print(f"   考虑选项:")
            print(f"     - 向左转")
            print(f"     - 向右转")
            print(f"     - 向上/下楼")
            print(f"   决策：尝试其他方向")
        elif cell_type == "path":
            if direction in ["up", "down", "stairs"]:
                print(f"🏢 思考：发现楼梯！可以改变层面")
                print(f"   决策：使用楼梯移动到 Z={pos.z} 层")
            else:
                print(f"✅ 思考：新路径，继续探索")
                print(f"   决策：继续前进")
        elif cell_type == "dead_end":
            print(f"❌ 思考：死路！需要回溯")
            print(f"   决策：返回上一个位置")
        
        # 定期显示迷宫状态
        if step % 10 == 0 or step == len(exploration_path):
            print(visualizer.render_all_layers())
        
        await asyncio.sleep(0.5)  # 模拟思考时间
    
    # 打印最终结果
    print("\n" + "=" * 80)
    print("  🎉 3D 迷宫探索完成!")
    print("=" * 80)
    
    print(f"\n✅ 完整路径:")
    print(f"   总步数：{len(exploration_path)}")
    print(f"   起点：{exploration_path[0][0]}")
    print(f"   终点：{exploration_path[-1][0]}")
    
    # 打印路径坐标
    print(f"\n📍 路径坐标 (X,Y,Z):")
    for i, (pos, _, _) in enumerate(exploration_path):
        marker = "🚩" if i == 0 else ("🎯" if i == len(exploration_path) - 1 else "  ")
        print(f"   {marker} {i+1:3d}. ({pos.x:2d}, {pos.y:2d}, {pos.z:2d})")
    
    # 打印思考统计
    print(f"\n🧠 思考统计:")
    print(f"   总思考步骤：{step_counter[0]}")
    print(f"   Explorer 思考记录：{len(explorer.thoughts)} 条")
    
    # 打印部分思考日志示例
    print(f"\n💭 思考日志示例（前 5 条）:")
    for i, thought in enumerate(explorer.thoughts[:5], 1):
        print(f"\n   【思考 {i}】")
        print(f"   位置：{thought.current_pos}")
        print(f"   方向：{thought.direction}")
        print(f"   状态：{thought.cell_state.value}")
        print(f"   思考：{thought.thought}")
        print(f"   决策：{thought.decision}")
        if thought.alternatives_considered:
            print(f"   考虑选项：{thought.alternatives_considered}")
        print(f"   置信度：{thought.confidence:.0%}")
    
    # 最终迷宫状态
    print(visualizer.render_all_layers())
    
    print("\n" + "=" * 80)
    print("  演示完成！✅")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(demo_3d_maze())
