"""
类型定义测试
"""

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.types import Position, CellState, MazeState


class TestPosition:
    """位置测试"""
    
    def test_position_creation(self):
        """测试位置创建"""
        pos = Position(3, 5)
        assert pos.x == 3
        assert pos.y == 5
    
    def test_position_neighbors(self):
        """测试邻居位置"""
        pos = Position(0, 0)
        neighbors = pos.neighbors()
        
        assert len(neighbors) == 4
        assert Position(0, -1) in neighbors  # 上
        assert Position(0, 1) in neighbors   # 下
        assert Position(-1, 0) in neighbors  # 左
        assert Position(1, 0) in neighbors   # 右
    
    def test_position_direction_to(self):
        """测试方向计算"""
        pos = Position(0, 0)
        
        assert pos.direction_to(Position(1, 0)) == "right"
        assert pos.direction_to(Position(-1, 0)) == "left"
        assert pos.direction_to(Position(0, 1)) == "down"
        assert pos.direction_to(Position(0, -1)) == "up"
    
    def test_position_distance_to(self):
        """测试距离计算"""
        pos1 = Position(0, 0)
        pos2 = Position(3, 4)
        
        assert pos1.distance_to(pos2) == 7  # 曼哈顿距离
    
    def test_position_hash(self):
        """测试哈希"""
        pos1 = Position(1, 2)
        pos2 = Position(1, 2)
        pos3 = Position(2, 1)
        
        assert hash(pos1) == hash(pos2)
        assert hash(pos1) != hash(pos3)


class TestCellState:
    """单元格状态测试"""
    
    def test_cell_state_values(self):
        """测试状态值"""
        assert CellState.UNKNOWN.value == "unknown"
        assert CellState.PATH.value == "path"
        assert CellState.WALL.value == "wall"
        assert CellState.DEAD_END.value == "dead_end"
        assert CellState.VISITED.value == "visited"
        assert CellState.SOLUTION.value == "solution"


class TestMazeState:
    """迷宫状态测试"""
    
    def test_maze_state_creation(self):
        """测试迷宫状态创建"""
        state = MazeState(
            grid={},
            start=Position(0, 0),
            end=Position(9, 9),
            current_pos=Position(0, 0),
            path_history=[Position(0, 0)],
        )
        
        assert state.start == Position(0, 0)
        assert state.end == Position(9, 9)
        assert state.is_solved == False
        assert state.is_unsolvable == False
    
    def test_maze_state_get_set_cell(self):
        """测试单元格读写"""
        state = MazeState(
            grid={},
            start=Position(0, 0),
            end=Position(9, 9),
            current_pos=Position(0, 0),
        )
        
        pos = Position(5, 5)
        
        # 默认未知
        assert state.get_cell(pos) == CellState.UNKNOWN
        
        # 设置状态
        state.set_cell(pos, CellState.PATH)
        assert state.get_cell(pos) == CellState.PATH
    
    def test_maze_state_is_valid(self):
        """测试有效性检查"""
        state = MazeState(
            grid={},
            start=Position(0, 0),
            end=Position(9, 9),
            current_pos=Position(0, 0),
        )
        
        # 设置墙壁
        state.set_cell(Position(5, 5), CellState.WALL)
        
        assert state.is_valid(Position(5, 5)) == False
        assert state.is_valid(Position(0, 0)) == True
    
    def test_maze_state_copy(self):
        """测试状态复制"""
        original = MazeState(
            grid={},
            start=Position(0, 0),
            end=Position(9, 9),
            current_pos=Position(0, 0),
            path_history=[Position(0, 0), Position(0, 1)],
        )
        
        original.set_cell(Position(5, 5), CellState.PATH)
        
        copied = original.copy()
        
        assert copied.start == original.start
        assert copied.end == original.end
        assert copied.path_history == original.path_history
        assert copied.get_cell(Position(5, 5)) == CellState.PATH
        
        # 修改副本不影响原件
        copied.set_cell(Position(5, 5), CellState.WALL)
        assert original.get_cell(Position(5, 5)) == CellState.PATH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
