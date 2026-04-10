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
- **客户管理**: CRUD，搜索筛选，转化漏斗，客户价值分析（生命周期价值）
- **项目管理**: 项目/任务/里程碑，进度追踪，利润分析（收入/成本/利润率），工时偏差记录，项目关闭管理
- **合同管理**: 自动编号，状态流转，金额同步，变更单管理
- **报价管理**: 报价 CRUD，金额计算引擎，实时预览，状态流转（草稿→发送→接受/拒绝/取消），报价转合同，客户报价 Tab，看板指标（转化率/月发出数），需求冻结机制
- **财务管理**: 收支记录，月度报表，应收账款，结算管理，发票台账
- **数据看板**: 核心指标，营收趋势，数据库备份，催办提醒，现金流预警，WIP 看板
- **需求管理**: 需求条目、验收标准、跟踪矩阵，变更冻结机制
- **验收管理**: 验收计划、验收记录
- **交付物管理**: 交付物登记、交付追踪
- **版本发布**: 版本规划、发布记录
- **售后维护期**: 维护周期管理、维护提醒
- **外包协作**: 外包记录，外包费用追踪
- **现金流预测**: 周度/月度现金流预测，合同回款计划
- **里程碑收款**: 里程碑与收款绑定，状态流转（未付款→已开票→已到账），逾期预警
- **数据导出**: Excel/PDF 导出（财务报表、客户列表、项目列表、合同列表、增值税台账）
- **文件管理**: 文件索引，合同附件管理
- **客户资产**: 客户关联资产记录
- **风险控制**: 客户风险等级、逾期里程碑/金额展示、固定成本管理、进项发票、粗利润概览、一致性校验
- **帮助引导**: 业务流程总览、字段级提示、页面帮助抽屉、错误码帮助对话框、全局错误拦截

## 版本历史

| 版本 | 功能 |
|------|------|
| v1.0 | 基础模块：认证、客户、项目、合同、财务、看板 |
| v1.1 | 催办提醒、文件索引、财务结算、报价管理、客户资产、逾期检查、日志系统 |
| v1.2 | 看板增强、备份验证 |
| v1.3 | 外包协作、发票台账、现金流预测、增值税汇总 |
| v1.4 | 项目利润核算、客户生命周期价值、数据导出（Excel/PDF） |
| v1.5 | 需求管理、验收管理、交付物管理、版本发布、变更单、售后维护期 + 现金流预警 |
| v1.6 | 报价单模块：金额计算引擎、状态流转、实时预览、报价转合同、客户报价 Tab、看板报价指标 |
| v1.7 | 项目执行控制：变更冻结机制、里程碑收款绑定、项目关闭强制条件、WIP 看板、工时偏差记录 |
| v1.8 | 发票台账、财务导出（Excel）、对账报表、Bug 修复 |
| v1.9 | 风险展示、成本视角、固定成本管理、进项发票、逾期预警、一致性校验、粗利润概览 |
| v1.10 | 帮助引导系统：错误码帮助（10 个）、流程总览页、字段提示（6 模块）、页面帮助抽屉（7 页面）、ErrorHelp 对话框、全局错误拦截 |

## 数据库备份

在仪表盘页面点击"立即备份数据库"按钮，SQLite 数据库文件将被复制到 `./backups` 目录，文件名包含时间戳。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy 2.0 + SQLite |
| 前端 | Vue 3 + Element Plus + Pinia |
| 认证 | JWT (python-jose) + bcrypt |
| 导出 | openpyxl (Excel) + reportlab (PDF) |
| 测试 | pytest + httpx |

## 项目结构

```
├── backend/          # FastAPI 后端
│   ├── app/          # 应用代码
│   │   ├── api/      # API 路由
│   │   ├── core/     # 安全/异常/工具函数
│   │   ├── crud/     # 数据库操作
│   │   ├── models/   # 数据模型
│   │   └── schemas/  # 数据验证
│   └── tests/        # 测试
├── frontend/         # Vue 3 前端
│   └── src/
│       ├── api/      # API 封装（含全局错误拦截）
│       ├── views/    # 页面
│       ├── components/ # 组件（ErrorHelp/FieldTip/PageHelpDrawer）
│       ├── constants/ # 静态数据（help.js）
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
