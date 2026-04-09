import logging
from contextlib import asynccontextmanager

from alembic.config import Config
from alembic import command
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.endpoints import (
    auth,
    customers,
    projects,
    contracts,
    finances,
    dashboard,
    changelogs,
    reminders,
    file_indexes,
    quotations,
    customer_assets,
    cashflow,
    exports,
    finance_export,
    reconciliation,
    requirements,
    acceptances,
    deliverables,
    releases,
    change_orders,
    project_change_orders,
    maintenance,
    invoices,
)
from app.database import async_session
from app.api.endpoints.auth import create_default_admin

logger = logging.getLogger(__name__)


def run_alembic_migration() -> None:
    """Run alembic migrations synchronously on startup."""
    import os

    alembic_ini = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    cfg = Config(alembic_ini)
    command.upgrade(cfg, "head")
    logger.info("Alembic migrations applied successfully")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize logging system
    try:
        from app.core.logging import setup_logging
        setup_logging()
    except Exception as e:
        logging.warning("Logging setup failed: %s", e)

    logger.info("系统启动事件 | action=start")

    # Run alembic migrations on startup
    try:
        run_alembic_migration()
    except Exception as e:
        logger.error("Migration failed: %s", e)
        raise SystemExit(1) from e

    # Seed default data and create admin
    async with async_session() as session:
        await create_default_admin(session)
        try:
            from app.services.seed import seed_default_data
            await seed_default_data(session)
        except Exception as e:
            logger.warning("Seed failed (may be expected): %s", e)

        # Trigger point A: Full overdue check on startup (once per process)
        try:
            from app.services.overdue_check import run_startup_check
            result = await run_startup_check(session)
            if result:
                logger.info("启动逾期检查完成 | result=%s", result)
        except Exception as e:
            logger.error("启动逾期检查失败: %s", e)

    # Setup scheduler
    try:
        from app.services.scheduler import setup_scheduler
        setup_scheduler(app)
    except ImportError:
        pass

    yield

    logger.info("系统关闭事件 | action=stop")


app = FastAPI(
    title=settings.APP_NAME,
    description="数标云管 - 一体化业务管理系统 API",
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(customers.router, prefix="/api/v1/customers", tags=["客户管理"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["项目管理"])
app.include_router(contracts.router, prefix="/api/v1/contracts", tags=["合同管理"])
app.include_router(finances.router, prefix="/api/v1/finances", tags=["财务管理"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["数据看板"])
app.include_router(changelogs.router, prefix="/api/v1/changelogs", tags=["变更日志"])
app.include_router(reminders.router, prefix="/api/v1/reminders", tags=["提醒管理"])
app.include_router(file_indexes.router, prefix="/api/v1/file-indexes", tags=["文件管理"])
app.include_router(quotations.router, prefix="/api/v1/quotations", tags=["报价单管理"])
app.include_router(customer_assets.router, prefix="/api/v1/customers/{customer_id}/assets", tags=["客户资产"])
app.include_router(cashflow.router, prefix="/api/v1/cashflow", tags=["现金流预测"])
app.include_router(invoices.router, prefix="/api/v1/invoices", tags=["发票管理"])
# v1.4 数据导出
app.include_router(exports.router, prefix="/api/v1/export", tags=["数据导出"])
# v1.8 财务导出
app.include_router(finance_export.router, prefix="/api/v1/finance/export", tags=["财务导出"])
# v1.8 对账
app.include_router(reconciliation.router, prefix="/api/v1/finance/reconciliation", tags=["对账管理"])
app.include_router(requirements.router, prefix="/api/v1/projects/{project_id}/requirements", tags=["需求管理"])
app.include_router(acceptances.router, prefix="/api/v1/projects/{project_id}/acceptances", tags=["验收管理"])
app.include_router(deliverables.router, prefix="/api/v1/projects/{project_id}/deliverables", tags=["交付物管理"])
app.include_router(releases.router, prefix="/api/v1/projects/{project_id}/releases", tags=["版本发布"])
app.include_router(change_orders.router, prefix="/api/v1/contracts/{contract_id}/change-orders", tags=["变更单管理"])
app.include_router(project_change_orders.router, prefix="/api/v1/projects/{project_id}/change-orders", tags=["变更单摘要"])
app.include_router(maintenance.router, prefix="/api/v1/projects/{project_id}/maintenance-periods", tags=["售后/维护期"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
