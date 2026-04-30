# Universal Currency Handling — Design

**Date:** 2026-04-30
**Scope:** Backend calculation + frontend display of currency for every monetary number in the valuation engine.

---

## Motivation

Discovered during user-review: our valuation engine conflates two currencies without declaring either.

**Problem:**
- Financial statements (revenue, EBIT, debt, cash) arrive in the **reporting currency** (e.g., USD for Lenovo).
- `IQ_MARKETCAP` and `IQ_CLOSEPRICE` arrive in the **listing currency** — whatever the exchange quotes in (HKD for Lenovo on SEHK).
- Our WACC combines `mv_equity` (listing) with `debt` (reporting) without converting.

**Impact:**
- For Lenovo (reports in USD, trades in HKD ~7.78 HKD/USD):
  - Today: mv_equity = 146,747 (labeled USD but actually HKD), debt = 5,733 USD, D/E = 0.039
  - Correct: mv_equity = 18,861 USD (after /7.78), D/E = 0.304 — **8× higher**
  - β_L would rise 1.363 → 1.662; WACC would rise 10.67% → ~12.08%
- For BABA (reports in CNY, trades on NYSE in USD): symmetric bug in the other direction.
- For MSFT/TSLA (both USD): no bug.

**Why it was invisible:** frontend showed bare numbers without currency suffixes. Two directly-comparable-looking figures (VPS and market price) silently lived in different currencies.

---

## Universal rule

> **All WACC / DCF / bridge math operates in `reporting_currency`.**
> **All displayed monetary values carry an explicit currency suffix.**
> **FX conversion happens exactly once, at the CIQ adapter boundary, using a rate implied from CIQ's own filing-currency-override feature.**

This is enforced by the CIQ adapter, not the orchestrator or frontend.

---

## Data flow

```
CIQ template (Excel, user-populated)
  │
  │ Fetches TWO copies of price + market cap:
  │   stock_price_listing    (default — listing currency)
  │   stock_price_reporting  (currency override → <FILING>)
  │   mv_equity_listing      (default)
  │   mv_equity_reporting    (<FILING>)
  ▼
read_ciq_template.py
  │ Reads both pairs into the dict.
  ▼
capiq_adapter.py
  │ Derives fx_rate = stock_price_reporting / stock_price_listing.
  │ Validates against mv_equity_reporting / mv_equity_listing (sanity check).
  │ Records fx_rate_source = "CIQ implied".
  ▼
CompanyValuationInput (Pydantic)
  │ raw_financials[0].stock_price    = listing  (for display)
  │ raw_financials[0].mv_equity      = reporting (math payload)
  │ NEW raw_financials[0].stock_price_reporting = reporting
  │ NEW raw_financials[0].mv_equity_listing     = listing
  │ NEW top-level: fx_rate, fx_rate_source, fx_rate_date
  ▼
orchestrator.py / module_2_risk.py
  │ Always uses mv_equity (= reporting). No additional conversion.
  ▼
Backend response (ValuationResponse)
  │ final.value_per_share is in reporting currency.
  │ fx_rate + both stock_price variants surfaced for frontend display.
  ▼
Frontend
  │ Shows currency suffix on every number.
  │ Side-by-side conversion on cross-currency comparison rows.
  │ Currency banner at top of every page.
```

---

## CIQ template changes

Add two rows to `CIQ_Fetch_Template.xlsx` → `CIQ_Data` sheet:

| Label | Formula | Resolved variable |
|---|---|---|
| `Stock price (reporting ccy)` | `=CIQ(ticker, "IQ_CLOSEPRICE", "", "", "<FILING>")` | `stock_price_reporting` |
| `Market cap (reporting ccy)`  | `=CIQ(ticker, "IQ_MARKETCAP",  "", "", "<FILING>")` | `mv_equity_reporting` |

The 5th argument to `=CIQ(...)` is the currency override. `<FILING>` resolves to the filing currency automatically. (Existing rows without override return listing currency.)

**Verification on re-download:**
- Lenovo: `stock_price_listing = 11.83 HKD`, `stock_price_reporting ≈ 1.52 USD`, implied FX ≈ 0.1286 USD/HKD (or 7.78 HKD/USD).
- BABA: `stock_price_listing = 132.52 USD` (NYSE ADR), `stock_price_reporting ≈ 963 CNY`, implied FX ≈ 7.27 CNY/USD.
- MSFT/TSLA: both values identical → FX = 1.0.

