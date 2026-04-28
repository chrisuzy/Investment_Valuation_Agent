# Ginzu Reconciliation — Brainstorm Design

**Date:** 2026-04-28
**Requested by:** user (takeover of AD_CC_pilot project on Linux)
**Goal:** Produce a reconciled, variable-linked, end-to-end specification of the Damodaran intrinsic-equity-valuation methodology, using the Ginzu NVIDIA workbook as ground truth, and a revised project plan based on that spec.

---

## 1. Problem Statement

Three source-of-truth documents exist today:

| Source | What it is | Suspected issues |
|---|---|---|
| `knowledge_base/Ginzu_NVIDIA.xlsx` | Damodaran's actual workbook, 18 sheets, ~1,675 formulas | **Authoritative.** |
| `docs/valuation_framework_textbook.md` | NotebookLM-assisted markdown spec | **May contain transcription errors / simplifications.** |
| `backend/engine/module_*.py` | Current code implementation | Known to lag Ginzu in many places. |

Existing audit (`docs/atom_level_audit.md`, `docs/current_state_audit.md`) compared code to the textbook MD — so if the textbook MD is partly wrong, the audit inherits the errors. We must re-validate downward from Ginzu itself.

## 2. Non-Goals

- No code changes in this brainstorm phase. Output is pure documentation.
- Do not rebuild the data layer (CIQ fetch works).
- Do not re-derive the framework philosophically — just reconcile formulas.
- Do not decide which document wins on discrepancies — flag every divergence for user decision.

## 3. Approach

### 3.1 Extraction

Use `openpyxl` to re-open `Ginzu_NVIDIA.xlsx` fresh. For every sheet, extract:

- `(sheet, cell, raw_formula, cached_value, row_label_A_column)` tuples
- Join with column-A labels (and column-B/C label cells where applicable) to get human-readable row labels
- Normalize cross-sheet references to `'Sheet Name'!Cell` form

Write a Python script — `backend/tools/extract_ginzu_formulas.py` — that produces `docs/brainstorm_cache/ginzu_extracted.json` with this richer structure (label-annotated, not just raw cells).

### 3.2 Variable Linking

For each compute formula, substitute cell refs with the financial variable name derived from the row label. Example:

- Raw: `=B12/B11`
- Label for B12: "Operating income"; label for B11: "Sales"
- Variable form: `operating_margin = operating_income / sales`

Produce a `(variable_name, formula_in_variable_terms, defining_sheet, defining_cell)` catalog.

### 3.3 Sheet walking order (bottom-up, dependency order)

| # | Stage | Ginzu sheets | Formula count (approx) |
|---|---|---|---:|
| 1 | Inputs & LTM | `Input sheet`, `Trailing 12 month` | 46 |
| 2 | Adjustments | `R& D converter`, `Operating lease converter` | 92 |
| 3 | Cost of Capital | `Cost of capital worksheet`, `Synthetic rating`, `Country equity risk premiums` | 428 |
| 4 | DCF core | `Valuation output` | 398 |
| 5 | Failure & Options | `Failure Rate worksheet`, `Option value` | 134 |
| 6 | Derived views (skim) | `Summary Sheet`, `Diagnostics`, plus presentation sheets | ~577 (mostly pass-through) |

Critical-path formulas we actively decode: ~600–700 out of ~1,675.

### 3.4 Per-stage output

For each stage, produce three cross-references:

1. **Ginzu-truth section** — every compute formula in variable form, grouped by output variable.
2. **Textbook MD delta** — for each Ginzu formula, check `valuation_framework_textbook.md`. Flag:
   - Missing (textbook does not cover this formula)
   - Divergent (textbook claims a different formula)
   - Equivalent (textbook matches)
3. **Code gap delta** — for each Ginzu formula, check the corresponding `module_X.py` line. Flag:
   - Unimplemented
   - Wrong (different formula than Ginzu)
   - Uses dead schema field
   - Correct

## 4. Deliverables

Three markdown files at `docs/` plus one small Python tool.

| File | Action | Content |
|---|---|---|
| `backend/tools/extract_ginzu_formulas.py` | NEW | openpyxl script producing `docs/brainstorm_cache/ginzu_extracted.json` |
| `docs/brainstorm_cache/ginzu_extracted.json` | NEW (replaces `ginzu_raw.json`) | label-enriched corpus |
| `docs/ginzu_spec_v2.md` | NEW (replaces `docs/brainstorm_cache/methods_in_details.md`) | reconciled variable-linked end-to-end spec, Ginzu-authoritative |
| `docs/textbook_corrections.md` | NEW (sits alongside `valuation_framework_textbook.md`) | list of every MD/Ginzu discrepancy, not auto-edited |
| `docs/project_plan_v2.md` | NEW (replaces `docs/project_plan_next_steps.md`) | revised phase plan re-sequenced after reconciliation |

