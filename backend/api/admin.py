"""
Admin-only endpoints — upload, refresh, status. Gated by an env-var token.

Set `AD_CC_ADMIN_TOKEN` in the server environment. Client sends the token
in the `X-Admin-Token` header on every admin request. No token set → all
admin endpoints respond 404 (feature dormant — what open-source users
see until they set their own token).

Endpoints:
  GET  /api/admin/whoami                    check token; returns {admin: bool}
  GET  /api/admin/dataset-status            file manifests + last ingest summary
  POST /api/admin/upload/markets-dataset    multipart upload of a ginzu_cc_*.xls
  POST /api/admin/upload/damodaran          multipart upload of a Damodaran file
  POST /api/admin/upload/industry-lookup    multipart upload of indname.xlsx
  POST /api/admin/refresh-database          rebuild SQLite from current .xls files
  POST /api/admin/refresh-knowledge-base    reload DamodaranStore + IndustryMapper

Uploads write atomically (.tmp + rename) and auto-trigger the matching
refresh. Raw file download is NEVER exposed — confidentiality is
structural.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, UploadFile, File

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_sources import us_cn_hk_db as db

router = APIRouter(prefix="/admin", tags=["admin"])

# Folder locations (hardcoded per the plan §6e).
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MARKETS_DATASET_DIR = REPO_ROOT / "US_CN_HK_dataset"
DAMODARAN_DIR = REPO_ROOT / "knowledge_base" / "damodaran"
INDUSTRY_LOOKUP_DIR = REPO_ROOT / "knowledge_base" / "industry_lookup"

# Upload safety rules
# Accept both the legacy layout (ginzu_cc_<N>_<M>.xls) and the current
# team layout (<prefix>_<N>.xls, <prefix>_<N> (K).xls). The ingester's
# _group_files() uses the same shape. Spaces and "(K)" re-download
# suffixes are allowed so files exported by browsers work as-is.
ALLOWED_MARKETS_PATTERN = re.compile(
    r"^[\w.\- ]+_\d+(?:_\d+|\s*\(\d+\))?\.xlsx?$",
    re.IGNORECASE,
)
ALLOWED_INDUSTRY_LOOKUP_NAMES = {"indname.xlsx"}
MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB

# "...(1).xls" → "....xls"  (browsers add this suffix on re-download)
_DOWNLOAD_SUFFIX = re.compile(r'\s*\(\d+\)(?=\.[^.]+$)')
# Characters unsafe in saved filenames (anything outside a permissive set)
_UNSAFE_FILENAME_CHARS = re.compile(r"[^\w.\- ()']")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _admin_token() -> str | None:
    t = os.environ.get("AD_CC_ADMIN_TOKEN")
    return t.strip() if t and t.strip() else None


def require_admin(x_admin_token: Annotated[str | None, Header()] = None) -> None:
    """Dependency — raises 401 if the token doesn't match.
    Raises 404 if admin features are disabled (no env var set), so unauth
    users can't even tell the endpoints exist."""
    expected = _admin_token()
    if expected is None:
        raise HTTPException(status_code=404, detail="Not found")
    if not x_admin_token or x_admin_token.strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid admin token")


# ---------------------------------------------------------------------------
# whoami — lightweight check for the frontend to decide whether to show the
# Data Sources sidebar item.
# ---------------------------------------------------------------------------

@router.get("/whoami")
def whoami(x_admin_token: Annotated[str | None, Header()] = None) -> dict:
    """Returns {admin: bool} without raising. Frontend uses this to decide
    whether to render the admin sidebar item (idempotent, cheap)."""
    expected = _admin_token()
    if expected is None:
        # Feature dormant — frontend should hide the sidebar item entirely.
        return {"admin": False, "configured": False}
    is_admin = bool(x_admin_token and x_admin_token.strip() == expected)
    return {"admin": is_admin, "configured": True}


# ---------------------------------------------------------------------------
# dataset-status — file manifest for all three folders.
# ---------------------------------------------------------------------------

