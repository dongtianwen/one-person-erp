from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.endpoints import auth, customers, projects, contracts, finances, dashboard, changelogs, reminders, file_indexes
from app.database import async_session, engine
from app.models.base import Base
from app.api.endpoints.auth import create_default_admin


app = FastAPI(
    title=settings.APP_NAME,
    description="数标云管 - 一体化业务管理系统 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        from app.services.db_migration import migrate_v11
        await migrate_v11(conn)
    async with async_session() as session:
        await create_default_admin(session)
        try:
            from app.services.seed import seed_default_data
            await seed_default_data(session)
        except Exception:
            pass
    try:
        from app.services.scheduler import setup_scheduler
        setup_scheduler(app)
    except ImportError:
        pass


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
