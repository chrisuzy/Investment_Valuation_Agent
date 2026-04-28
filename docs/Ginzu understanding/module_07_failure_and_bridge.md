# Module 07 — Failure Probability Overlay + Equity Bridge

**Ginzu source:** `knowledge_base/Ginzu_NVIDIA.xlsx`, `Valuation output` rows 40–52. Plus `Failure Rate worksheet` as a reference-data helper for picking the failure probability input.

---

## 1. What this module is trying to do

Two output-layer operations bundled together because Ginzu does them sequentially on the same block of cells and they must happen in that specific order.

**Failure overlay:** the DCF assumes the firm continues as a going concern forever. For mature blue-chips this is fine; for distressed firms, startups, or firms with credible survival risk it's naive. The failure overlay adjusts the going-concern value by blending it with a distress-scenario value weighted by the probability of failure. Even a small failure probability can shave a meaningful amount off a leveraged or weak firm's valuation.

**Equity bridge:** translates firm value (value of operating assets) into the value of common equity. The firm belongs to multiple capital providers — debt holders, preferred holders, minority interest holders in subsidiaries — and owns non-operating assets (cash, cross-holdings in other firms). Common equity is what's left after all of that is sorted out.

The bridge must use POST-failure-overlay firm value as its starting point, not going-concern value, because the debt and minority claimants face the same failure risk we just accounted for.

---

## 2. The financial intuition

### Why the overlay is an expected-value blend

Two possible futures for the firm: survives (with probability 1 − p, worth the going-concern value) or fails (with probability p, worth the distress recovery). Expected value:

```
V_operating_assets = V_going_concern × (1 − p) + V_distress × p
```

The analyst specifies what distress is tied to:
- **V (fair value)** — distress value = going-concern × recovery rate (typical 30–70%). Used for firms whose distressed assets would be sold as going-concern pieces.
- **B (book value)** — distress value = (book equity + book debt) × recovery rate. Used for firms where liquidation values would track book rather than operating value.

Recovery rate defaults to 50% but is analyst-adjustable.

### Why failure adjustment precedes the equity bridge

When a firm fails, debt holders are still debt holders. Minority interest holders are still minority interest holders. The claim hierarchy doesn't disappear in distress. So the failure-weighted expected firm value is the correct starting point for the equity bridge — we're asking "what are the operating assets worth today, accounting for possible failure?" and then we subtract the non-equity claims.

Applying failure AFTER the bridge (to the equity value directly) would double-count. The debt would be subtracted at full face value, then the remaining equity would be discounted again for failure — but in failure, the debt is also at risk; both sides feel the distress.

### The bridge components and their direction

```
Value of operating assets                  (starting point, post-failure-overlay)
− Debt                                      (creditors' first claim)
− Minority interests                        (non-controlling claims in subsidiaries)
+ Cash and marketable securities            (non-operating asset — adjusted for trapped cash)
+ Cross holdings                            (stakes in other firms, non-operating)
= Value of equity (pre-options)
```

Each addition and subtraction has a clean economic meaning:
- **Debt** is subtracted because creditors have first claim on the firm's cash flows. Equity gets only what's left after debt is serviced.
- **Minority interests** are subtracted because if the firm consolidates a subsidiary it doesn't fully own, part of the operating value belongs to the minority partners, not the parent's common equity.
- **Cash** is added back because it's not part of the operating business (already netted out of invested capital on the way in). Equity holders own the cash alongside the operating value.
- **Cross holdings** are stakes in other firms — passive investments, not part of the firm's own operating cash flow. Added back at book or market.

### Trapped cash adjustment

If a firm holds cash overseas that's subject to repatriation tax, that cash isn't worth face value to the equity holders. The adjustment:

```
Usable cash = Total cash − Trapped amount × (Marginal_tax − Foreign_tax_paid)
```

Only the incremental tax that would be owed on repatriation is subtracted. If the firm already paid 15% foreign tax and the marginal rate is 25%, the haircut is 10 percentage points on the trapped amount.

---

## 3. The algorithm — in financial terms

### 3.1 Failure probability

```
p = analyst's chosen failure probability (typically 0 for blue-chips, 5–30% for distressed)
```

