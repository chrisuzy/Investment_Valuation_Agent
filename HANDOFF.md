# Project Handoff — AD_CC_pilot

**Read this first if you are a fresh Claude Code instance on the Linux server.**

You are continuing work on a Damodaran-style equity valuation application. This document tells you exactly where things stand and what to do next.

---

## 1. Project State Summary (as of 2026-04-19)

This is a full-stack Python/React application that automates Aswath Damodaran's intrinsic equity valuation methodology. Users enter a ticker, the system fetches data from Capital IQ + Damodaran datasets, runs a 6-module computation pipeline, and presents the valuation with every intermediate step inspectable.

**Tech stack:**
- Backend: FastAPI + Python 3.11+ + Pydantic v2 + openpyxl
- Frontend: React + TypeScript + Vite + Tailwind CSS
- Engine: pure Python, zero web framework coupling
- Data: Capital IQ Excel plugin + 244 Damodaran Excel files (8 regions)
- Tests: 65 backend tests passing as of last session

**Servers:**
- Backend: `localhost:8000`
- Frontend: `localhost:5173`

---

## 2. Key Documents — Read These in Order

All documents live under `docs/`:

1. **`docs/valuation_framework_textbook.md`** (~38 KB, 17 sections)
   The canonical specification. The 10-stage valuation method, written textbook-style, generic for any publicly traded company. Every formula, every variable name, every input source. **Read this first.**

2. **`docs/atom_level_audit.md`** (~25 KB)
   Line-by-line comparison of the current codebase against the textbook. Shows every data dictionary field with status (populated / read / dead), every engine module line that is wrong, every missing CIQ field, every missing Damodaran dataset. **Read second.**

3. **`docs/current_state_audit.md`** (~15 KB)
   Stage-by-stage scoring (✅ / ⚠️ / ❌ / 🔴) of what is complete vs. half-built vs. wrong. Higher-level than the atom audit. Good for quick navigation.

4. **`docs/project_plan_next_steps.md`** (~12 KB)
   The 7-phase roadmap. Each phase has estimated effort and dependencies. Use this as your sequence guide.

5. **`docs/brainstorm_cache/methods_in_details.md`**
   The detailed mapping of Ginzu NVIDIA workbook formulas to PRD variables. Background reading.

6. **`CLAUDE.md`** (project root)
   Operational rules. Most important: Rule 7 (never do "all remaining N things in one go"), Rule 8 (Excel export must use live formulas not static values), Rule 4 (break tasks into baby steps).

7. **`PRD.md`** (project root, in Chinese)
   Original product requirements document. The textbook document supersedes it where they conflict.

---

## 3. The Core Finding from the Audit

**17 of 27 `ValuationAssumptions` schema fields are defined in code but never read by any module.** The frontend lets the user set them, the backend stores them, the DCF engine ignores them.

This is the primary defect. Fixing it is Phase 1 of the plan.

Dead fields (all in `backend/engine/data_dictionary.py:ValuationAssumptions`):
- `operating_margin_next_year`, `revenue_growth_years_2_5`, `target_operating_margin`, `margin_convergence_year`
- `sales_to_capital_high`, `sales_to_capital_stable`
- `failure_tie_to`
- `override_reinvestment_lag`, `reinvestment_lag_years`
- `override_tax_convergence`
- `override_nol`, `nol_amount`
- `override_riskfree`, `riskfree_after_yr10`
- `override_growth_perpetuity`
- `override_trapped_cash`, `trapped_cash_amount`, `trapped_cash_tax_rate`

The primary fix is to rewrite the projection path in `backend/engine/module_4_dcf.py` so these fields are consumed.

---

## 4. What Works Today (Green Light)

- **Stage 1 (LTM normalization)**: `backend/engine/ltm_calculator.py` — correct textbook formula.
- **Stage 2a (R&D capitalization)**: `backend/engine/module_1_adjustments.py:capitalize_r_and_d()` — fully correct.
- **Stage 2b (Operating lease conversion)**: `module_1_adjustments.py:capitalize_operating_leases()` — correct with annuity method (recently fixed).
- **Stage 3 core (single-business WACC)**: `backend/engine/module_2_risk.py` — CAPM + weighted WACC correct.
- **Stage 6 (Terminal Value)**: Gordon formula with `RIR = g/ROIC` correct.
- **Stage 10 (per-share)**: correct.
- **Data Fetching**: 247+ CIQ mnemonics fetched, 10 years annual + 8 quarters. 244 Damodaran files loaded across 8 regions.

---