def _manifest(folder: Path, pattern: str = "*") -> list[dict]:
    if not folder.exists():
        return []
    out = []
    for f in sorted(folder.glob(pattern)):
        if f.is_file():
            stat = f.stat()
            out.append({
                "name": f.name,
                "size_bytes": stat.st_size,
                "size_human": _fmt_bytes(stat.st_size),
                "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            })
    return out


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}B"
        n /= 1024
    return f"{n}"


@router.get("/dataset-status")
def dataset_status(_: None = None, x_admin_token: Annotated[str | None, Header()] = None) -> dict:
    require_admin(x_admin_token)

    # Match the ingester's file-discovery pattern exactly (see
    # `_group_files` in tools/ingest_us_cn_hk_dataset.py) so the UI shows
    # every file that will actually feed the rebuild — NOT just legacy
    # `ginzu_cc_*.xls`. Critical: the ingester unioning files the operator
    # can't see is exactly how stale+current data get silently mixed.
    markets_files = _manifest(MARKETS_DATASET_DIR, "*.xls*")
    damodaran_files = _manifest(DAMODARAN_DIR, "*.xls*")
    lookup_files = _manifest(INDUSTRY_LOOKUP_DIR, "*.xls*")

    # DB state — report both the active (admin-built or seed) and the
    # shipped seed so the operator can tell which one is live and
    # whether the seed is stale relative to a recent admin refresh.
    active_path = db.get_db_path()
    db_state: dict = {
        "path": str(active_path),
        "exists": active_path.exists(),
        "is_seed": active_path == db.SEED_DB_PATH,
    }
    db_state["size_bytes"] = active_path.stat().st_size if db_state["exists"] else None
    db_state["size_human"] = _fmt_bytes(db_state["size_bytes"]) if db_state["exists"] else None

    # Seed status — shipped to the public repo
    db_state["seed_path"] = str(db.SEED_DB_PATH)
    db_state["seed_exists"] = db.SEED_DB_PATH.exists()
    if db_state["seed_exists"]:
        ss = db.SEED_DB_PATH.stat()
        db_state["seed_size_human"] = _fmt_bytes(ss.st_size)
        db_state["seed_mtime"] = datetime.fromtimestamp(ss.st_mtime).isoformat(timespec="seconds")
    # Admin DB status — private to this instance
    db_state["admin_db_path"] = str(db.DB_PATH)
    db_state["admin_db_exists"] = db.DB_PATH.exists()
    if db_state["admin_db_exists"]:
        adb_stat = db.DB_PATH.stat()
        db_state["admin_db_size_human"] = _fmt_bytes(adb_stat.st_size)
        db_state["admin_db_mtime"] = datetime.fromtimestamp(adb_stat.st_mtime).isoformat(timespec="seconds")

    last_ingest = None
    if db_state["exists"]:
        try:
            with db.get_connection() as conn:
                last_ingest = db.latest_ingest_summary(conn)
                db_state["company_count"] = db.company_count(conn)
        except Exception as e:
            db_state["error"] = str(e)
            db_state["company_count"] = 0
    else:
        db_state["company_count"] = 0

    return {
        "markets_dataset": {
            "folder": str(MARKETS_DATASET_DIR),
            "files": markets_files,
        },
        "knowledge_base_damodaran": {
            "folder": str(DAMODARAN_DIR),
            "files": damodaran_files,
        },
        "industry_lookup": {
            "folder": str(INDUSTRY_LOOKUP_DIR),
            "files": lookup_files,
        },
        "database": db_state,
        "last_ingest": last_ingest,
    }


# ---------------------------------------------------------------------------
# Upload endpoints
# ---------------------------------------------------------------------------

def _atomic_write(target: Path, upload: UploadFile) -> int:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    bytes_written = 0
    with tmp.open("wb") as out:
        while True:
            chunk = upload.file.read(1 << 20)  # 1 MB
            if not chunk:
                break
            bytes_written += len(chunk)
            if bytes_written > MAX_UPLOAD_BYTES:
                tmp.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"Upload exceeds {MAX_UPLOAD_BYTES // 1_000_000} MB limit",
                )
            out.write(chunk)
    tmp.replace(target)
    return bytes_written


@router.post("/upload/markets-dataset")
def upload_markets_dataset(
    file: Annotated[UploadFile, File()],
    x_admin_token: Annotated[str | None, Header()] = None,
) -> dict:
    """Upload a single ginzu_cc_*.xls file. Validates filename, saves atomically.
    Does NOT auto-ingest — the client should call /refresh-database once all
    files for the batch have been uploaded."""
    require_admin(x_admin_token)

    # Save the uploaded file with its original name (minus any path
    # traversal). Critically — DO NOT strip a trailing " (K)" suffix for
    # markets-dataset uploads: the team's current convention treats
    # "(1)", "(2)", "(3)" as meaningful page numbers inside one batch
    # (e.g. all_major_exchange_1.xls, all_major_exchange_1 (1).xls,
    # all_major_exchange_1 (2).xls — all DIFFERENT pages). Stripping the
    # suffix would collapse four pages onto one filename and silently
    # overwrite them. The ingester's _group_files() groups by the
    # leading integer regardless of suffix.
    name = Path(file.filename or "").name
    if not ALLOWED_MARKETS_PATTERN.match(name):
        raise HTTPException(
            status_code=400,
            detail=(
                "Filename must end with a screener group id — e.g. "
                "'ginzu_cc_1_1.xls' (legacy) or 'all_major_exchange_1.xls', "
                "'all_major_exchange_1 (1).xls' (current). "
                f"Got {name!r}."
            ),
        )
    target = MARKETS_DATASET_DIR / name
    bytes_written = _atomic_write(target, file)
    return {
        "saved": str(target),
        "filename": name,
        "size_bytes": bytes_written,
        "next_step": "Call POST /api/admin/refresh-database to rebuild the SQLite from all current files.",
    }


