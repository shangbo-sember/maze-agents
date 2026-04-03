# 🚀 快速启动指南

## 运行协作系统

```bash
cd /home/admin/.openclaw/workspace/maze_agents

# 基本运行（4 个 Agent，30 秒超时）
python3 -m collaborative.main --agents 4 --timeout 30

# 详细输出（显示 Hub 消息）
python3 -m collaborative.main --agents 4 --timeout 60 --verbose

# 自定义 Agent 数量
python3 -m collaborative.main --agents 2 --timeout 30
```

## 系统特点

### 独立上下文
- ✅ 每个 Agent 有自己的 MazeState
- ✅ 不能直接访问其他 Agent 的内存
- ✅ 只能通过 Hub 通信

### 通信协议
- `STATE_UPDATE` - 状态更新
- `HELP_REQUEST` - 请求帮助
- `HELP_RESPONSE` - 帮助响应
- `SKILL_SHARE` - 分享 skill
- `COORDINATION` - 协调行动

### Skill 系统
| Agent | 初始 Skill | 可解决关卡 |
|-------|-----------|-----------|
| Agent 1 | Math | 数学题 |
| Agent 2 | Logic | 逻辑题 |
| Agent 3 | Cipher | 密码题 |
| Agent 4 | Pattern | 模式题 |

### 关卡类型
- 🔢 数学题（需要计算）
- 🔍 逻辑题（需要推理）
- 🗝️ 密码锁（需要解密）
- 🧩 谜题（需要模式识别）
- 🤝 协作题（需要其他 Agent 帮助）

## 输出示例

```
🤖 [agent_1] 启动
   迷宫：4x4
   初始 skills: ['math_computation']

🔒 [agent_1] 遇到关卡:
   类型：puzzle
   ❌ 缺少 skill: pattern_recognition

🆘 [agent_1] 请求帮助:
   需要：pattern_recognition

📨 [agent_4] 收到消息:
   类型：help_request
   发送者：agent_1

✅ [agent_4] 分享 skill: pattern_recognition

🔒 [agent_1] 遇到关卡:
   ✅ 关卡解决！
```

## 协作流程

1. Agent 遇到不会的关卡
2. 发送 HELP_REQUEST 到 Hub
3. Hub 广播给所有 Agent
4. 有对应 skill 的 Agent 响应
5. 通过 SKILL_SHARE 分享 skill
6. 请求者学会 skill，解决关卡
7. 继续前进

## 查看结果

运行完成后会显示：
- 每个 Agent 的步数、解决关卡数
- 帮助请求次数
- Skill 共享次数
- 协作成功率
