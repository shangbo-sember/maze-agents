#!/bin/bash

# Maze Agents - GitHub 部署脚本
# 用法：./deploy_to_github.sh YOUR_USERNAME

set -e

if [ -z "$1" ]; then
    echo "❌ 错误：请提供 GitHub 用户名"
    echo "用法：$0 YOUR_USERNAME"
    exit 1
fi

USERNAME=$1
REPO_NAME="maze-agents"
REMOTE_URL="https://github.com/${USERNAME}/${REPO_NAME}.git"

echo "🚀 开始部署到 GitHub..."
echo "   用户名：${USERNAME}"
echo "   仓库：${REPO_NAME}"
echo ""

# 检查 git 是否安装
if ! command -v git &> /dev/null; then
    echo "❌ git 未安装，请先安装 git"
    exit 1
fi

# 初始化仓库
if [ ! -d ".git" ]; then
    echo "📦 初始化 git 仓库..."
    git init
fi

# 添加所有文件
echo "📝 添加文件..."
git add .

# 创建提交
echo "💾 创建提交..."
git commit -m "Initial commit: Multi-agent maze solver

- Coordinator-Worker architecture
- 4 agent roles (Coordinator, Explorer, Memory, Verifier)
- Async message passing
- 2D and 3D maze support
- Detailed thinking logs
- Real-time visualization" || echo "⚠️  没有变化需要提交"

# 重命名分支
git branch -M main

# 添加远程仓库
echo "🔗 关联远程仓库..."
git remote remove origin 2>/dev/null || true
git remote add origin $REMOTE_URL

# 推送
echo "⬆️  推送到 GitHub..."
echo ""
echo "📋 下一步："
echo "   1. 在 GitHub 创建仓库：https://github.com/new"
echo "   2. 仓库名：${REPO_NAME}"
echo "   3. 不要勾选 'Initialize with README'"
echo "   4. 创建后按回车继续推送..."
echo ""
read -p "按回车继续推送..."

git push -u origin main

echo ""
echo "✅ 部署完成！"
echo "   仓库地址：https://github.com/${USERNAME}/${REPO_NAME}"
