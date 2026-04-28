# Git Rollback & Environment Restore

This repo was saved as a git tree on 2026-04-28 with 2 commits on `main`:

```
682b7d4 Initial snapshot: AD_CC_pilot Ginzu-style DCF valuation engine
2663e08 chore: add .gitignore
```

Working tree: 29 MB / 407 files tracked. `.venv/` and `node_modules/` are **not** tracked — they must be rebuilt after any clone or fresh boot.

---

## 1. Restore environment after boot / clone

```bash
# Backend — Python 3.12+ required
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

## 2. Run the stack

```bash
# Terminal A — backend (FastAPI on :8000)
cd backend && source .venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal B — frontend (Vite dev server on :5173 or :5174)
cd frontend
npm run dev -- --host 0.0.0.0
```

Open `http://<host>:5173/` (or `:5174/` if 5173 is taken by another process) in a browser. Upload any file from `TEST_DATA/TEST_*.xlsx` to verify.

## 3. Verify pipeline integrity

```bash
# Backend tests — expected: 83 passed, 4 skipped
cd backend && source .venv/bin/activate && pytest tests/ -q

# Quick live-API smoke check
curl -s http://localhost:8000/api/industries | head -c 80

# End-to-end for MSFT
curl -s -X POST "http://localhost:8000/api/valuation/fetch-from-file" \
  -F "file=@../TEST_DATA/TEST_MSFT.xlsx" -F "region=US" -F "risk_free_rate=0.0425" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'WACC={d[\"cost_of_capital\"][\"wacc\"]*100:.2f}%, VPS=\${d[\"final\"][\"value_per_share\"]:.2f}')"

# Expected: WACC=10.04%, VPS=$360.20
```

## 4. Rollback / inspect history

```bash
# See commits
git log --oneline

# Inspect a commit
git show <hash>

# Roll working tree back to a commit (keeps uncommitted files staged)
git reset --soft <hash>

# Hard reset — DISCARDS uncommitted changes; only use if you're sure
git reset --hard <hash>

# See what changed in a file between commits
git diff <hash1> <hash2> -- path/to/file

# Restore a single file from a past commit
git checkout <hash> -- path/to/file
```

## 5. What's in the repo

| Directory | Contents |
|---|---|
| `backend/` | FastAPI engine (M1–M6), LTM calculator, DamodaranStore, CIQ adapter, 83-test suite |
| `frontend/` | React/Vite/TS source — 15 pages including full Ginzu methodology selectors on `/wacc` |
| `knowledge_base/` | Damodaran reference data, `Ginzu_NVIDIA.xlsx` ground truth, `indname.xlsx`, industry lookup |
| `docs/Ginzu understanding/` | Per-module financial-reasoning docs (`module_01_ltm.md` … `module_09_per_share.md`, `HONEST_AUDIT.md`) |
| `TEST_DATA/` | CIQ-populated test files: MSFT, BABA, TSLA, LENOVO |
| `CLAUDE.md` | Operational rules + lessons learned |
| `PRD.md`, `HANDOFF.md`, `TRANSFER_*.md` | Product + handoff documentation |

## 6. What's excluded (via .gitignore)

- `backend/.venv/` (≈337 MB)
- `frontend/node_modules/` (≈284 MB)
- `frontend/dist/`, `.vite/` build caches
- `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- `knowledge_base/ciq_fetches/_temp_*.xlsx` (CIQ scratch — regenerate as needed)
- IDE files, OS files, `.env*`
