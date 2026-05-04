"""FastAPI application entry point — serves API + bundled frontend."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .routes import router
from .export import router as export_router
from .admin import router as admin_router
from .database import router as database_router, valuation_router as db_valuation_router

app = FastAPI(title="Valuation Engine API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(export_router)
# Admin + DB endpoints live under /api/admin and /api/database; mount at /api/*.
app.include_router(admin_router, prefix="/api")
app.include_router(database_router, prefix="/api")
app.include_router(db_valuation_router, prefix="/api")

DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve frontend static assets (JS, CSS, etc.)
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    # Catch-all: serve index.html for any non-API route (SPA client-side routing)
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        return FileResponse(str(DIST_DIR / "index.html"))
