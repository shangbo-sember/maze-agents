"""
类型定义
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime


class AgentRole(Enum):
    """Agent 角色定义"""
    COORDINATOR = "coordinator"      # 决策中心
    EXPLORER = "explorer"           # 路径探索
    MEMORY = "memory"               # 状态管理
    VERIFIER = "verifier"           # 死路验证


@dataclass(frozen=True)
class Position:
    """迷宫位置"""
    x: int
    y: int
    
    def neighbors(self) -> List['Position']:
        """返回四个方向的邻居"""
        return [
            Position(self.x, self.y - 1),  # 上
            Position(self.x, self.y + 1),  # 下
            Position(self.x - 1, self.y),  # 左
            Position(self.x + 1, self.y),  # 右
        ]
    
    def direction_to(self, other: 'Position') -> str:
        """计算到另一个位置的方向"""
        if other.x > self.x:
            return "right"
        elif other.x < self.x:
            return "left"
        elif other.y > self.y:
            return "down"
        elif other.y < self.y:
            return "up"
        return "unknown"
    
    def distance_to(self, other: 'Position') -> int:
        """计算曼哈顿距离"""
        return abs(self.x - other.x) + abs(self.y - other.y)


class CellState(Enum):
    """单元格状态"""
    UNKNOWN = "unknown"      # 未探索
    PATH = "path"           # 可行路径
    WALL = "wall"           # 墙壁
    DEAD_END = "dead_end"   # 死路
    VISITED = "visited"     # 已访问
    SOLUTION = "solution"   # 解路径


@dataclass
class MazeState:
    """迷宫全局状态"""
    grid: Dict[Position, CellState]
    start: Position
    end: Position
    current_pos: Position
    path_history: List[Position] = field(default_factory=list)
    explorer_count: int = 0
    solution: Optional[List[Position]] = None
    is_solved: bool = False
    is_unsolvable: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    
    def copy(self) -> 'MazeState':
        """创建状态副本"""
        return MazeState(
            grid=self.grid.copy(),
            start=self.start,
            end=self.end,
            current_pos=self.current_pos,
            path_history=self.path_history.copy(),
            explorer_count=self.explorer_count,
            solution=self.solution.copy() if self.solution else None,
            is_solved=self.is_solved,
            is_unsolvable=self.is_unsolvable,
            created_at=self.created_at,
        )
    
    def get_cell(self, pos: Position) -> CellState:
        """获取单元格状态"""
        return self.grid.get(pos, CellState.UNKNOWN)
    
    def set_cell(self, pos: Position, state: CellState):
        """设置单元格状态"""
        self.grid[pos] = state
    
    def is_valid(self, pos: Position) -> bool:
        """检查位置是否有效（不是墙壁）"""
        state = self.get_cell(pos)
        return state != CellState.WALL
    
    def is_explored(self, pos: Position) -> bool:
        """检查位置是否已探索"""
        state = self.get_cell(pos)
        return state not in (CellState.UNKNOWN, CellState.WALL)