Files removed: `docs/brainstorm_cache/methods_in_details.md`, `docs/project_plan_next_steps.md`.
Files untouched: `docs/valuation_framework_textbook.md`, `docs/atom_level_audit.md`, `docs/current_state_audit.md` (atom audit marked "superseded; see ginzu_spec_v2.md" at the top).

## 5. Tiebreaker Policy

Per user request: **flag, do not decide**. When Ginzu and textbook MD disagree, `textbook_corrections.md` presents both sides verbatim. User picks per-item in a follow-up pass.

## 6. Session structure & checkpointing

Long session. Plan: create one TaskCreate task per stage (8 stages total: Extraction + 6 walks + Synthesis). Write stage output to `docs/brainstorm_cache/stage_N_findings.md` scratch files as I go, then synthesize into the three final deliverables at the end. This way if context runs thin we can checkpoint.

## 7. Risk register

| Risk | Mitigation |
|---|---|
| Row labels in Column A are incomplete/ambiguous for some compute cells | Fallback: use nearest label row above; for unlabeled cells, inspect dependency graph (what formulas reference this cell) to infer meaning |
| Cross-sheet references resolve to multiple possible meanings | Resolve only on the compute path; leave presentation-sheet refs un-resolved |
| Volume of formulas exhausts context | Process stage by stage with scratch-file checkpoints; synthesize from scratch files not in-memory |
| `ginzu_raw.json` and fresh openpyxl extract disagree | Trust fresh openpyxl; record discrepancies for investigation |

## 8. Success criteria

1. Every formula in `ginzu_spec_v2.md` is expressed in financial-variable terms with at most one cell reference per formula (and only when no label exists).
2. `textbook_corrections.md` has at least one entry per textbook section — either "verified matches Ginzu" or a specific discrepancy.
3. `project_plan_v2.md` phases are re-ordered so that any task invalidated by a textbook correction is updated.
4. Running the new extraction tool produces the same 18-sheet, ~1,675-formula count as `ginzu_raw.json` ± 5%.

## 9. CIQ Data Acquisition Model (locked-in for project_plan_v2)

**Hard constraint:** the user's Capital IQ credentials authenticate the Excel plugin, not a public API. There is no way to use those credentials directly from Linux. Five options were considered (template upload; Windows fetch-agent daemon; S&P API contract; alternative free sources; web scraping — ruled out immediately as ToS-violating).

**Decision: Option A now + Option B later.**

- **Phase A (immediate, zero new infra):** Pre-resolved template upload. Workflow:
  1. User enters ticker in the Linux web UI.
  2. Backend generates `<TICKER>_ciq_template.xlsx` via `generate_ciq_template.py` and returns it.
  3. User opens the template on any Windows/Mac-with-Parallels machine that has Excel + CIQ plugin, waits for formulas to resolve, saves the workbook.
  4. User drags the resolved file into the web UI.
  5. Backend parses it via `read_ciq_template.py` and feeds the engine.
  
  Plumbing already exists. No credential handling on the Linux side at all.

- **Phase B (enhancement, ~1 day of work, later phase in plan):** Windows fetch-agent daemon.
  - A tiny Python/FastAPI service runs on the user's Windows box and wraps the existing `capiq_excel_automation.py` COM driver.
  - Exposes a single endpoint: `POST /fetch {ticker} → resolved .xlsx binary`.
  - Linux backend POSTs to the Windows agent over a Tailscale / WireGuard / LAN tunnel.
  - Credentials never leave Windows; only the Linux backend needs to know the agent's URL + a bearer token.
  - Plan treats this as a Phase 8 enhancement; Option A remains a supported fallback.

This decision affects only `project_plan_v2.md` — the brainstorm walk itself (Ginzu formula extraction) is data-acquisition-agnostic.

**Out of scope for Phase B in this plan (explicit non-goals):**
- No cloud-hosted Windows VM (user keeps their existing Windows machine in the loop).
- No OAuth/SSO to S&P — the agent talks to Excel COM, which in turn uses the user's cached plugin credentials.
- No scraping of web.capitaliq.com under any circumstance.

## 10. Out of scope for this brainstorm

- Implementing the plan (separate pass after spec is approved).
- Editing the textbook markdown itself (user will decide per-item after reviewing corrections).
- Any backend code changes beyond the new Ginzu extraction tool.
- Refactoring existing audit docs.
- Building the Windows fetch-agent daemon (that work lives in Phase 8 of `project_plan_v2.md`, not this brainstorm).