def _sanitize_filename(raw: str, require_ext: set[str]) -> str:
    """Clean up a user-supplied filename so it's safe to write and matches
    the well-known Damodaran / industry-lookup shape.

    Steps (conservative — only transforms the filename, never the bytes):
      1. Strip any path components (guards against path traversal).
      2. Remove trailing "(1)", "(2)", etc. that browsers add on re-download.
      3. Require the extension is one of the expected ones.
      4. Replace any characters outside [A-Za-z0-9 ._-()'] with '_'.

    Raises HTTPException(400) when the extension isn't accepted.
    """
    name = Path(raw or "").name  # strip any /... path parts
    name = _DOWNLOAD_SUFFIX.sub('', name)
    # Require a known extension
    ext = Path(name).suffix.lower().lstrip('.')
    if ext not in require_ext:
        raise HTTPException(
            status_code=400,
            detail=f"File must have extension {sorted(require_ext)}; got {name!r}",
        )
    # Sanitize remaining characters
    safe = _UNSAFE_FILENAME_CHARS.sub('_', name)
    if not safe or safe.startswith('.'):
        raise HTTPException(status_code=400, detail=f"Invalid filename {raw!r}")
    return safe


@router.post("/upload/damodaran")
def upload_damodaran(
    file: Annotated[UploadFile, File()],
    x_admin_token: Annotated[str | None, Header()] = None,
) -> dict:
    """Upload any Damodaran .xls file (betaGlobal.xls, capex.xls, etc.).
    The filename determines which slot it occupies."""
    require_admin(x_admin_token)

    name = _sanitize_filename(file.filename or "", require_ext={"xls", "xlsx"})
    target = DAMODARAN_DIR / name
    bytes_written = _atomic_write(target, file)
    return {
        "saved": str(target),
        "filename": name,
        "size_bytes": bytes_written,
        "next_step": "Call POST /api/admin/refresh-knowledge-base to reload DamodaranStore.",
    }


@router.post("/upload/industry-lookup")
def upload_industry_lookup(
    file: Annotated[UploadFile, File()],
    x_admin_token: Annotated[str | None, Header()] = None,
) -> dict:
    """Upload the ticker→industry indname.xlsx."""
    require_admin(x_admin_token)

    name = Path(file.filename or "").name
    if name not in ALLOWED_INDUSTRY_LOOKUP_NAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Expected one of {sorted(ALLOWED_INDUSTRY_LOOKUP_NAMES)}; got {name!r}",
        )
    target = INDUSTRY_LOOKUP_DIR / name
    bytes_written = _atomic_write(target, file)
    return {
        "saved": str(target),
        "filename": name,
        "size_bytes": bytes_written,
        "next_step": "Call POST /api/admin/refresh-knowledge-base to reload IndustryMapper.",
    }


# ---------------------------------------------------------------------------
# Clear endpoints — wipe files in a section before uploading a fresh batch
# ---------------------------------------------------------------------------

_SECTION_DIRS: dict[str, Path] = {
    "markets-dataset": MARKETS_DATASET_DIR,
    "damodaran": DAMODARAN_DIR,
    "industry-lookup": INDUSTRY_LOOKUP_DIR,
}


def _resolve_section_file(section: str, filename: str) -> Path:
    """Resolve `section` + `filename` to an absolute path inside the intended
    section folder. Rejects any filename that would escape the folder (path
    traversal, absolute paths, `..` parts)."""
    if section not in _SECTION_DIRS:
        raise HTTPException(status_code=400, detail=f"Unknown section {section!r}")
    base = _SECTION_DIRS[section].resolve()
    # Strip any path components the client might have smuggled in.
    safe_name = Path(filename).name
    if not safe_name or safe_name in ('.', '..'):
        raise HTTPException(status_code=400, detail=f"Invalid filename {filename!r}")
    target = (base / safe_name).resolve()
    # Ensure the resolved path is still under the section folder.
    if base not in target.parents and target != base:
        raise HTTPException(status_code=400, detail="Path traversal rejected")
    return target


