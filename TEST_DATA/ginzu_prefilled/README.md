# Pre-filled Ginzu Workbooks — Windows/Excel Instructions

Four Excel files are in this folder, one per test company:

- `MSFT_ginzu_input.xlsx` (Microsoft)
- `BABA_ginzu_input.xlsx` (Alibaba)
- `TSLA_ginzu_input.xlsx` (Tesla)
- `LENOVO_ginzu_input.xlsx` (Lenovo)

Each one is a **copy of Damodaran's Ginzu_NVIDIA.xlsx** with every input cell
already overwritten with that company's values from `TEST_DATA/TEST_<TICKER>.xlsx`.
You do NOT need to paste anything. Ginzu's formulas recompute from the values
already in the workbook.

## Per-workbook workflow (3 minutes each)

1. **Copy** `<TICKER>_ginzu_input.xlsx` to your Windows machine.
2. **Open** in Excel.
3. **Dismiss** any "repaired workbook" dialog — openpyxl stripped some data-validation
   extensions when writing, but the formulas are intact.
4. **Enable iterative calculation** (one-time per Excel install):
   `File → Options → Formulas → Enable iterative calculation` (100 iterations,
   max change 0.001). Ginzu needs this because its cost-of-capital uses circular
   references (β ↔ D/E).
5. Press **F9** (or just wait — Excel auto-recalcs on open if iteration is
   already enabled from a previous session).
6. **Verify inputs look right** — go to the `Input sheet` and check rows 10–23
   show the company's numbers. Row 4 should show the company's name.
7. **Save-As** `<TICKER>_ginzu_output.xlsx` in the same folder. (This step bakes the
   recalculated values into the file so my comparison script can read them
   without needing Excel.)

That's it per company. Repeat for all 4 files.

## What's already set for you

### Input sheet (all 4 files)

| Cell | Content | Note |
|---|---|---|
| B3  | Valuation date | From the company's CIQ period end |
| B4  | Company name | Microsoft / Alibaba / Tesla / Lenovo |
| B7  | Country | US / China / US / Hong Kong |
| B8  | Industry (US) | Damodaran match |
| B9  | Industry (Global) | same |
| B10–B19 | LTM revenue / EBIT / interest / debt / cash / cross-holdings / minority / etc. | from CIQ |
| B20–B23 | Shares / price / effective tax / marginal tax | |
| B25–B31 | Growth + margin + sales/capital assumptions | auto-derived defaults |
| B33 | Risk-free rate | 4.25% |
| B36–B40 | Options | set to 'No' (CIQ has no employee-options data) |
| **B42–B52** | **AI/Auto story drivers (NVIDIA-specific)** | **ZEROED OUT** so they don't contaminate the valuation |
| B56–B68 | Stable-period + failure + reinvestment-lag overrides | see below |
| B69–B83 | Tax / NOL / riskfree / growth / trapped-cash overrides | all set to "No" (defaults) |

### Stable-period overrides (applied to all companies)

- **B56=Yes, B57=0.085** — stable-period WACC = 8.5% after year 10
- **B59=Yes, B60=0.12** — stable-period ROIC = 12%
- **B62=No** — no failure probability
- **B67=Yes, B68=1** — reinvestment lag = 1 year

These are sensible defaults for mature, profitable firms. They match the
assumptions our backend uses in its default run, so the comparison is apples-to-apples.

### R&D converter (MSFT / BABA / TSLA / LENOVO — all have R&D)

- `B6` — amortization period N = 5
- `B7` — current-year LTM R&D
- `B11–B20` — historical R&D, years -1 through -10 (most recent first)

Ginzu's R&D converter will compute:
- Value of research asset (D35)
- Amortization this year (D37)
- Adjustment to EBIT (D39)

These feed back into the main valuation when B15 on the Input sheet = "Yes"
(which it is, for all 4 companies).

### Operating lease converter

**Untouched.** All 4 companies have `has_operating_leases = No` because post-ASC 842
lease liabilities are already captured in `bv_debt`. You can ignore the lease converter
sheet entirely — it still has NVIDIA's lease data but it's unused.

## After you've recalculated all 4

Send me (or save in this folder) the 4 recalculated files named
`<TICKER>_ginzu_output.xlsx` (one per company). When I'm back on Linux I'll run:

```bash
cd backend && source .venv/bin/activate
python tools/run_ginzu_comparison.py
```

which reads Ginzu's output cells directly from each `_output.xlsx`, runs the
same inputs through our backend's `/api/valuation`, and writes
`docs/experiments/ginzu_comparison_<TICKER>.md` with per-module tables.

## Sanity checks before you save

Before saving as `_output.xlsx`, quickly verify on the **Valuation output** sheet:

- `B52` (value per share) is a sensible positive number — single digits to low thousands
- `B53` matches the current stock price shown in `B21` on the Input sheet
- `B43` (value of operating assets) is finite, not `#REF!` or `#DIV/0!`

If any of those show errors, iteration probably didn't converge — try pressing
F9 a few more times, or increase max iterations in the Excel options dialog.