---

## Schema changes

### `RawFinancials` (data_dictionary.py)

```python
class RawFinancials(BaseModel):
    # existing fields...
    stock_price: float | None         # listing currency  (display + UI)
    mv_equity: float | None           # reporting currency (math payload)

    # NEW
    stock_price_reporting: float | None = None   # price converted to reporting ccy
    mv_equity_listing:      float | None = None  # market cap in listing ccy (raw CIQ)
```

**Semantic convention:** `stock_price` remains the listing-currency price (unchanged) for display continuity. `mv_equity` is the one that changes behavior — moving forward it is **always reporting currency** so WACC math is consistent. A migration note is added in `module_2_risk.py`.

### `CompanyValuationInput`

```python
# NEW top-level fields
fx_rate: float | None = None
fx_rate_source: str = "unknown"       # "CIQ implied" | "manual" | "unknown"
fx_rate_date: str | None = None       # the balance-sheet date of the rate
```

### `FinalValuation`

```python
class FinalValuation(BaseModel):
    value_per_share: float             # reporting currency
    value_per_share_reporting_ccy: str # echo of reporting_currency for frontend
    value_per_share_in_listing: float | None = None  # convenience: VPS × fx_rate
```

---

## Exchange → currency map audit

`exchange_currency_map.py` currently covers ~70 exchanges. Audit pass:

1. Cross-check every exchange prefix CIQ has returned in our test data and production — ensure coverage.
2. Add any missing common exchanges:
   - `MICEX`, `RTS` (Russia historical)
   - `BIST` (Turkey)
   - `JSE` already covered
   - `BOVESPA` already covered
   - `ENXTAM`, `ENXTBR`, `ENXTLS` already covered
3. For unknown prefixes, log a warning at load and default to `None` (frontend shows "listing currency unknown").

No behavior change to the existing map — purely additive.

---

## Backend changes (per file)

### `backend/data_sources/capiq_formula_map.py`
Add 2 fields:
```python
CIQField("stock_price_reporting", "IQ_CLOSEPRICE", description="Stock price (reporting ccy)",
         fx_override="<FILING>"),
CIQField("mv_equity_reporting",   "IQ_MARKETCAP",  description="Market cap (reporting ccy)",
         fx_override="<FILING>"),
```

### `backend/tools/generate_ciq_template.py`
Extend formula-emit to pass the 5th currency-override argument when `fx_override` is set.

### `backend/tools/read_ciq_template.py`
Read the two new cells; no special handling — they're just additional scalar fields in the `current` dict.

### `backend/data_sources/capiq_adapter.py`
After parsing CIQ:
```python
stock_reporting = current.get("stock_price_reporting")
stock_listing   = current.get("stock_price")
if stock_reporting and stock_listing and stock_listing > 0:
    fx_rate = stock_reporting / stock_listing   # listing → reporting
else:
    fx_rate = None
```

### `backend/api/routes.py` (both fetch endpoints)
Populate `mv_equity` from `mv_equity_reporting` (reporting currency) when building `raw_financials[0]`.
Populate new `mv_equity_listing` field from raw CIQ mv_equity.
Populate new `stock_price_reporting` field.
Populate top-level `fx_rate`, `fx_rate_source`, `fx_rate_date`.

### `backend/engine/module_2_risk.py`
**No code change needed.** Already reads `raw_current.mv_equity` and uses it in WACC. Because the adapter now sets that to the reporting-currency value, the math becomes correct automatically.

Add a comment at the `mv_equity` read site documenting the invariant: "mv_equity is guaranteed to be in reporting currency; see currency handling spec."

### `backend/engine/module_4_dcf.py`
No change. All projections were already in reporting currency. VPS output was already reporting.

---

## Frontend changes

### `frontend/src/types/valuation.ts`
Mirror backend schema additions.

### New: `frontend/src/lib/currency.ts`
```typescript
export function fmtCurrency(value: number | null, ccy: string, decimals = 2): string {
  if (value == null) return "—";
  // USD → "$1,234.56 USD", HKD → "HK$1,234.56", CNY → "¥1,234.56 CNY", ...
  // Handle localized prefixes; unknown currency → plain number + ISO suffix
}

export function fmtFxBanner(from: string, to: string, rate: number, date: string): string {
  return `1 ${from} = ${rate.toFixed(4)} ${to}  (CIQ, ${date})`;
}

export function convert(value: number, fx: number): number {
  return value * fx;
}
```

