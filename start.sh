#!/bin/bash
echo "========================================"
echo "    数标云管 - 一键启动 (Mac/Linux)"
echo "========================================"
echo ""

echo "[1/3] 启动后端服务..."
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..
sleep 3

echo "[2/3] 启动前端服务..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..
sleep 3

echo ""
echo "[3/3] 启动完成！"
echo ""
echo "后端 API: http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo "前端页面: http://localhost:5173"
echo ""
echo "默认管理员: admin / admin123"
echo ""
echo "按 Ctrl+C 停止所有服务"
wait
