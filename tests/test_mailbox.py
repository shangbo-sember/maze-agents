"""
邮箱系统测试
"""

import pytest
import asyncio
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.messages import Message, MessageType
from utils.mailbox import MailboxSystem, send_message, receive_message


@pytest.fixture
def mailbox():
    """创建邮箱系统"""
    return MailboxSystem(persist=False)


@pytest.fixture
def sample_message():
    """创建示例消息"""
    return Message(
        type=MessageType.EXPLORE_REQUEST,
        sender_id="coordinator",
        receiver_id="explorer_0",
        timestamp=datetime.now(),
        content={"from_pos": [0, 0], "direction": "up"},
    )


class TestMailboxSystem:
    """邮箱系统测试"""
    
    def test_register_agent(self, mailbox):
        """测试注册 Agent"""
        mailbox.register_agent("test_agent")
        assert "test_agent" in mailbox.mailboxes
        assert mailbox.registered_agents["test_agent"] == True
    
    def test_unregister_agent(self, mailbox):
        """测试注销 Agent"""
        mailbox.register_agent("test_agent")
        mailbox.unregister_agent("test_agent")
        assert "test_agent" not in mailbox.mailboxes
        assert mailbox.registered_agents["test_agent"] == False
    
    @pytest.mark.asyncio
    async def test_send_receive(self, mailbox, sample_message):
        """测试发送接收"""
        mailbox.register_agent("coordinator")
        mailbox.register_agent("explorer_0")
        
        await mailbox.send(sample_message)
        
        received = await mailbox.receive("explorer_0", timeout=1.0)
        assert received is not None
        assert received.type == MessageType.EXPLORE_REQUEST
        assert received.sender_id == "coordinator"
    
    @pytest.mark.asyncio
    async def test_broadcast(self, mailbox):
        """测试广播"""
        # 注册多个 Agent
        for i in range(3):
            mailbox.register_agent(f"agent_{i}")
        
        broadcast_msg = Message(
            type=MessageType.MAZE_SOLVED,
            sender_id="coordinator",
            receiver_id="broadcast",
            timestamp=datetime.now(),
            content={"solution": [[0, 0], [1, 1]]},
        )
        
        await mailbox.broadcast(broadcast_msg)
        
        # 检查所有 Agent 都收到了消息
        for i in range(3):
            received = await mailbox.receive(f"agent_{i}", timeout=1.0)
            assert received is not None
            assert received.type == MessageType.MAZE_SOLVED
    
    @pytest.mark.asyncio
    async def test_receive_timeout(self, mailbox):
        """测试接收超时"""
        mailbox.register_agent("test_agent")
        
        received = await mailbox.receive("test_agent", timeout=0.1)
        assert received is None
    
    @pytest.mark.asyncio
    async def test_receive_all(self, mailbox):
        """测试接收所有消息"""
        mailbox.register_agent("test_agent")
        
        # 发送多条消息
        for i in range(5):
            msg = Message(
                type=MessageType.EXPLORE_REQUEST,
                sender_id="coordinator",
                receiver_id="test_agent",
                timestamp=datetime.now(),
                content={"index": i},
            )
            await mailbox.send(msg)
        
        # 接收所有消息
        messages = await mailbox.receive_all("test_agent")
        assert len(messages) == 5
    
    def test_get_stats(self, mailbox):
        """测试统计信息"""
        for i in range(3):
            mailbox.register_agent(f"agent_{i}")
        
        stats = mailbox.get_stats()
        assert stats["registered_agents"] == 3
        assert stats["active_agents"] == 3
        assert stats["total_messages"] == 0


class TestMessage:
    """消息测试"""
    
    def test_message_creation(self, sample_message):
        """测试消息创建"""
        assert sample_message.message_id is not None
        assert sample_message.read == False
        assert sample_message.correlation_id is None
    
    def test_message_reply(self, sample_message):
        """测试消息回复"""
        reply = sample_message.create_reply(
            MessageType.EXPLORE_RESULT,
            {"result": "success"}
        )
        
        assert reply.type == MessageType.EXPLORE_RESULT
        assert reply.sender_id == "explorer_0"
        assert reply.receiver_id == "coordinator"
        assert reply.correlation_id == sample_message.message_id
        assert reply.reply_to == sample_message.message_id
    
    def test_message_to_dict(self, sample_message):
        """测试消息序列化"""
        data = sample_message.to_dict()
        
        assert data["type"] == "explore_request"
        assert data["sender_id"] == "coordinator"
        assert data["receiver_id"] == "explorer_0"
        assert "timestamp" in data
    
    def test_message_from_dict(self, sample_message):
        """测试消息反序列化"""
        data = sample_message.to_dict()
        restored = Message.from_dict(data)
        
        assert restored.type == sample_message.type
        assert restored.sender_id == sample_message.sender_id
        assert restored.content == sample_message.content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