### `frontend/src/components/CurrencyBanner.tsx` (new)
Renders the top-of-page banner when reporting ccy ≠ listing ccy:

```
Reporting currency: USD   |   Stock price currency: HKD
FX rate: 7.78 HKD/USD  (CIQ, 2025-06-30)
```

When both ccys match, banner collapses to: `Currency: USD`.

### `frontend/src/components/DualCurrency.tsx` (new)
Inline helper: `<DualCurrency value={2.37} reportingCcy="USD" listingCcy="HKD" fxRate={7.78} />` renders as:
```
$2.37 USD  (≈ HK$18.45)
```

Only shown when ccys differ.

### Page updates
- **Input Sheet** — existing currency display already exists; add currency suffix to Current Stock Price + Market Cap cells.
- **Valuation Output** — bridge rows that contain listing-currency items (market price) show `<DualCurrency>`.
- **Summary Sheet** — the "Value per share (ours)" and "Market price" rows get explicit currency suffixes + FX conversion.
- **Cost of Capital** — MV equity, MV debt, Total Capital — all get reporting currency suffix.
- **Relative Valuation** — same treatment.
- **Option Value** — stock price gets both currencies.
- **Trailing 12 Month** — all financial rows are reporting-ccy (no change).
- **Failure Rate / R&D / Lease / Synthetic Rating** — reporting-ccy only (no change).

`CurrencyBanner` component added to every valuation page (top).

---

## Failure modes

| Scenario | Behavior |
|---|---|
| CIQ `<FILING>` override returns `#N/A` | `fx_rate = None`, `fx_rate_source = "unavailable"`; frontend shows single currency with warning; `mv_equity` falls back to `mv_equity_listing`; WACC still computes but with amber warning |
| `reporting_currency` missing in CIQ | Frontend shows "currency unknown"; banner visible warning; valuation proceeds but comparisons suppressed |
| Exchange prefix missing from `exchange_currency_map.py` | Log warning at startup; `stock_price_currency = None`; frontend shows plain price without ccy suffix |
| FX rate wildly implausible (< 0.00001 or > 100,000) | Reject fx_rate, treat as unavailable, display raw |

---

## Verification plan

After implementation:
1. Re-upload the existing `TEST_DATA/TEST_LENOVO.xlsx` — confirm `fx_rate ≈ 7.78` HKD/USD, confirm D/E jumps from 0.039 to ~0.30, confirm WACC rises ~140 bp.
2. Re-upload `TEST_DATA/TEST_BABA.xlsx` — confirm FX in opposite direction, WACC shifts in opposite direction.
3. `TEST_MSFT.xlsx` and `TEST_TSLA.xlsx` — confirm fx_rate = 1.0, no numeric changes.
4. 83 backend tests still pass.
5. Visual: frontend shows FX banner + dual-currency renders on Lenovo / BABA pages; MSFT / TSLA banners collapse to single currency.

---

## Scope discipline — explicitly OUT

- **Historical FX for flow items.** CIQ returns all P&L and balance-sheet items already in reporting currency. We do NOT fetch historical FX rates for flows.
- **Projected FX in DCF.** Future years are assumed to retain the reporting currency. No PPP-adjusted discount.
- **Trapped cash conversion.** Ginzu's trapped-cash adjustment stays as-is; already handled in reporting currency.
- **Multi-currency convertibles / preferred stock.** Schema accepts only reporting-currency values; users must pre-convert.
- **Live FX at viewing time.** FX rate is frozen at CIQ fetch; doesn't refresh as currencies drift.

---

## Success criteria

1. **Correctness:** Lenovo D/E and WACC match a hand calculation using FX = 7.78 within 10 bps.
2. **Visibility:** No bare number on any page; every monetary value has a currency suffix.
3. **Universality:** Works for every ticker in the test set — MSFT (no conversion), Lenovo (HKD→USD), BABA (USD→CNY), TSLA (no conversion). Verified explicitly.
4. **No regressions:** 83 tests still pass; other companies' outputs unchanged when currencies match.
