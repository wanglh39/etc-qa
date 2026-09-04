#!/bin/bash
set -e

echo "================================================"
echo "  ETC客服QA — 一键开发环境搭建"
echo "================================================"
echo

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未检测到Python3，请先安装Python 3.10+"
    exit 1
fi
echo "✓ Python 已安装"

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 未检测到Docker，请先安装Docker"
    exit 1
fi
echo "✓ Docker 已安装"

# 创建.env
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "📋 从模板创建 .env 文件..."
        cp .env.example .env
        echo
        echo "⚠️  请编辑 .env 填入你的 DEEPSEEK_API_KEY"
        echo "   路径: $(pwd)/.env"
        echo
        ${EDITOR:-nano} .env
    else
        echo "❌ 未找到 .env.example"
        exit 1
    fi
else
    echo "✓ .env 文件已存在"
fi

# 安装Python依赖
echo
echo "=== 安装Python依赖 ==="
pip install --no-deps aliyunsdkcore>=1.0.3 -q
pip install -r requirements-dev.txt -q
echo "✓ 依赖安装完成"

# 启动MySQL容器
echo
echo "=== 启动MySQL容器 ==="
docker compose -f docker-compose.dev.yml up -d mysql
echo "等待MySQL就绪..."
sleep 15

# 初始化数据库
echo
echo "=== 初始化数据库 ==="
export ETC_QA_ENV=dev
python3 scripts/data/init_db.py dev

echo
echo "================================================"
echo "  ✓ 开发环境搭建完成！"
echo "================================================"
echo
echo "启动方式:"
echo "  Docker: docker compose -f docker-compose.dev.yml up etc-qa"
echo "  本地:   python3 main.py"
echo
echo "API文档: http://localhost:8000/docs"