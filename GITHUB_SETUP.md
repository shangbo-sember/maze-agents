# GitHub 推送指南

## 当前状态

✅ Git 仓库已初始化  
✅ 文件已提交（33 个文件，5273 行代码）  
✅ 远程仓库已关联：`git@github.com:shangbo-sember/maze-agents.git`  
⚠️  需要手动推送（需要 GitHub 认证）

---

## 方法 1：使用 HTTPS 推送（推荐）

```bash
cd /home/admin/.openclaw/workspace/maze_agents

# 推送代码
git push -u origin main
```

系统会提示输入 GitHub 用户名和密码：
- **用户名**: `shangbo-sember`
- **密码**: 使用 **Personal Access Token**（不是登录密码）

### 创建 Personal Access Token

1. 访问：https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 选择权限：`repo` (Full control of private repositories)
4. 生成后复制 token
5. 推送时使用 token 作为密码

---

## 方法 2：使用 SSH 推送

### 生成 SSH 密钥

```bash
# 生成新的 SSH 密钥
ssh-keygen -t ed25519 -C "your_email@example.com"

# 查看公钥
cat ~/.ssh/id_ed25519.pub
```

### 添加到 GitHub

1. 复制公钥内容（`id_ed25519.pub` 文件内容）
2. 访问：https://github.com/settings/keys
3. 点击 "New SSH key"
4. 粘贴公钥，保存

### 推送

```bash
cd /home/admin/.openclaw/workspace/maze_agents
git push -u origin main
```

---

## 方法 3：使用 GitHub CLI

```bash
# 安装 gh
sudo apt install gh  # 或 brew install gh

# 认证
gh auth login

# 推送
cd /home/admin/.openclaw/workspace/maze_agents
git push -u origin main
```

---

## 验证推送

推送成功后，访问：
https://github.com/shangbo-sember/maze-agents

应该能看到所有文件。

---

## 后续操作

### 启用 GitHub Actions

推送后，GitHub Actions 会自动运行测试：
https://github.com/shangbo-sember/maze-agents/actions

### 添加仓库描述

在 GitHub 网站上：
1. 关于 → 编辑
2. 描述：`Multi-Agent Maze Solver with Coordinator-Worker Architecture`
3. 网站：（可选）
4.  Topics：`multi-agent`, `maze-solver`, `python`, `asyncio`

### 保护主分支

Settings → Branches → Add branch protection rule:
- Branch name pattern: `main`
- Require pull request reviews before merging

---

## 常见问题

**Q: 推送时提示 "Permission denied"**  
A: 确保 SSH 密钥已添加到 GitHub，或使用 HTTPS + Personal Access Token

**Q: 提示 "repository not found"**  
A: 确保已在 GitHub 创建仓库，或检查用户名是否正确

**Q: 推送后看不到文件**  
A: 检查是否推送到正确的分支（main）
