"""
邮箱系统 - Agent 间异步消息传递

实现：
1. 点对点消息
2. 广播消息
3. 消息持久化（可选）
4. 已读标记
"""

import asyncio
import json
from typing import Dict, Optional, List
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from agents.messages import Message


class MailboxSystem:
    """邮箱系统"""
    
    def __init__(self, persist: bool = False, persist_dir: str = None):
        self.mailboxes: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self.persist = persist
        self.persist_dir = Path(persist_dir) if persist_dir else None
        self.message_log: List[Message] = []
        self.registered_agents: Dict[str, bool] = {}  # agent_id -> is_alive
        
        if self.persist and self.persist_dir:
            self.persist_dir.mkdir(parents=True, exist_ok=True)
    
    def register_agent(self, agent_id: str):
        """注册 Agent"""
        _ = self.mailboxes[agent_id]  # 创建队列
        self.registered_agents[agent_id] = True
        print(f"[Mailbox] 注册 Agent: {agent_id}")
    
    def unregister_agent(self, agent_id: str):
        """注销 Agent"""
        if agent_id in self.mailboxes:
            del self.mailboxes[agent_id]
        self.registered_agents[agent_id] = False
        print(f"[Mailbox] 注销 Agent: {agent_id}")
    
    async def send(self, msg: Message):
        """发送消息到目标邮箱"""
        receiver_id = msg.receiver_id
        
        if receiver_id == "broadcast":
            await self.broadcast(msg)
        else:
            # 检查接收者是否存在
            if receiver_id not in self.mailboxes:
                print(f"[Mailbox] 警告：接收者 {receiver_id} 未注册，创建邮箱")
                self.register_agent(receiver_id)
            
            await self.mailboxes[receiver_id].put(msg)
            
            # 持久化
            if self.persist:
                self.message_log.append(msg)
                await self._persist_message(msg)
    
    async def broadcast(self, msg: Message):
        """广播消息到所有邮箱"""
        for agent_id in list(self.mailboxes.keys()):
            if self.registered_agents.get(agent_id, False):
                await self.mailboxes[agent_id].put(msg)
        
        print(f"[Mailbox] 广播消息：{msg.type.value}")
    
    async def receive(self, agent_id: str, timeout: float = None) -> Optional[Message]:
        """接收消息"""
        if agent_id not in self.mailboxes:
            return None
        
        try:
            if timeout:
                return await asyncio.wait_for(
                    self.mailboxes[agent_id].get(),
                    timeout=timeout
                )
            else:
                return await self.mailboxes[agent_id].get()
        except asyncio.TimeoutError:
            return None
    
    async def receive_all(self, agent_id: str) -> List[Message]:
        """接收所有可用消息"""
        messages = []
        if agent_id in self.mailboxes:
            while not self.mailboxes[agent_id].empty():
                messages.append(await self.mailboxes[agent_id].get())
        return messages
    
    async def _persist_message(self, msg: Message):
        """持久化消息到文件"""
        if not self.persist_dir:
            return
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = self.persist_dir / f"messages_{date_str}.jsonl"
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(msg.to_dict()) + "\n")
        except Exception as e:
            print(f"[Mailbox] 持久化失败：{e}")
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "registered_agents": len(self.registered_agents),
            "active_agents": sum(1 for v in self.registered_agents.values() if v),
            "total_messages": len(self.message_log),
            "pending_messages": sum(q.qsize() for q in self.mailboxes.values()),
        }


# 全局邮箱系统实例
mailbox_system = MailboxSystem(persist=True, persist_dir="message_logs")


async def send_message(msg: Message):
    """发送消息的便捷函数"""
    await mailbox_system.send(msg)


async def receive_message(agent_id: str, timeout: float = None) -> Optional[Message]:
    """接收消息的便捷函数"""
    return await mailbox_system.receive(agent_id, timeout)


async def broadcast_message(msg: Message):
    """广播消息的便捷函数"""
    await mailbox_system.broadcast(msg)
