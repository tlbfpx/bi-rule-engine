#!/bin/bash
# BI Rule Engine (Backend) — 快速启动脚本
set -e

echo "============================================"
echo " BI Rule Engine — 后端启动脚本"
echo "============================================"

# 检查 Python 版本
PYTHON=$(which python3.12 || which python3)
echo "Python: $($PYTHON --version)"

# 安装依赖
echo ""
echo "[1/3] 安装依赖..."
cd "$(dirname "$0")"
pip install -e . --quiet 2>&1 | tail -1

# 初始化数据库
echo ""
echo "[2/3] 初始化数据库..."
echo "  确保 MySQL 和 Redis 已启动 (docker compose -f ../docker-compose.yml up -d mysql redis)"
echo "  运行数据库迁移: alembic upgrade head"

# 启动 API
echo ""
echo "[3/3] 启动 API 服务..."
echo "  开发模式: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo "  生产模式: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"
echo ""
echo "  文档地址: http://localhost:8000/docs"
echo "  健康检查: http://localhost:8000/api/health"
echo ""
echo "============================================"
echo " 快速测试: PYTHONPATH=. python tests/test_rules.py"
echo "============================================"