## 5. What is Broken (Priority Fix List)

From `docs/atom_level_audit.md` Part 12, the atom-level task list for Phase 1:

**File to modify: `backend/engine/module_4_dcf.py`**

1. Read `assumptions.operating_margin_next_year` as year-1 margin
2. Build `_margin_path(margin_y1, target, convergence_year)` helper
3. Replace `ebit_t = ebit_prev × (1+g)` with `ebit_t = rev_t × margin_t`
4. Fix growth source: use `assumptions.revenue_growth_next_year` before falling back to `cf_metrics.expected_growth_ebit`
5. Honor `assumptions.revenue_growth_years_2_5` for years 2-5
6. Build `_tax_path(effective, marginal, override_convergence)` helper
7. Thread effective tax rate through M4 from `CompanyValuationInput.effective_tax_rate_ciq`
8. Dynamic NOL carryforward
9. Sales-to-Capital reinvestment with lag (replaces `nopat_t * rir_firm`)
10. WACC path from initial to terminal over years 6-10
11. Cumulative discount factors (year-by-year product, not `1/(1+wacc)^t`)
12. Invested capital + ROIC path tracking
13. Honor `override_riskfree`, `override_growth_perpetuity` in terminal WACC/g
14. Move failure adjustment before equity bridge, honor `failure_tie_to`
15. Equity bridge: subtract `raw.minority_interests`, add `raw.cross_holdings`
16. Trapped cash adjustment
17. Fix M3: add lease depreciation to `adjusted_d_a`
18. Fix M3: pass `macro.tax_rate_marginal` directly instead of reverse-engineering
19. Comprehensive tests against Ginzu NVIDIA workbook as ground truth

Estimated ~7 hours of focused work for Phase 1.

**Follow `docs/atom_level_audit.md` Part 12 for the full implementation plan — each task is sized to one sitting.**

---

## 6. How to Start Work

1. Read the 4 key docs in section 2 above.
2. Set up environment (see section 7 below).
3. Run existing tests to verify baseline: `cd backend && pytest tests/engine/ -v`. Expect 65 passing.
4. Start with Task 1 in section 5: a 5-minute edit that reads `operating_margin_next_year`. Verify with a test. Move to Task 2.

**Operate in baby steps per CLAUDE.md Rule 4 and Rule 7: one task per response, verify each, then proceed.**

---

## 7. Environment Setup

### Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # or pip install fastapi uvicorn pydantic openpyxl pytest
uvicorn api.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev   # serves on localhost:5173
```

### Tests
```bash
cd backend
pytest tests/engine/ -v
```

Expect 65 passing.

---

## 8. User Preferences (from `CLAUDE.md` — memorize these)

- **Never announce work without doing it.** If you say "let me do X," the next tool call must be X.
- **Baby steps.** Never attempt more than one small change per response.
- **Every response ends with a tool call unless done.** Text-only responses that promise future work cause the user to lose trust.
- **Never stop without explanation.** If you can't continue, say why immediately.
- **Always restart the backend after Python edits.** `--reload` is unreliable for schema changes.
- **Never skip hooks (`--no-verify`), never force-push.** Default to safe operations.
- **The user communicates in English, values speed over exhaustive explanation.**
- **Test company is Almarai (SASE:2280)** — Saudi food company, ground truth in `knowledge_base/groud_truth/ground_truth.xlsx`. Note: "groud_truth" is a typo in the folder name — do NOT rename.
- **Also valuable test case: NVIDIA via `knowledge_base/Ginzu_NVIDIA.xlsx`** — Damodaran's actual workbook for Phase 1 ground-truth testing.

---

## 9. What NOT to Do

- Do NOT re-derive the 10-stage framework. It is already canonical in `docs/valuation_framework_textbook.md`.
- Do NOT re-audit the code. The atom-level audit already exists in `docs/atom_level_audit.md`.
- Do NOT rebuild the data fetching layer. It works.
- Do NOT create a Git repo unless asked. The project has traditionally not been git-initialized.
- Do NOT touch `PRD.md` (Chinese original). The textbook document supersedes it.
- Do NOT try to run Capital IQ COM automation on Linux. CIQ only works on Windows with Excel. On Linux, upload a pre-resolved CIQ template via the frontend.

---

## 10. Quick Status Line

You are on the Linux server. The project has a correct data layer, correct adjustment layer, correct terminal value, and correct per-share math. The DCF projection (`module_4_dcf.py`) ignores most user inputs. Phase 1 of the plan fixes this. Read the docs, run the tests, start with Task 1.

Build from here.
