# Module 08 — Employee Options Dilution (Iterative Black-Scholes)

**Ginzu source:** `knowledge_base/Ginzu_NVIDIA.xlsx`, sheet `Option value`.

---

## 1. What this module is trying to do

A firm with employee stock options outstanding has granted claims on its future equity that are not reflected in today's share count. Those options will be exercised as the stock price rises, creating new shares and diluting the per-share value for existing equity holders. A proper DCF must subtract the value of those options from the common equity value before dividing by share count to get per-share intrinsic value.

The twist: the value of an option depends on the stock price, and the stock price (post-dilution) depends on the value of the options. This circular dependency is resolved by iteration.

This module takes the firm's equity value (post-bridge, pre-option-dilution) and produces a final per-share intrinsic value that properly accounts for the dilution effect.

---

## 2. The financial intuition

### Why options dilute equity value

An employee option with strike $50 on a stock trading at $100 effectively obligates the firm to sell a share at $50 when the holder exercises, getting only $50 of cash for a share worth $100. The $50 gap is wealth transferred from existing shareholders to the option holder. That transfer, summed across all outstanding options, is what we need to subtract.

Importantly, we care about the economic value of the option at its fair market price, not its intrinsic value (stock minus strike). Options have time value too — an at-the-money option isn't worth zero, it's worth something proportional to volatility and time to expiration. Black-Scholes prices that time value correctly.

### Why dilution-adjusted stock price

If we priced the option at the current market stock price, we'd overstate its value, because issuing new shares at exercise dilutes the stock. The "true" stock price post-exercise is lower than today's market price. Black-Scholes should be applied to the dilution-adjusted stock price, which itself depends on the option value — hence the iteration.

```
Dilution-adjusted stock price 
    = (current stock price × existing shares + call value × warrants outstanding) 
      / (existing shares + warrants outstanding)
```

The intuition: imagine all option holders exercise simultaneously. They pay in their option values (in cash-equivalent terms); those payments combine with the current market value of existing equity to form the new total firm equity value; divided by the new (diluted) share count, that's the post-exercise stock price. Black-Scholes on THAT price gives the right option value.

### Why iteration

The adjusted stock price depends on call value (via the weighted-average formula above). Call value depends on adjusted stock price (via Black-Scholes). Start with an initial guess for call value (zero works), compute adjusted price, recompute call value, recompute adjusted price… the process converges in 3–5 iterations for typical cases.

---

## 3. The algorithm — in financial terms

### 3.1 Seed the iteration

Start with call value = 0 (or any reasonable initial guess; convergence is insensitive to the seed). Seed stock price for the adjustment is the current market price (Ginzu's convention) — though there's a case to be made for using the firm's intrinsic pre-options per-share value instead (a design choice we've documented).

### 3.2 Compute dilution-adjusted stock price

```
Adjusted_S = (Stock_seed × shares_outstanding + Call_value_current × warrants_count)
             / (shares_outstanding + warrants_count)
```

Strike price is not adjusted — it's the contractual strike.

### 3.3 Black-Scholes call pricing

Using Adjusted_S, the strike K, time to expiration T (weighted-average remaining life), risk-free rate r, stock-price standard deviation σ, and dividend yield y:

```
d1 = [ ln(Adjusted_S / K) + (r − y + σ²/2) × T ] / (σ × √T)
d2 = d1 − σ × √T

Call_value = Adjusted_S × e^(−y×T) × N(d1) − K × e^(−r×T) × N(d2)
```

Where N() is the standard normal cumulative distribution function.

### 3.4 Iterate until convergence

Repeat from step 3.2 with the new call value. Stop when `|new call − old call| < ε` (tolerance like $0.01) or after a max iteration count (20 is comfortable).

### 3.5 Total option value and per-share

```
Value_of_all_options = Call_value × Warrants_count
Value_of_equity_in_common = Value_of_equity_pre_options − Value_of_all_options
Value_per_share = Value_of_equity_in_common / Shares_outstanding
```

---

## 4. Inputs and where they come from

**From CIQ (fetched):**
- Current stock price (market)
- Shares outstanding (current)
- Number of warrants / options outstanding
- Weighted-average strike price
- Weighted-average remaining life

**From CIQ or industry default:**
- Stock price standard deviation (volatility)
- Dividend yield (often zero for growth firms)

**From macro:**
- Risk-free rate

**From prior modules:**
- Value of equity pre-options (Module 7)

**User control:**
- Has-options Yes/No toggle. When off, module returns zero and per-share equals pre-options value.

No analyst judgment inputs beyond the on/off toggle — all numbers are fetched or fixed.

---

## 5. Outputs and what consumes them

- **Call value per option** — the per-option fair value, displayed.
- **Value of all options** — total dilution cost. Subtracted from pre-options equity to yield final equity.
- **Final value per share** — the definitive per-share intrinsic value displayed on the Valuation Output page and compared against market price on the Relative Valuation / Summary Sheet pages.

---

## 6. Current implementation assessment

### What works

The backend implements Black-Scholes correctly. `module_6_options.py` computes d1, d2, N(d1), N(d2), and the call value per the formula. The 18 options-specific unit tests in `test_module_6_options.py` pass.

### What's broken

**The iteration loop is not implemented.** The current code uses a one-shot calculation: it computes the call value using the pre-options intrinsic stock price (not market price, and not iterated) and calls that done. Damodaran's Ginzu spec requires the fixed-point iteration between Adjusted_S and Call_value.

Impact: for firms with a meaningful gap between market price and intrinsic pre-options price, the options are mispriced. For firms close to zero moneyness or with few options relative to shares, the impact is small.

### Rectification

Add the fixed-point iteration loop in `compute_options_and_final_value()`:
1. Initialize call_value = 0
2. Loop up to 20 times:
   a. Compute adjusted_S from current call_value estimate
   b. Compute new call_value via Black-Scholes on adjusted_S
   c. If |new − old| < 0.01, break
3. Use final call_value for total option value

Also consider: Ginzu's convention uses market price as the iteration seed. Our current code uses pre-options intrinsic. This is a design choice — default to Ginzu's behavior for consistency.

### Frontend display

The Option Value page shows the full BSM inputs and outputs, with dilution-adjusted stock price prominent. When iteration is implemented, the page should ideally show a "converged in N iterations" indicator.

---

## 7. Revision log

| Date | Change |
|---|---|
| 2026-04-28 | Initial draft. Iteration rectification pending — will apply in Module 08b task. |
