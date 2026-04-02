# 🧩 Maze Agents - 多 Agent 迷宫求解系统

[![Tests](https://github.com/YOUR_USERNAME/maze-agents/actions/workflows/test.yml/badge.svg)](https://github.com/YOUR_USERNAME/maze-agents/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

基于 Claude Code 架构灵感设计的多 Agent 协作迷宫求解系统。

## 架构特点

- **Coordinator-Worker 模式**: 中心决策 + 并行探索
- **异步消息传递**: 基于邮箱系统的 Agent 间通信
- **动态 Agent 管理**: 根据需要动态创建/销毁 Explorer
- **实时可视化**: 终端实时渲染迷宫探索过程

## 项目结构

```
maze_agents/
├── agents/                 # Agent 实现
│   ├── types.py           # 类型定义
│   ├── messages.py        # 消息定义
│   ├── coordinator.py     # 决策中心
│   ├── explorer.py        # 路径探索
│   ├── memory.py          # 状态管理
│   └── verifier.py        # 死路验证
├── utils/                  # 工具模块
│   ├── mailbox.py         # 邮箱系统
│   └── visualizer.py      # 可视化工具
├── mazes/                  # 迷宫配置
│   └── sample_maze.json   # 示例迷宫
├── tests/                  # 测试
│   ├── test_mailbox.py
│   └── test_types.py
├── main.py                 # 主程序入口
├── config.py               # 配置
└── README.md               # 说明文档
```

## 快速开始

### 安装依赖

```bash
cd maze_agents
pip install -r requirements.txt
```

### 运行示例

```bash
# 使用示例迷宫
python main.py

# 使用随机迷宫
python main.py --random --size 15 --density 0.25

# 禁用实时渲染（适合日志记录）
python main.py --no-render

# 自定义 Explorer 数量
python main.py --explorers 20 --timeout 120
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--maze` | 迷宫配置文件 | sample_maze.json |
| `--random` | 使用随机迷宫 | False |
| `--size` | 随机迷宫大小 | 10 |
| `--density` | 墙壁密度 | 0.2 |
| `--explorers` | 最大 Explorer 数量 | 10 |
| `--timeout` | 超时时间（秒） | 60.0 |
| `--no-render` | 禁用实时渲染 | False |

## Agent 角色

### Coordinator (决策中心)
- 接收 Explorer 的探索结果
- 决策下一步探索方向
- 管理 Explorer 池
- 判断迷宫是否可解

### Explorer (路径探索)
- 接收 Coordinator 的探索指令
- 深度优先探索路径
- 报告探索结果
- 检测死路

### Memory (状态管理)
- 维护全局迷宫状态
- 处理状态查询
- 提供路径历史

### Verifier (死路验证)
- 验证疑似死路
- 确认路径有效性
- 检测循环路径

## 消息类型

| 类型 | 方向 | 说明 |
|------|------|------|
| `EXPLORE_REQUEST` | Coordinator → Explorer | 探索请求 |
| `EXPLORE_RESULT` | Explorer → Coordinator | 探索结果 |
| `DEAD_END_REPORT` | Explorer → Coordinator | 死路报告 |
| `PATH_FOUND` | Explorer → Coordinator | 找到路径 |
| `STATE_UPDATE` | Coordinator → Memory | 状态更新 |
| `STATE_QUERY` | Coordinator → Memory | 状态查询 |
| `VERIFY_PATH` | Coordinator → Verifier | 路径验证 |
| `MAZE_SOLVED` | System → All | 迷宫已解决 |
| `MAZE_UNSOLVABLE` | System → All | 迷宫无解 |

## 架构对比

| 特性 | Maze Agents | LangGraph |
|------|-------------|-----------|
| 流程控制 | 动态决策 | 预定义图 |
| 并行能力 | 天然支持 | 需显式定义 |
| 状态管理 | 分布式 | 集中式 |
| 人类介入 | 自然支持 | 需特殊处理 |
| 调试难度 | 较高 | 较低 |
| 适用场景 | 开放性问题 | 确定性流程 |

## 开发指南

### 添加新 Agent

1. 在 `agents/` 目录创建新 Agent 类
2. 实现 `handle_message()` 方法
3. 实现 `run()` 运行循环
4. 在 `main.py` 中注册

### 添加新消息类型

1. 在 `agents/messages.py` 添加 `MessageType` 枚举
2. 创建消息内容类（如 `ExploreRequest`）
3. 实现 `to_dict()` 和 `from_dict()` 方法

### 自定义迷宫

在 `mazes/` 目录创建 JSON 配置文件：

```json
{
  "name": "My Maze",
  "start": [0, 0],
  "end": [9, 9],
  "grid": {
    "(3, 0)": "wall",
    "(3, 1)": "wall"
  }
}
```

## 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_mailbox.py -v
```

## 许可证

MIT License

## 致谢

灵感来源于：
- [Claude Code](https://github.com/anthropics/claude-code) - 多 Agent 架构
- [OpenClaw](https://github.com/openclaw/openclaw) - Agent 编排
