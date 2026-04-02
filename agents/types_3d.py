"""
3D 类型定义
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from datetime import datetime

from agents.types import AgentRole


@dataclass(frozen=True)
class Position3D:
    """3D 迷宫位置"""
    x: int
    y: int
    z: int
    
    def neighbors(self) -> List['Position3D']:
        """返回六个方向的邻居（3D）"""
        return [
            Position3D(self.x, self.y, self.z - 1),  # 上
            Position3D(self.x, self.y, self.z + 1),  # 下
            Position3D(self.x - 1, self.y, self.z),  # 左
            Position3D(self.x + 1, self.y, self.z),  # 右
            Position3D(self.x, self.y - 1, self.z),  # 前
            Position3D(self.x, self.y + 1, self.z),  # 后
        ]
    
    def direction_to(self, other: 'Position3D') -> str:
        """计算到另一个位置的方向"""
        if other.z > self.z:
            return "down"
        elif other.z < self.z:
            return "up"
        elif other.x > self.x:
            return "right"
        elif other.x < self.x:
            return "left"
        elif other.y > self.y:
            return "back"
        elif other.y < self.y:
            return "front"
        return "unknown"
    
    def distance_to(self, other: 'Position3D') -> int:
        """计算曼哈顿距离（3D）"""
        return abs(self.x - other.x) + abs(self.y - other.y) + abs(self.z - other.z)
    
    def __str__(self):
        return f"({self.x},{self.y},{self.z})"


class CellState3D(Enum):
    """3D 单元格状态"""
    UNKNOWN = "unknown"
    PATH = "path"
    WALL = "wall"
    DEAD_END = "dead_end"
    VISITED = "visited"
    SOLUTION = "solution"


class Direction3D(Enum):
    """3D 方向"""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    FRONT = "front"
    BACK = "back"


@dataclass
class MazeState3D:
    """3D 迷宫全局状态"""
    grid: Dict[Position3D, CellState3D]
    start: Position3D
    end: Position3D
    current_pos: Position3D
    path_history: List[Position3D] = field(default_factory=list)
    explorer_count: int = 0
    solution: Optional[List[Position3D]] = None
    is_solved: bool = False
    is_unsolvable: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    
    # 思考日志
    thinking_log: List[dict] = field(default_factory=list)
    
    def copy(self) -> 'MazeState3D':
        """创建状态副本"""
        return MazeState3D(
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
            thinking_log=self.thinking_log.copy(),
        )
    
    def get_cell(self, pos: Position3D) -> CellState3D:
        """获取单元格状态"""
        return self.grid.get(pos, CellState3D.UNKNOWN)
    
    def set_cell(self, pos: Position3D, state: CellState3D):
        """设置单元格状态"""
        self.grid[pos] = state
    
    def is_valid(self, pos: Position3D) -> bool:
        """检查位置是否有效"""
        state = self.get_cell(pos)
        return state != CellState3D.WALL
    
    def add_thinking_log(self, step: str, agent: str, thought: str, decision: str, data: dict = None):
        """添加思考日志"""
        self.thinking_log.append({
            "step": step,
            "agent": agent,
            "thought": thought,
            "decision": decision,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
        })
    
    def print_thinking_log(self, filter_agent: str = None):
        """打印思考日志"""
        print("\n" + "=" * 80)
        print("  🧠 思考过程日志")
        print("=" * 80)
        
        for i, log in enumerate(self.thinking_log, 1):
            if filter_agent and log["agent"] != filter_agent:
                continue
            
            print(f"\n【步骤 {log['step']:3d}】{log['agent']}")
            print(f"  💭 思考：{log['thought']}")
            print(f"  ✅ 决策：{log['decision']}")
            if log.get('data'):
                print(f"  📊 数据：{log['data']}")
        
        print("\n" + "=" * 80)


@dataclass
class ExplorerThought:
    """Explorer 思考记录"""
    step: int
    current_pos: Position3D
    direction: str
    cell_state: CellState3D
    thought: str
    decision: str
    alternatives_considered: List[str] = field(default_factory=list)
    confidence: float = 1.0
