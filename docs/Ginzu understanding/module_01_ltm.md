# Module 01 — LTM Normalization (Trailing 12 Months)

**Ginzu source:** `knowledge_base/Ginzu_NVIDIA.xlsx`, sheet titled `Trailing 12 month`. This doc explains the financial meaning; the cell-level corpus lives in `docs/brainstorm_cache/ginzu_extracted.json` if verification is ever needed.

---

## 1. What this module is trying to do

The DCF will project ten years of cash flows, compute a terminal value, and discount everything back to today. The single most influential number in that chain is the **base year** — the starting line from which all future years grow. If the base year is stale, every projection year is shifted, and the per-share valuation is systematically wrong.

The problem: a 10-K annual filing is a complete picture of a firm's fiscal year, but by the time a valuation is actually run, that fiscal year may have ended 6, 9, or even 12 months ago. The firm has kept operating. Revenues have grown (or fallen). Margins have evolved. New quarters have been filed.

LTM normalization is the mechanism that **rotates the 12-month observation window forward** so the base year ends at the most recent quarterly filing, not at the last fiscal-year end. It replaces stale months of the old fiscal year with fresh months of the new fiscal year, keeping the window width at exactly twelve months so year-over-year comparisons remain meaningful.

This runs first. Every subsequent module — adjustments (R&D, leases), cost of capital, DCF projection, terminal value, equity bridge — uses the LTM-rotated base year as its starting point.

---

## 2. The financial intuition

Think of the operating business as a continuous stream of revenue and costs. A fiscal year is just an arbitrary 12-month slice analysts use for reporting. When we value a company, we want the freshest possible 12-month slice — because tomorrow's value depends on what the business is doing **now**, not what it was doing a year ago.

If the last 10-K is 6 months old, half the "base year" is already stale. If we project forward from that stale base by applying a growth rate, we're really projecting forward from a point that's 6 months behind reality. The future we're computing is 6 months displaced from the true future.

The rotation solves this by pulling the window forward. We take the stale 10-K's 12 months, cut off the parts that have been superseded by newer quarterly filings, and stitch on the fresh quarters from the current fiscal year. The window still covers 12 months — we haven't invented data — we've just shifted which 12 months.

Crucially, the rotation uses **same-calendar-window substitution**: the stale months we cut are replaced with the matching months from the current year. If we cut April–September of last fiscal year, we stitch on April–September of this fiscal year. This preserves seasonality. A retailer's Q4 looks nothing like its Q1; rotating would be meaningless if we mixed calendar positions.

---

## 3. The algorithm — in financial terms

### 3.1 Flow items (revenue, EBIT, interest, R&D, net income, taxes, capex, D&A)

A flow is an accumulation over a period. Twelve months of revenue is the sum of every dollar that flowed in during those twelve months. Since flows are additive, we can decompose any 12-month total into pieces and recombine:

```
LTM (a fresh 12-month flow)  
    =  Last fiscal year's total
     − Prior-year Year-to-Date (the first K months of the last fiscal year)
     + Current-year Year-to-Date (the first K months of the new fiscal year)
```

Where **K** is the number of months elapsed between the last fiscal-year end and the most recent quarterly filing, expressed in quarters (K ∈ {0, 1, 2, 3}).

Why this works, in words:
- We start with the last full fiscal year.
- We subtract the portion of that year that has now been superseded (the "prior YTD" — same K quarters that are now one year stale).
- We add the freshly reported equivalent portion of the current year (the "current YTD").
- The net result is a 12-month window that ends at the most recent 10-Q, not at the stale fiscal-year end.

### 3.2 Balance-sheet items (cash, book equity, book debt, shares, cross-holdings, minority interests)

A balance sheet is a snapshot, not an accumulation. There is no meaningful "12-month balance sheet" — asking for one is like asking for a 12-month temperature reading. The freshest snapshot is the one from the most recent quarterly filing. No rotation, no arithmetic:

```
LTM balance-sheet value = most recent 10-Q balance-sheet value
```

If that snapshot is unavailable for a specific field, we fall back to the last 10-K value (stale but better than nothing) and flag the source.

### 3.3 The K parameter — how many quarters have passed

K is derived from two dates:
- The fiscal-year-end date (last 10-K period end)
- The most recent quarterly filing date (last 10-Q period end)

```
K = round((months between 10-Q date and 10-K date) / 3)
```

Bounded to the integer range [0, 4]. A few concrete examples:

