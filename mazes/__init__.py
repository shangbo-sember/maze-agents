"""
迷宫配置模块
"""

import json
from pathlib import Path
from typing import Dict, Any


def load_maze(filename: str) -> Dict[str, Any]:
    """加载迷宫配置"""
    filepath = Path(__file__).parent / filename
    
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_sample_maze() -> Dict[str, Any]:
    """获取示例迷宫"""
    return load_maze("sample_maze.json")


def create_empty_maze(size: int = 10) -> Dict[str, Any]:
    """创建空迷宫"""
    return {
        "name": f"Empty Maze {size}x{size}",
        "start": [0, 0],
        "end": [size - 1, size - 1],
        "grid": {},
        "difficulty": "easy",
    }


def create_random_maze(size: int = 10, wall_density: float = 0.2) -> Dict[str, Any]:
    """
    创建随机迷宫
    
    Args:
        size: 迷宫大小
        wall_density: 墙壁密度 (0-1)
    """
    import random
    
    grid = {}
    
    for x in range(size):
        for y in range(size):
            # 起点和终点不能是墙
            if (x == 0 and y == 0) or (x == size - 1 and y == size - 1):
                continue
            
            # 随机生成墙壁
            if random.random() < wall_density:
                grid[f"({x}, {y})"] = "wall"
    
    return {
        "name": f"Random Maze {size}x{size}",
        "start": [0, 0],
        "end": [size - 1, size - 1],
        "grid": grid,
        "difficulty": "medium" if wall_density > 0.2 else "easy",
        "wall_density": wall_density,
    }