@router.post("/clear/{section}")
def clear_section(section: str, x_admin_token: Annotated[str | None, Header()] = None) -> dict:
    """Delete every file in the given section folder (markets-dataset,
    damodaran, or industry-lookup). Call BEFORE uploading a fresh batch so
    the next refresh doesn't accidentally union new files with stale ones.
    Does not touch the SQLite DB — a Rebuild is still needed afterwards."""
    require_admin(x_admin_token)
    if section not in _SECTION_DIRS:
        raise HTTPException(status_code=400, detail=f"Unknown section {section!r}")
    folder = _SECTION_DIRS[section]
    removed: list[str] = []
    if folder.exists():
        for f in sorted(folder.iterdir()):
            if f.is_file():
                f.unlink()
                removed.append(f.name)
    return {
        "status": "ok",
        "section": section,
        "removed": removed,
        "count": len(removed),
        "next_step": f"Drop a fresh batch into the {section} zone, then click Rebuild.",
    }


@router.delete("/file/{section}/{filename:path}")
def delete_section_file(
    section: str,
    filename: str,
    x_admin_token: Annotated[str | None, Header()] = None,
) -> dict:
    """Delete a single file by name from a section folder. Path-traversal
    safe — only files directly under the section folder can be removed."""
    require_admin(x_admin_token)
    target = _resolve_section_file(section, filename)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {target.name}")
    if not target.is_file():
        raise HTTPException(status_code=400, detail=f"Not a regular file: {target.name}")
    target.unlink()
    return {
        "status": "ok",
        "section": section,
        "removed": target.name,
        "next_step": "Click Rebuild to regenerate the database.",
    }


# ---------------------------------------------------------------------------
# Refresh endpoints
# ---------------------------------------------------------------------------

@router.post("/refresh-database")
def refresh_database(x_admin_token: Annotated[str | None, Header()] = None) -> dict:
    """Rebuild the local admin SQLite from current ginzu_cc_*.xls files,
    then regenerate the scrubbed public seed database.

    Two-step atomic refresh:
      1. ingest()         → backend/data_sources/us_cn_hk.sqlite (admin DB,
                            gitignored, includes ingest_log)
      2. build_seed()     → backend/data/valuation_seed.sqlite   (shipped
                            seed — dropped ingest_log, neutral metadata)

    After this endpoint returns, the operator's next step is a single
    git command: `git add backend/data/valuation_seed.sqlite && git
    commit -m "data: refresh seed" && git push`. The UI shows this hint.
    """
    require_admin(x_admin_token)

    from tools.ingest_us_cn_hk_dataset import ingest
    from tools.build_seed_database import build_seed

    try:
        ingest_report = ingest(MARKETS_DATASET_DIR)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}")

    # Rebuild the public seed so the shipped database stays in sync.
    seed_report: dict | None = None
    seed_error: str | None = None
    try:
        seed_report = build_seed()
    except Exception as e:
        seed_error = str(e)

    return {
        "ingest": ingest_report,
        "seed": seed_report,
        "seed_error": seed_error,
        "publish_hint": (
            "To publish the rebuilt seed to the public repo, run: "
            "cd <repo> && git add backend/data/valuation_seed.sqlite && "
            "git commit -m 'data: refresh seed' && git push"
        ),
    }


@router.post("/refresh-knowledge-base")
def refresh_knowledge_base(x_admin_token: Annotated[str | None, Header()] = None) -> dict:
    """Reload the DamodaranStore and IndustryMapper singletons from disk."""
    require_admin(x_admin_token)

    from api import routes as routes_module
    warnings: list[str] = []
    try:
        # Clear the cached singletons — the next /api/valuation/... call will rebuild.
        if hasattr(routes_module, "_DAM_STORE"):
            routes_module._DAM_STORE = None
        if hasattr(routes_module, "_IND_MAPPER"):
            routes_module._IND_MAPPER = None

        # Rebuild eagerly so the caller sees any load errors immediately.
        store = routes_module._get_damodaran_store()
        mapper = routes_module._get_industry_mapper()

        # Small sanity probes
        n_industries = len(store.list_industries("US") or []) if store else 0
        sample_ticker = mapper.lookup("AAPL") if mapper else None
    except Exception as e:
        warnings.append(str(e))
        return {"status": "error", "warnings": warnings}

    return {
        "status": "ok",
        "damodaran_industries_us": n_industries,
        "industry_mapper_probe_aapl": bool(sample_ticker),
        "refreshed_at": datetime.utcnow().isoformat() + "Z",
        "warnings": warnings,
    }


@router.post("/refresh-all")
def refresh_all(x_admin_token: Annotated[str | None, Header()] = None) -> dict:
    """Refresh everything (markets DB + knowledge base)."""
    require_admin(x_admin_token)
    db_report = refresh_database(x_admin_token)
    kb_report = refresh_knowledge_base(x_admin_token)
    return {"database": db_report, "knowledge_base": kb_report}