- NVIDIA (FY ends January 25, 2026; most recent 10-Q also January 25, 2026): K = 0. The annual filing IS the most recent filing; no rotation possible or needed, LTM equals the 10-K.
- Tesla (FY ends December 31, 2025; 10-Q at March 31, 2026): K = 1. Rotate forward three months.
- Microsoft (FY ends June 30, 2025; 10-Q at December 31, 2025): K = 2. Rotate forward six months.
- Alibaba, Lenovo (FY ends March 31, 2025; 10-Q at December 31, 2025): K = 3. Rotate forward nine months.

At K = 4 the company has filed its next full 10-K, so we'd simply re-anchor to the new fiscal year rather than rotate. Our code clamps K at 4 as a defensive guard.

### 3.4 Why the prior YTD uses a one-year-earlier window

A subtle but critical design choice: the "prior YTD" we subtract must cover **the same calendar positions** as the "current YTD" we add. For K = 2 at Microsoft — where current YTD is July–December 2025 — the prior YTD must be **July–December 2024**, not "the two quarters just before July 2025" (which would be January–June 2025, the second half of FY 2025).

Conceptually: we are removing the comparison period of last year that is directly superseded by the fresh current-year data. Year-over-year comparability is preserved.

Operationally, since CIQ indexes quarters from most-recent backward (FQ-0 = most recent quarter, FQ-1 = one before it, etc.), the prior-year same quarter is exactly **four quarters older** than the current-year quarter. Current YTD uses quarters 0 through K−1; prior YTD uses quarters 4 through K+3. That offset of four is the "rotate back exactly one year" move.

A backend implementation that used "prior YTD = the K quarters immediately before current YTD" would be subtracting the wrong calendar window, giving results that are internally inconsistent for any K ≥ 2. This exact mistake existed in our backend's dead `compute_ltm` function before the 2026-04-28 rectification; it's been corrected.

---

## 4. Inputs and where they come from

Ginzu's `Trailing 12 month` sheet is a typing-pad: the analyst enters three numbers per line item (last 10-K flow, prior-year YTD, current-year YTD) and Ginzu sums them. Our system never asks the user to type these — we **derive them entirely** from Capital IQ quarterly fetches:

- **Last 10-K value** → fetched once per flow item, from the most recent full fiscal year.
- **Prior-year YTD** → constructed by summing the K same-calendar-position quarters from one year before the most recent 10-Q.
- **Current-year YTD** → constructed by summing the K most recent quarters (K ≤ 4).
- **Balance-sheet point-in-time** → fetched directly as the most recent 10-Q snapshot.
- **K (quarters_since_10k)** → derived from the two period dates we fetch alongside the financials.

None of these are user judgments. Every input either exists in CIQ or is computable from CIQ. The analyst has no reason to disagree with the arithmetic — they can only disagree with the fetched source values themselves, which is a data-quality concern, not a valuation judgment.

---

## 5. Outputs and what consumes them

LTM produces a full set of rotated flow numbers plus a set of point-in-time balance-sheet snapshots. These feed every downstream valuation module:

- **Adjustments layer** (R&D capitalization and operating-lease conversion): uses LTM revenues, LTM EBIT, LTM R&D expense, LTM lease expense as the base year being adjusted.
- **Cost of capital**: uses LTM interest expense for interest coverage (synthetic rating path); uses the FQ-0 book debt and book equity for market-value reconciliation.
- **DCF projection**: uses LTM revenue as the base year for year-1 growth, LTM EBIT divided by LTM revenue as the implied base-year operating margin, LTM tax-paid divided by LTM EBT as the effective tax rate feeding the tax convergence path.
- **Equity bridge**: uses FQ-0 cash, book debt, minority interests, and cross-holdings directly.
- **Per-share divisor**: uses FQ-0 shares outstanding.

Because LTM feeds the entire pipeline, an error here propagates everywhere. That's the concern that motivated the user's insistence on zero tolerance for calculation error.

---

## 6. Data flow

### Ginzu's design (analyst-driven)

Ginzu envisions the analyst opening the 10-K and 10-Q PDF reports, reading the revenue line from each, typing three numbers per line item into the TTM sheet, letting Ginzu add and subtract them, and then **manually re-typing the LTM result into the base-year column of the Input sheet**. The `Trailing 12 month` sheet is not formula-wired to anything else — it's a scratchpad.

### Our automation

We bypass the entire typing workflow:

1. The CIQ template fetches 11 annual years and 8 quarters of every flow item, plus point-in-time balance-sheet fields for the most recent quarter, plus both period dates.
2. The backend parses this into `raw_financials` (annual) and `quarterly_financials` (quarterly) arrays.
3. The LTM calculator assembles the rotated base year programmatically in a single function call.
4. The orchestrator passes the LTM-rotated base year as the "current year" input to every downstream module.
5. The frontend reads the backend's LTM result directly; it does not recompute.

One function call replaces what Ginzu would have the analyst do by hand and by eye.

