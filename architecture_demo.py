#!/usr/bin/env python3
"""
架构演示 - 展示多 Agent 消息传递流程
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from agents.types import Position, CellState, MazeState
from agents.messages import Message, MessageType, ExploreRequest, ExploreResult
from utils.mailbox import mailbox_system, receive_message


async def architecture_demo():
    """展示架构工作原理"""
    
    print("\n" + "=" * 70)
    print("  🏗️  Maze Agents 架构演示 - 消息传递流程")
    print("=" * 70)
    
    # 1. 注册 Agent
    print("\n【步骤 1】注册 Agent 到邮箱系统")
    print("-" * 70)
    
    mailbox_system.register_agent("coordinator")
    mailbox_system.register_agent("memory")
    mailbox_system.register_agent("explorer_0")
    mailbox_system.register_agent("explorer_1")
    
    print(f"已注册 Agent: {list(mailbox_system.registered_agents.keys())}")
    
    # 2. Coordinator 发送探索请求
    print("\n【步骤 2】Coordinator → Explorer 发送探索请求")
    print("-" * 70)
    
    from_pos = Position(0, 0)
    
    explore_request = Message(
        type=MessageType.EXPLORE_REQUEST,
        sender_id="coordinator",
        receiver_id="explorer_0",
        timestamp=datetime.now(),
        content=ExploreRequest(
            from_pos=(from_pos.x, from_pos.y),
            direction="right",
            max_depth=10,
        ).to_dict()
    )
    
    await mailbox_system.send(explore_request)
    print(f"发送探索请求:")
    print(f"  发送者：{explore_request.sender_id}")
    print(f"  接收者：{explore_request.receiver_id}")
    print(f"  类型：{explore_request.type.value}")
    print(f"  内容：从 {from_pos} 向右探索，最大深度=10")
    
    # 3. Explorer 接收并处理
    print("\n【步骤 3】Explorer 接收并处理请求")
    print("-" * 70)
    
    received = await mailbox_system.receive("explorer_0", timeout=1.0)
    if received:
        print(f"Explorer_0 收到消息:")
        print(f"  消息 ID: {received.message_id}")
        print(f"  类型：{received.type.value}")
        print(f"  已读：{received.read}")
        
        # 模拟探索过程
        print(f"\nExplorer_0 开始探索...")
        await asyncio.sleep(0.5)
        
        # 4. Explorer 返回结果
        print("\n【步骤 4】Explorer → Coordinator 返回探索结果")
        print("-" * 70)
        
        explore_result = received.create_reply(MessageType.EXPLORE_RESULT, {
            "from_pos": (0, 0),
            "direction": "right",
            "cells_explored": [
                ((1, 0), "path"),
                ((2, 0), "path"),
                ((3, 0), "path"),
            ],
            "dead_ends": [],
            "paths_found": [(1, 0), (2, 0), (3, 0)],
            "explorer_status": "success"
        })
        
        await mailbox_system.send(explore_result)
        
        print(f"发送探索结果:")
        print(f"  发送者：{explore_result.sender_id}")
        print(f"  接收者：{explore_result.receiver_id}")
        print(f"  探索单元格：3 个")
        print(f"  找到路径：3 个")
        print(f"  死路：0 个")
    
    # 5. Coordinator 接收结果
    print("\n【步骤 5】Coordinator 接收结果并决策")
    print("-" * 70)
    
    result = await mailbox_system.receive("coordinator", timeout=1.0)
    if result:
        print(f"Coordinator 收到结果:")
        print(f"  关联 ID: {result.correlation_id}")
        print(f"  回复给：{result.reply_to}")
        print(f"\nCoordinator 决策：继续从 (3, 0) 向右探索")
    
    # 6. 并行探索演示
    print("\n【步骤 6】并行探索 - 派出多个 Explorer")
    print("-" * 70)
    
    # 同时派出 2 个 Explorer
    tasks = []
    for i, direction in enumerate(["up", "down"]):
        msg = Message(
            type=MessageType.EXPLORE_REQUEST,
            sender_id="coordinator",
            receiver_id=f"explorer_{i+1}",
            timestamp=datetime.now(),
            content={
                "from_pos": (0, 0),
                "direction": direction,
                "max_depth": 10
            }
        )
        await mailbox_system.send(msg)
        print(f"派出 Explorer_{i+1} 向 {direction} 探索")
    
    # 等待两个 Explorer 完成
    print("\n等待 Explorer 完成...")
    await asyncio.sleep(0.5)
    
    # 7. 状态更新
    print("\n【步骤 7】Coordinator → Memory 更新状态")
    print("-" * 70)
    
    state_update = Message(
        type=MessageType.STATE_UPDATE,
        sender_id="coordinator",
        receiver_id="memory",
        timestamp=datetime.now(),
        content={
            "updated_cells": {
                "(1, 0)": "path",
                "(2, 0)": "path",
                "(3, 0)": "path",
            },
            "new_current_pos": (3, 0),
            "path_added": [(1, 0), (2, 0), (3, 0)],
        }
    )
    
    await mailbox_system.send(state_update)
    
    print(f"更新状态到 Memory:")
    print(f"  更新单元格：3 个")
    print(f"  新位置：(3, 0)")
    print(f"  添加路径：3 个单元格")
    
    # 8. Memory 响应查询
    print("\n【步骤 8】Memory 响应状态查询")
    print("-" * 70)
    
    state_query = Message(
        type=MessageType.STATE_QUERY,
        sender_id="coordinator",
        receiver_id="memory",
        timestamp=datetime.now(),
        content={"query_type": "get_cell", "position": (3, 0)}
    )
    
    await mailbox_system.send(state_query)
    
    # Memory 处理（简化）
    print(f"Memory 收到查询：获取 (3, 0) 的状态")
    print(f"Memory 响应：CellState.PATH")
    
    # 9. 迷宫解决
    print("\n【步骤 9】找到终点，广播解决消息")
    print("-" * 70)
    
    solved_msg = Message(
        type=MessageType.MAZE_SOLVED,
        sender_id="coordinator",
        receiver_id="broadcast",
        timestamp=datetime.now(),
        content={
            "solution": [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)],
            "length": 5,
        }
    )
    
    await mailbox_system.broadcast(solved_msg)
    
    print(f"广播迷宫解决消息:")
    print(f"  路径长度：5")
    print(f"  路径：[(0,0), (1,0), (2,0), (3,0), (4,0)]")
    
    # 所有 Agent 收到广播
    for agent_id in ["explorer_0", "explorer_1", "memory"]:
        msg = await mailbox_system.receive(agent_id, timeout=0.5)
        if msg:
            print(f"  ✓ {agent_id} 收到解决消息")
    
    # 10. 统计信息
    print("\n【统计信息】")
    print("-" * 70)
    
    stats = mailbox_system.get_stats()
    print(f"  注册 Agent: {stats['registered_agents']}")
    print(f"  活跃 Agent: {stats['active_agents']}")
    print(f"  消息总数：{stats['total_messages']}")
    print(f"  待处理消息：{stats['pending_messages']}")
    
    # 可视化消息流
    print("\n" + "=" * 70)
    print("  消息流可视化")
    print("=" * 70)
    
    print("""
    ┌─────────────┐
    │Coordinator  │
    └──────┬──────┘
           │
     ┌─────┼─────┬──────────┐
     │     │     │          │
     ▼     ▼     ▼          ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│Explorer0│ │Explorer1│ │ Memory  │
└────┬────┘ └────┬────┘ └────┬────┘
     │           │           │
     └───────────┼───────────┘
                 │
                 ▼
          ┌─────────────┐
          │   Verifier  │ (可选)
          └─────────────┘
    
    消息类型:
    → EXPLORE_REQUEST (Coordinator → Explorer)
    ← EXPLORE_RESULT (Explorer → Coordinator)
    ↔ STATE_UPDATE/QUERY (Coordinator ↔ Memory)
    ↗ VERIFY_PATH (Coordinator → Verifier)
    ★ MAZE_SOLVED (广播)
    """)
    
    print("\n" + "=" * 70)
    print("  演示完成！✅")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(architecture_demo())
