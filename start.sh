#!/bin/bash

# DifyChatBackend 启动脚本
# 用于 Linux 环境

echo " 启动 DifyChatBackend..."

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo " Python3 未找到，请先安装 Python3"
    exit 1
fi

# 检查虚拟环境
if [[ -d ".venv" ]]; then
    echo " 激活虚拟环境..."
    source .venv/bin/activate
elif [[ -d "venv" ]]; then
    echo " 激活虚拟环境..."
    source venv/bin/activate
else
    echo "  未找到虚拟环境，使用系统 Python"
fi

# 检查依赖
echo " 检查依赖..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo " 安装依赖..."
    pip install -r requirements.txt
fi

# 检查环境配置文件
if [[ ! -f ".env" ]]; then
    echo "  未找到 .env 文件"
    if [[ -f ".env.example" ]]; then
        echo " 从 .env.example 复制配置..."
        cp .env.example .env
        echo "  请编辑 .env 文件设置正确的配置"
    fi
fi

# 检查数据目录
if [[ ! -d "data" ]]; then
    echo " 创建数据目录..."
    mkdir -p data
fi

# 启动应用
echo " 启动应用..."
python3 app.py