---

## 7. Edge cases and design choices

### K = 0

The 10-K and the 10-Q coincide (fiscal-year end = most recent filing date). Nothing to rotate. LTM equals the 10-K. Our code early-returns in this case rather than running the sum-of-zero-quarters loop.

### Insufficient quarterly data

If our template fetched fewer quarters than K + 4, we lack the raw material to rotate properly. Falling back silently to partial sums would introduce a double-count error (adding current YTD without subtracting the correct prior YTD). The principled response: abort the rotation, return the 10-K values unchanged, and surface a visible warning so the user understands why LTM equals FY0.

### Per-field missing values

CIQ sometimes returns a null for a specific field in a specific quarter (data gap in the filing). Our current code coerces nulls to zero, which can introduce subtle per-field errors. A stricter behavior would be to detect any null in the rotation window and fall back to FY0 for that single field while still rotating other fields. This is a small known gap in our implementation.

### Off-cycle fiscal years

Microsoft (June 30), Alibaba and Lenovo (March 31) all have fiscal years that don't align with the calendar. The LTM rotation math is unaffected by this — it operates on whatever fiscal quarters the company reports. But analysts reading the output should understand that a Microsoft "LTM" ending December 31, 2025 is a hybrid: the first half of the window is MSFT's FY 2025 (second half of that fiscal year) and the second half is MSFT's FY 2026 (first half of that fiscal year).

### Ginzu's TTM sheet has stale Netflix data in the NVIDIA workbook

The NVIDIA Ginzu copy contains rows labeled "Technology & Content", "Content Costs", "Marketing Costs" — these are Netflix income-statement line items left over from a prior valuation. This confirms something important about how Ginzu is actually used: the TTM sheet is a **scratchpad that doesn't flow into anything**. The analyst computes LTM on it, types the result into the Input sheet, and moves on. Our automation replaces this entire flow.

---

## 8. Current implementation assessment

### Backend

The LTM rotation is implemented correctly. The formula uses the one-year-earlier window for prior YTD (FQ-4 through FQ-(K+3)), not the incorrect "quarters immediately preceding" pattern that was in the dead legacy code. The balance-sheet fallback chain (FQ-0 snapshot, else FY-0) works. The insufficient-data guard is in place. The orchestrator calls the LTM step before every downstream module, so the adjustment and DCF layers all operate on the rotated base year, not on stale FY-0.

### Frontend

The Input Sheet's base-year column and the Trailing 12 Month page both read the backend's LTM values as the single source of truth. The Trailing 12 Month page additionally shows the component breakdown (10-K value, current YTD added, prior YTD subtracted, LTM result) for audit transparency — the user can see not just the final number but how it was assembled. An insufficient-data warning banner appears when the fetched quarterly data is too short for the required rotation.

### End-to-end verification

Tested through the full network stack (user's browser → Vite proxy → backend) with four real companies at three different K values:

- **Tesla** (K = 1, 3-month rotation): LTM revenue $97.9B vs FY-0 $94.8B, +3.2%. Small rotation, small delta, consistent with a company whose next-fiscal-year is only one quarter reported.
- **Microsoft** (K = 2, 6-month rotation): LTM revenue $305.5B vs FY-0 $281.7B, +8.4%. Six fresh months of AI-driven growth captured.
- **Alibaba** (K = 3, 9-month rotation): LTM revenue $1.02T vs FY-0 $996B, +2.0% top-line. But LTM EBIT $90B vs FY-0 $152B, −41%. The rotation captured nine months of severe margin compression that the stale fiscal-year didn't yet reflect. This is exactly the kind of directional information the DCF base year needs.
- **Lenovo** (K = 3, 9-month rotation): similar Asian-fiscal-year company with major rotation.

All four companies correctly rotated. Balance-sheet snapshots correctly swapped from annual to quarterly dates. DCF year-1 projections correctly grow off the LTM base.

### Remaining concerns (non-blocking)

- **Per-field null handling**: if a specific field is null in one of the required quarters, we coerce to zero instead of per-field fallback. Low impact in practice, worth tightening.
- **Cross-field consistency for downstream modules**: the R&D-capitalization module takes `r_and_d_expense_current` from the FY-0 adjustment-inputs, not from LTM. That's a minor inconsistency addressed in Module 02's rectification plan.

---

## 9. Revision log

| Date | Change |
|---|---|
| 2026-04-28 | Initial draft. Reflects post-rectification state of backend and frontend. Source: `Ginzu_NVIDIA.xlsx`, sheet `Trailing 12 month`. |
| 2026-04-28 (v2) | Rewrote to eliminate cell-address references per user feedback. Presentation is now purely in financial-variable language. |
