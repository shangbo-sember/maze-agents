"""
迷宫可视化工具
"""

import asyncio
import os
from typing import Dict, List, Optional
from datetime import datetime

from agents.types import Position, CellState, MazeState


class MazeVisualizer:
    """迷宫可视化工具"""
    
    SYMBOLS = {
        CellState.UNKNOWN: " ?",
        CellState.PATH: " .",
        CellState.WALL: " #",
        CellState.DEAD_END: " X",
        CellState.VISITED: " *",
        CellState.SOLUTION: " +",
    }
    
    SPECIAL_SYMBOLS = {
        "start": " S",
        "end": " E",
        "current": " @",
    }
    
    def __init__(self, maze_state: MazeState):
        self.maze_state = maze_state
        self.last_render = None
    
    def render(self) -> str:
        """渲染迷宫"""
        lines = []
        
        # 找到边界
        if not self.maze_state.grid:
            return "Empty maze"
        
        all_positions = list(self.maze_state.grid.keys())
        if self.maze_state.start:
            all_positions.append(self.maze_state.start)
        if self.maze_state.end:
            all_positions.append(self.maze_state.end)
        
        min_x = min(p.x for p in all_positions)
        max_x = max(p.x for p in all_positions)
        min_y = min(p.y for p in all_positions)
        max_y = max(p.y for p in all_positions)
        
        # 添加边距
        min_x -= 1
        max_x += 1
        min_y -= 1
        max_y += 1
        
        # 渲染标题
        lines.append("=" * 60)
        lines.append(f"  迷宫状态 - {datetime.now().strftime('%H:%M:%S')}")
        lines.append("=" * 60)
        
        # 渲染迷宫
        for y in range(min_y, max_y + 1):
            line = ""
            for x in range(min_x, max_x + 1):
                pos = Position(x, y)
                
                # 检查特殊位置
                if self.maze_state.start and pos == self.maze_state.start:
                    line += self.SPECIAL_SYMBOLS["start"]
                elif self.maze_state.end and pos == self.maze_state.end:
                    line += self.SPECIAL_SYMBOLS["end"]
                elif self.maze_state.current_pos and pos == self.maze_state.current_pos:
                    line += self.SPECIAL_SYMBOLS["current"]
                else:
                    state = self.maze_state.get_cell(pos)
                    line += self.SYMBOLS[state]
            
            lines.append(line)
        
        # 渲染统计信息
        lines.append("")
        lines.append("-" * 60)
        lines.append(f"  当前位置：{self.maze_state.current_pos}")
        lines.append(f"  路径长度：{len(self.maze_state.path_history)}")
        lines.append(f"  已访问：{len(self.maze_state.visited) if hasattr(self.maze_state, 'visited') else 'N/A'}")
        
        dead_ends = sum(1 for s in self.maze_state.grid.values() if s == CellState.DEAD_END)
        lines.append(f"  已知死路：{dead_ends}")
        
        if self.maze_state.solution:
            lines.append(f"  解路径长度：{len(self.maze_state.solution)}")
        
        if self.maze_state.is_solved:
            lines.append("  状态：✅ 已解决")
        elif self.maze_state.is_unsolvable:
            lines.append("  状态：❌ 无解")
        else:
            lines.append("  状态：🔄 探索中...")
        
        lines.append("=" * 60)
        
        self.last_render = "\n".join(lines)
        return self.last_render
    
    def render_simple(self) -> str:
        """简化渲染（用于日志）"""
        if not self.maze_state.grid:
            return "Empty maze"
        
        lines = []
        
        all_positions = list(self.maze_state.grid.keys())
        if self.maze_state.start:
            all_positions.append(self.maze_state.start)
        if self.maze_state.end:
            all_positions.append(self.maze_state.end)
        
        min_x = min(p.x for p in all_positions)
        max_x = max(p.x for p in all_positions)
        min_y = min(p.y for p in all_positions)
        max_y = max(p.y for p in all_positions)
        
        for y in range(min_y, max_y + 1):
            line = ""
            for x in range(min_x, max_x + 1):
                pos = Position(x, y)
                
                if self.maze_state.start and pos == self.maze_state.start:
                    line += "S"
                elif self.maze_state.end and pos == self.maze_state.end:
                    line += "E"
                elif self.maze_state.current_pos and pos == self.maze_state.current_pos:
                    line += "@"
                else:
                    state = self.maze_state.get_cell(pos)
                    line += self.SYMBOLS[state].strip()
            
            lines.append(line)
        
        return "\n".join(lines)
    
    async def live_render(self, refresh_interval: float = 0.3):
        """实时渲染"""
        while True:
            self.clear_screen()
            print(self.render())
            await asyncio.sleep(refresh_interval)
    
    def clear_screen(self):
        """清屏"""
        os.system("clear" if os.name == "posix" else "cls")
    
    def save_render(self, filename: str = None):
        """保存渲染结果到文件"""
        if filename is None:
            filename = f"maze_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.render())
        
        print(f"迷宫已保存到：{filename}")


class LiveRenderer:
    """实时渲染器"""
    
    def __init__(self, maze_state: MazeState):
        self.maze_state = maze_state
        self.visualizer = MazeVisualizer(maze_state)
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self, refresh_interval: float = 0.3):
        """启动实时渲染"""
        self.running = True
        self.task = asyncio.create_task(
            self.visualizer.live_render(refresh_interval)
        )
    
    async def stop(self):
        """停止实时渲染"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
    
    def update(self, maze_state: MazeState):
        """更新迷宫状态"""
        self.maze_state = maze_state
        self.visualizer.maze_state = maze_state
