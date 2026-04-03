"""
协作迷宫系统 - 类型定义
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import uuid


class MessageType(Enum):
    """通信消息类型"""
    STATE_UPDATE = "state_update"           # 状态更新
    HELP_REQUEST = "help_request"           # 请求帮助
    HELP_RESPONSE = "help_response"         # 帮助响应
    SKILL_SHARE = "skill_share"             # 分享 skill
    SKILL_REQUEST = "skill_request"         # 请求 skill
    COORDINATION = "coordination"           # 协调行动
    PROGRESS_REPORT = "progress_report"     # 进度报告
    MAZE_SOLVED = "maze_solved"             # 迷宫解决
    ALL_MAZES_SOLVED = "all_mazes_solved"   # 所有迷宫解决


class GateType(Enum):
    """关卡类型"""
    MATH = "math"               # 数学题
    LOGIC = "logic"             # 逻辑题
    CIPHER = "cipher"           # 密码锁
    PUZZLE = "puzzle"           # 谜题
    COLLABORATION = "collaboration"  # 协作题（需要其他 Agent）
    SKILL_CHECK = "skill_check"      # Skill 检查


class SkillType(Enum):
    """Skill 类型"""
    MATH_COMPUTATION = "math_computation"     # 数学计算
    LOGICAL_REASONING = "logical_reasoning"   # 逻辑推理
    CIPHER_DECRYPTION = "cipher_decryption"   # 密码解密
    PATTERN_RECOGNITION = "pattern_recognition"  # 模式识别
    CODE_EXECUTION = "code_execution"         # 代码执行
    WEB_SEARCH = "web_search"                 # 网络搜索


@dataclass(frozen=True)
class Position:
    """迷宫位置"""
    x: int
    y: int
    
    def __str__(self):
        return f"({self.x},{self.y})"


@dataclass
class CellState:
    """单元格状态"""
    pos: Position
    is_visited: bool = False
    is_solved: bool = False
    gate: Optional['Gate'] = None
    required_skill: Optional[SkillType] = None


@dataclass
class Gate:
    """关卡定义"""
    gate_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    gate_type: GateType = GateType.MATH
    difficulty: int = 1  # 1-5
    description: str = ""
    required_skill: Optional[SkillType] = None
    requires_collaboration: bool = False
    collaborating_agents: List[str] = field(default_factory=list)
    
    # 关卡数据
    question: Optional[Dict[str, Any]] = None
    answer: Optional[Any] = None
    is_solved: bool = False
    attempts: int = 0


@dataclass
class AgentState:
    """Agent 状态"""
    agent_id: str
    maze_id: str
    current_pos: Position
    path_history: List[Position] = field(default_factory=list)
    solved_gates: List[str] = field(default_factory=list)
    available_skills: List[SkillType] = field(default_factory=list)
    shared_skills: Dict[str, SkillType] = field(default_factory=dict)  # agent_id -> skill
    is_stuck: bool = False
    stuck_at: Optional[Position] = None
    help_requests: int = 0


@dataclass
class StateMessage:
    """状态消息"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.STATE_UPDATE
    sender_id: str = ""
    receiver_id: str = "hub"  # 默认发送到 Hub
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 状态数据
    agent_state: Optional[AgentState] = None
    current_pos: Optional[Tuple[int, int]] = None
    is_stuck: bool = False
    progress_percent: float = 0.0
    
    # 帮助相关
    help_request: Optional[str] = None
    required_skill: Optional[SkillType] = None
    collaborating_agents: List[str] = field(default_factory=list)
    
    # Skill 共享
    shared_skill: Optional[SkillType] = None
    skill_target: Optional[str] = None
    
    # 协调相关
    coordination_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "timestamp": self.timestamp.isoformat(),
            "agent_state": self.agent_state.__dict__ if self.agent_state else None,
            "current_pos": self.current_pos,
            "is_stuck": self.is_stuck,
            "progress_percent": self.progress_percent,
            "help_request": self.help_request,
            "required_skill": self.required_skill.value if self.required_skill else None,
            "collaborating_agents": self.collaborating_agents,
            "shared_skill": self.shared_skill.value if self.shared_skill else None,
            "skill_target": self.skill_target,
            "coordination_data": self.coordination_data,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateMessage':
        """从字典创建"""
        agent_state = None
        if data.get("agent_state"):
            agent_state = AgentState(**data["agent_state"])
        
        required_skill = None
        if data.get("required_skill"):
            required_skill = SkillType(data["required_skill"])
        
        shared_skill = None
        if data.get("shared_skill"):
            shared_skill = SkillType(data["shared_skill"])
        
        return cls(
            message_id=data["message_id"],
            message_type=MessageType(data["message_type"]),
            sender_id=data["sender_id"],
            receiver_id=data["receiver_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            agent_state=agent_state,
            current_pos=tuple(data["current_pos"]) if data.get("current_pos") else None,
            is_stuck=data.get("is_stuck", False),
            progress_percent=data.get("progress_percent", 0.0),
            help_request=data.get("help_request"),
            required_skill=required_skill,
            collaborating_agents=data.get("collaborating_agents", []),
            shared_skill=shared_skill,
            skill_target=data.get("skill_target"),
            coordination_data=data.get("coordination_data"),
        )


@dataclass
class MazeConfig:
    """迷宫配置"""
    maze_id: str
    width: int
    height: int
    agent_id: str
    start_pos: Position = field(default_factory=lambda: Position(0, 0))
    end_pos: Optional[Position] = None
    gate_density: float = 0.8  # 有关卡的单元格比例
    
    def __post_init__(self):
        if self.end_pos is None:
            self.end_pos = Position(self.width - 1, self.height - 1)


@dataclass
class CollaborationHub:
    """协作中心"""
    hub_id: str = "collaboration_hub"
    registered_agents: Dict[str, AgentState] = field(default_factory=dict)
    message_queue: List[StateMessage] = field(default_factory=list)
    shared_knowledge: Dict[str, Any] = field(default_factory=dict)
    global_progress: float = 0.0
    all_solved: bool = False
    
    def broadcast(self, message: StateMessage):
        """广播消息"""
        message.receiver_id = "broadcast"
        self.message_queue.append(message)
    
    def send_to(self, message: StateMessage, target_id: str):
        """发送给特定 Agent"""
        message.receiver_id = target_id
        self.message_queue.append(message)
    
    def get_messages_for(self, agent_id: str) -> List[StateMessage]:
        """获取发送给特定 Agent 的消息"""
        messages = []
        for msg in self.message_queue:
            if msg.receiver_id == agent_id or msg.receiver_id == "broadcast":
                if msg.sender_id != agent_id:  # 不接收自己的消息
                    messages.append(msg)
        return messages
    
    def clear_processed(self, agent_id: str):
        """清理已处理的消息"""
        self.message_queue = [
            msg for msg in self.message_queue
            if not (msg.receiver_id == agent_id or msg.receiver_id == "broadcast")
            or msg.sender_id == agent_id
        ]
