"""ClipResumen FastAPI application entrypoint.

This is the Fase 0 skeleton: it wires up configuration, CORS and a health
router. Business routers (summarize, auth, summaries, billing) are mounted in
later phases.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, billing, health, summary

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(billing.router)
app.include_router(summary.router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "ok",
        "docs": "/docs",
    }
