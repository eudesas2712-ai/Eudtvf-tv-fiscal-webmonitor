from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.bootstrap import bootstrap_system
from app.routers import market_intelligence
from app.routers.banners import router as banners_router
from app.routers.ingest import router as ingest_router
from app.routers.items import router as items_router
from app.routers.projects import router as projects_router
from app.routers.sources import router as sources_router
from app.routers.terms import router as terms_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[app] iniciando lifespan...")
    bootstrap_system()
    yield
    print("[app] encerrando aplicação...")


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
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router, prefix="/projects", tags=["projects"])
app.include_router(sources_router, prefix="/sources", tags=["sources"])
app.include_router(terms_router, prefix="/terms", tags=["terms"])
app.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
app.include_router(items_router, prefix="/items", tags=["items"])
app.include_router(banners_router)
app.include_router(market_intelligence.router)


@app.get("/health")
def health():
    return {"status": "ok", "app": "TV Fiscal WebMonitor"}