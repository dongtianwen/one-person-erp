# 数标云管 - ShuBiao Cloud Manager

> 一人软件公司一体化业务管理平台

## 快速开始

### 环境要求
- Python 3.10+
- Node.js 18+
- uv (Python 包管理器)

### 一键启动

**Windows:**
```bash
start.bat
```

**Mac/Linux:**
```bash
chmod +x start.sh
./start.sh
```

### 手动启动

**后端:**
```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端:**
```bash
cd frontend
npm install
npm run dev
```

## 默认账户

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |

## 服务地址

| 服务 | 地址 |
|------|------|
| 前端页面 | http://localhost:5173 |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |

## 功能模块

- **认证系统**: JWT 认证，账户锁定，Token 刷新
- **客户管理**: CRUD，搜索筛选，转化漏斗
- **项目管理**: 项目/任务/里程碑，进度追踪
- **合同管理**: 自动编号，状态流转，金额同步
- **财务管理**: 收支记录，月度报表，应收账款
- **数据看板**: 核心指标，营收趋势，数据库备份

## 数据库备份

在仪表盘页面点击"立即备份数据库"按钮，SQLite 数据库文件将被复制到 `./backups` 目录，文件名包含时间戳。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy 2.0 + SQLite |
| 前端 | Vue 3 + Element Plus + Pinia |
| 认证 | JWT (python-jose) + bcrypt |
| 测试 | pytest + httpx |

## 项目结构

```
├── backend/          # FastAPI 后端
│   ├── app/          # 应用代码
│   │   ├── api/      # API 路由
│   │   ├── core/     # 安全/异常
│   │   ├── crud/     # 数据库操作
│   │   ├── models/   # 数据模型
│   │   └── schemas/  # 数据验证
│   └── tests/        # 测试
├── frontend/         # Vue 3 前端
│   └── src/
│       ├── api/      # API 封装
│       ├── views/    # 页面
│       ├── components/ # 组件
│       ├── router/   # 路由
│       └── store/    # 状态管理
├── openspec/         # OpenSpec 规格
├── docs/             # 文档
├── start.bat         # Windows 启动脚本
└── start.sh          # Mac/Linux 启动脚本
```

## 环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite+aiosqlite:///./shubiao.db
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## 开发规范

- Python: PEP 8 + 强制类型注解
- 前端: ESLint
- 提交: Conventional Commits
- 语言: 简体中文 UI/日志/注释
