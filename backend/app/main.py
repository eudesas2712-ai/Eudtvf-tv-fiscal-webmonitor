from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.bootstrap import bootstrap_system
from app.routers.projects import router as projects_router
from app.routers.sources import router as sources_router
from app.routers.terms import router as terms_router
from app.routers.ingest import router as ingest_router
from app.routers.items import router as items_router
from app.routers.banners import router as banners_router
from app.routers.registry import router as registry_router
from app.routers.intel_compare import router as intel_compare_router
from app.routers.project_reports import router as project_reports_router
from app.routers.editorial import router as editorial_router
from app.routers.identification import router as identification_router
from app.routers.alerts import router as alerts_router
from app.routers.notifications import router as notifications_router
from app.routers.auth import router as auth_router
from app.routers.executive_dashboard import router as executive_dashboard_router
from app.routers.maintenance import router as maintenance_router
from app.routers.system_health import router as system_health_router, public_router as system_health_public_router
from app.routers import market_intelligence
from app.routers import scheduler_admin
from app.services.snapshot_scheduler import start_snapshot_scheduler
from app.services.backup_scheduler import start_auto_backup_scheduler
from app.db.session import SessionLocal
from app.services.permissions_service import validate_request_permission


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[app] iniciando lifespan...")

    bootstrap_system()
    snapshot_stop_event = start_snapshot_scheduler()
    backup_stop_event = start_auto_backup_scheduler()

    try:
        yield
    finally:
        if snapshot_stop_event:
            snapshot_stop_event.set()
        if backup_stop_event:
            backup_stop_event.set()


app = FastAPI(
    title="TV Fiscal WebMonitor",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def auth_permission_middleware(request, call_next):
    db = SessionLocal()
    try:
        validate_request_permission(db, request)
    except Exception as exc:
        # Preserva respostas HTTPException em formato JSON, sem derrubar CORS/app.
        from fastapi import HTTPException
        if isinstance(exc, HTTPException):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        raise
    finally:
        db.close()
    return await call_next(request)

app.include_router(projects_router, prefix="/projects", tags=["projects"])
app.include_router(sources_router, prefix="/sources", tags=["sources"])
app.include_router(terms_router, prefix="/terms", tags=["terms"])
app.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
app.include_router(items_router, prefix="/items", tags=["items"])
app.include_router(banners_router)
app.include_router(registry_router)
app.include_router(intel_compare_router)
app.include_router(project_reports_router)
app.include_router(editorial_router)
app.include_router(identification_router)
app.include_router(alerts_router)
app.include_router(notifications_router)
app.include_router(auth_router)
app.include_router(executive_dashboard_router)
app.include_router(maintenance_router)
app.include_router(system_health_router)
app.include_router(system_health_public_router)
app.include_router(market_intelligence.router)
app.include_router(scheduler_admin.router)


@app.get("/health")
def health():
    return {"status": "ok", "app": "TV Fiscal WebMonitor"}
