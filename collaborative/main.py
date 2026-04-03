#!/usr/bin/env python3
"""
多 Agent 协作迷宫系统 - 主程序

4 个 Agent，每个独立处理一个迷宫，通过 Hub 通信协作
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from .types import MazeConfig, Position, CollaborationHub, StateMessage, MessageType
from .agent import MazeAgent


class CollaborativeSystem:
    """协作系统"""
    
    def __init__(self, num_agents: int = 4, verbose: bool = False):
        self.num_agents = num_agents
        self.verbose = verbose
        self.hub = CollaborationHub()
        self.agents = []
        self.start_time = None
        self.end_time = None
    
    def create_agents(self):
        """创建 Agent"""
        # 4 的倍数矩阵迷宫
        maze_configs = [
            MazeConfig(maze_id="maze_1", width=4, height=4, agent_id="agent_1"),
            MazeConfig(maze_id="maze_2", width=8, height=8, agent_id="agent_2"),
            MazeConfig(maze_id="maze_3", width=12, height=12, agent_id="agent_3"),
            MazeConfig(maze_id="maze_4", width=16, height=16, agent_id="agent_4"),
        ][:self.num_agents]
        
        print(f"\n{'='*80}")
        print(f"  🤝 多 Agent 协作迷宫系统")
        print(f"{'='*80}")
        print(f"\n📊 配置:")
        print(f"   Agent 数量：{self.num_agents}")
        print(f"   通信方式：Hub 中转（不共享上下文）")
        print(f"\n🗺️  迷宫配置:")
        
        for config in maze_configs:
            agent = MazeAgent(config.agent_id, config, self.hub)
            self.agents.append(agent)
            self.hub.registered_agents[config.agent_id] = agent.state
            
            print(f"   {config.agent_id}: {config.width}x{config.height}, "
                  f"关卡数：{config.width * config.height * config.gate_density:.0f}")
        
        print(f"\n📡 Hub 已启动")
        print(f"   注册 Agent: {len(self.hub.registered_agents)}")
    
    async def run(self, timeout: float = 120.0):
        """运行系统"""
        self.start_time = datetime.now()
        
        print(f"\n🚀 开始协作求解...")
        print(f"   超时时间：{timeout}秒\n")
        
        # 启动所有 Agent
        agent_tasks = [asyncio.create_task(agent.run()) for agent in self.agents]
        
        # Hub 监控任务
        hub_task = asyncio.create_task(self._hub_monitor())
        
        # 等待完成或超时
        try:
            await asyncio.wait_for(
                asyncio.gather(*agent_tasks, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            print(f"\n⏱️  超时 ({timeout}秒)")
            
            # 停止所有 Agent
            for agent in self.agents:
                agent.running = False
        
        hub_task.cancel()
        try:
            await hub_task
        except asyncio.CancelledError:
            pass
        
        self.end_time = datetime.now()
        
        # 打印结果
        await self._print_results()
    
    async def _hub_monitor(self):
        """Hub 监控"""
        while True:
            # 检查是否所有 Agent 都完成了
            solved_count = sum(
                1 for agent in self.agents
                if agent.state.current_pos == agent.config.end_pos
            )
            
            if solved_count == len(self.agents):
                # 所有 Agent 完成
                all_solved_msg = StateMessage(
                    message_type=MessageType.ALL_MAZES_SOLVED,
                    sender_id="hub",
                    coordination_data={
                        "solved_count": solved_count,
                        "total_agents": len(self.agents),
                    }
                )
                self.hub.broadcast(all_solved_msg)
                break
            
            # 打印 Hub 状态
            if self.verbose:
                msg_count = len(self.hub.message_queue)
                if msg_count > 0:
                    print(f"\n📡 [Hub] 消息队列：{msg_count} 条")
                    for msg in self.hub.message_queue[-3:]:
                        print(f"   {msg.message_type.value}: {msg.sender_id} → {msg.receiver_id}")
            
            await asyncio.sleep(1.0)
    
    async def _print_results(self):
        """打印结果"""
        elapsed = (self.end_time - self.start_time).total_seconds()
        
        print(f"\n{'='*80}")
        print(f"  📊 协作结果")
        print(f"{'='*80}")
        
        print(f"\n⏱️  总耗时：{elapsed:.2f}秒")
        
        # 每个 Agent 的统计
        print(f"\n🤖 Agent 统计:")
        
        all_solved = True
        for agent in self.agents:
            stats = agent.get_stats()
            solved = stats["steps"] < 500  # 没超时
            
            status = "✅" if solved else "⏱️"
            print(f"\n   {status} {stats['agent_id']}:")
            print(f"      迷宫：{stats['maze_size']}")
            print(f"      步数：{stats['steps']}")
            print(f"      解决关卡：{stats['gates_solved']}")
            print(f"      路径长度：{stats['path_length']}")
            print(f"      请求帮助：{stats['help_requests']} 次")
            print(f"      共享 skill: {stats['shared_skills']} 个")
            
            if stats['skills_used']:
                print(f"      Skills 使用:")
                for skill, count in stats['skills_used'].items():
                    if count > 0:
                        print(f"         {skill.value}: {count} 次")
            
            if not solved:
                all_solved = False
        
        # Hub 统计
        print(f"\n📡 Hub 统计:")
        print(f"   注册 Agent: {len(self.hub.registered_agents)}")
        print(f"   总消息数：{len(self.hub.message_queue)}")
        print(f"   共享 knowledge: {len(self.hub.shared_knowledge)}")
        
        # 协作效果
        total_help_requests = sum(a.state.help_requests for a in self.agents)
        total_shared_skills = sum(len(a.state.shared_skills) for a in self.agents)
        
        print(f"\n🤝 协作效果:")
        print(f"   总帮助请求：{total_help_requests} 次")
        print(f"   Skill 共享：{total_shared_skills} 次")
        print(f"   协作成功率：{total_shared_skills / max(1, total_help_requests) * 100:.1f}%")
        
        # 总结
        print(f"\n{'='*80}")
        if all_solved:
            print(f"  ✅ 所有 Agent 成功走出迷宫!")
        else:
            print(f"  ⏱️  部分 Agent 未完成")
        print(f"{'='*80}\n")
        
        # 打印思考日志示例
        if self.verbose:
            print(f"\n🧠 思考日志示例 (Agent 1):")
            agent1 = self.agents[0]
            for log in agent1.thought_log[:5]:
                print(f"\n   【步骤 {log['step']:3d}】")
                print(f"   💭 思考：{log['thought']}")
                print(f"   ✅ 决策：{log['decision']}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="多 Agent 协作迷宫系统")
    parser.add_argument("--agents", type=int, default=4, help="Agent 数量")
    parser.add_argument("--timeout", type=float, default=120.0, help="超时时间（秒）")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 创建系统
    system = CollaborativeSystem(num_agents=args.agents, verbose=args.verbose)
    system.create_agents()
    
    # 运行
    await system.run(timeout=args.timeout)


if __name__ == "__main__":
    asyncio.run(main())
