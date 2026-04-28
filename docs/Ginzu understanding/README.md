# Ginzu Understanding — Module Library

**Purpose.** For every compute module of the Damodaran Ginzu (`fcffsimpleginzu`) valuation workbook, this folder contains a single Markdown file capturing Claude's authoritative understanding of:

1. The specific algorithm / formulas
2. Assessment of whether the backend logic matches Ginzu
3. The underlying **reasoning** — why Ginzu performs calculations this way (financial intuition, not just arithmetic)
4. Data flow between inputs, intermediates, and outputs
5. Cross-sheet relationships — what feeds this module, what consumes its outputs

**Why this folder exists.** Without an explicit understanding step, any verification of backend/frontend is unverifiable. These documents are the ground truth against which all code is judged. They supersede earlier stage-findings scratch files and are the canonical reference going forward.

**Authority.** Ginzu spec = `knowledge_base/Ginzu_NVIDIA.xlsx`. Extracted formulas live in `docs/brainstorm_cache/ginzu_extracted.json`. These docs are Claude's structured interpretation of that extracted corpus, not a new derivation.

**Update convention.** Each file is written in one pass during the module's 6-step investigation. If Ginzu understanding is later corrected (by user feedback or new finding), the file is updated and a "Revision log" section at the bottom records the change.

---

## Module index

| # | Module | File | Status |
|---|---|---|---|
| 01 | LTM Normalization (Trailing 12 Months) | [module_01_ltm.md](module_01_ltm.md) | ✅ Drafted |
| 02 | R&D Capitalization | [module_02_rd_capitalization.md](module_02_rd_capitalization.md) | ✅ Drafted |
| 03 | Operating Lease Capitalization | module_03_operating_leases.md | ⏳ Pending |
| 04 | Cost of Capital (WACC) — 4 approaches | module_04_cost_of_capital.md | ⏳ Pending |
| 05 | Synthetic Rating → Kd | module_05_synthetic_rating.md | ⏳ Pending |
| 06 | 10-Year DCF Projection | module_06_dcf_projection.md | ⏳ Pending |
| 07 | Terminal Value | module_07_terminal_value.md | ⏳ Pending |
| 08 | Discounting to Present Value | module_08_pv_discount.md | ⏳ Pending |
| 09 | Failure Probability Overlay | module_09_failure.md | ⏳ Pending |
| 10 | Equity Bridge | module_10_equity_bridge.md | ⏳ Pending |
| 11 | Options Dilution (Iterative BSM) | module_11_options.md | ⏳ Pending |
| 12 | Per-Share + Market Verdict | module_12_per_share.md | ⏳ Pending |

---

## Document template (applied to every module file)

```
# Module NN — [Name]

## 1. Ginzu sheet and overview
- Sheet(s) involved
- Total formulas
- Role in the valuation

## 2. Inputs (classified by source)
- FACT (fetched from CIQ or derived)
- JUDGMENT (analyst narrative)
- METHODOLOGY CHOICE (selector)
- CONSTANT (Damodaran reference)

## 3. Outputs and downstream consumers
- What this module produces
- What sheets/modules read its outputs

## 4. Algorithm — formulas in variable form
- Every compute formula, with Ginzu cell reference
- Intermediate computations (row/col breakdown)
- Aggregates

## 5. Reasoning — the financial intuition
- Why each step exists
- What problem it solves
- What happens if we skip it

## 6. Data flow diagram
- Within the sheet
- Cross-sheet

## 7. Edge cases and quirks
- Specific Ginzu behaviors not obvious from the formula
- Any known Ginzu bugs or design quirks

## 8. Current backend/frontend assessment
- Does our implementation match?
- What gaps exist?

## 9. Revision log
- Updates over time
```

All modules follow this identical 9-section structure for consistency.
