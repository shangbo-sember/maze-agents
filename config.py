"""
Maze Agents Configuration
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """全局配置"""
    
    # Agent 配置
    MAX_EXPLORERS: int = 10           # 最大 Explorer 数量
    EXPLORER_MAX_DEPTH: int = 20      # Explorer 单次探索最大深度
    EXPLORER_TIMEOUT: float = 5.0     # Explorer 超时时间（秒）
    
    # 邮箱配置
    MAILBOX_TIMEOUT: float = 1.0      # 邮箱接收超时
    PERSIST_MESSAGES: bool = True     # 是否持久化消息
    
    # 迷宫配置
    DEFAULT_MAZE_SIZE: int = 10       # 默认迷宫大小
    START_POS: tuple = (0, 0)         # 默认起点
    END_POS: tuple = (9, 9)           # 默认终点
    
    # 可视化配置
    REFRESH_INTERVAL: float = 0.3     # 可视化刷新间隔（秒）
    ENABLE_LIVE_RENDER: bool = True   # 是否启用实时渲染
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = "maze_agents.log"


# 全局配置实例
config = Config()