The analyst picks p by consulting the Failure Rate worksheet (which provides reference tables: default probabilities by bond rating × time horizon, and age-based failure rates by industry from BLS data). The worksheet is a helper, not a computation; p is a user input.

### 3.2 Distress value

```
If failure_tie_to == "B":
    Distress_value = (Book_Value_Equity + Book_Value_Debt) × Distress_Recovery_Rate
If failure_tie_to == "V":
    Distress_value = Value_as_Going_Concern × Distress_Recovery_Rate
```

Recovery rate is analyst input (default 0.5).

### 3.3 Value of operating assets (post-failure-overlay)

```
Value_of_Operating_Assets = V_going_concern × (1 − p) + Distress_value × p
```

### 3.4 Equity bridge

```
Debt = Book Debt + (PV of operating leases from Module 3, if lease capitalization was applied)
Usable_Cash = Cash − Trapped_Cash × (Marginal_Tax − Foreign_Tax)   if trapped-cash override is set
Usable_Cash = Cash                                                  otherwise

Value_of_Equity_pre_options 
    = Value_of_Operating_Assets 
    − Debt 
    − Minority_Interests 
    + Usable_Cash 
    + Cross_Holdings
```

### 3.5 Final equity value (after options dilution)

Covered in Module 8. Preview:

```
Value_of_Equity = Value_of_Equity_pre_options − Value_of_All_Options
Value_per_Share = Value_of_Equity / Shares_Outstanding
```

---

## 4. Inputs and where they come from

**From prior modules:**
- Value as going concern (Module 6)
- PV of operating leases (Module 3)
- Book equity, book debt, cash, cross-holdings, minority interests (from LTM-rotated base year — Module 1 balance-sheet snapshots)
- Marginal tax rate (Module 4's macro)

**From user (JUDGMENT):**
- Failure probability (default 0)
- Distress proceeds percentage (default 0.5)

**From user (METHODOLOGY CHOICE):**
- Failure tie-to: "B" (book) or "V" (fair value) — default "V"
- Trapped-cash override on/off, with amount and foreign tax rate if on

---

## 5. Outputs and what consumes them

- **Value of operating assets** — the post-failure-overlay firm value. Displayed prominently; starting point for the equity bridge.
- **Value of equity (pre-options)** — intermediate output. Consumed by Module 8 (options dilution) to yield the final equity value.
- **Per-share intrinsic value (pre-options)** — computed as a reference. Final per-share comes after options.

---

## 6. Current implementation assessment

### Formula correctness

After the 2026-04-28 DCF rewrite:
- Failure overlay applied BEFORE the equity bridge (previously applied AFTER, which was wrong). ✓
- Failure tie-to "B" and "V" variants both implemented. ✓
- Expected-value blend formula correct. ✓
- Full bridge: V_op − debt − minority + cash + cross_holdings. ✓ (minority and cross were previously missing.)
- Trapped cash adjustment honors the override and uses `marginal − foreign` tax spread on the trapped portion. ✓

### Data flow

Uses LTM balance-sheet values (from Module 1's FQ-0 snapshots) rather than stale FY-0. This is the right behavior — freshest point-in-time values for debt, cash, minority, cross-holdings.

For MSFT with the rectifications applied:
- Value of operating assets: $2.75T
- − Debt (incl lease): $123B
- − Minority: $0
- + Cash (no trapped): $24.3B
- + Cross holdings: $21.2B
- = Value of equity pre-options: $2.67T

### Frontend display

Summary Sheet's "Value Rollup" block shows the full bridge: Σ PV FCFF → + PV terminal → = V_op_assets → = V_equity → per-share. With failure probability > 0, the overlay adjustment is shown as an intermediate row. Relative Valuation page shows the ratio to market price.

### Known gaps

- Failure Rate worksheet reference tables (rating-based, age-based) are NOT surfaced in the frontend. Analyst has no in-UI reference to pick the probability — just a blank input cell. Rule F violation (no reference data for a judgment input).
- Trapped cash override is exposed as a Yes/No on the Input Sheet, which is good, but there's no heuristic flag ("this firm's cash pile is largely overseas, consider the trapped-cash adjustment").

---

## 7. Revision log

| Date | Change |
|---|---|
| 2026-04-28 | Initial draft. Reflects post-rectification state (failure overlay moved pre-bridge, minority + cross + trapped cash all wired). |
