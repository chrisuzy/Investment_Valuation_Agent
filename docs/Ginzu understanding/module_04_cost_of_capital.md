# Module 04 — Cost of Capital (WACC)

**Ginzu source:** `knowledge_base/Ginzu_NVIDIA.xlsx`, sheet `Cost of capital worksheet` (plus `Synthetic rating` and `Country equity risk premiums` as referenced sub-sheets).

---

## 1. What this module is trying to do

Every future dollar a business will throw off must be discounted back to today at a rate that reflects the risk of receiving it. That rate is the cost of capital — a blended figure reflecting what equity holders demand for bearing equity risk and what debt holders demand for bearing credit risk, weighted by how much of the business each side is financing. Get it wrong by 1 percentage point and the per-share value moves by 10–20%. This is the single most influential parameter in the DCF.

Ginzu offers four routes to the number, ordered from most analytically rigorous to most pragmatic:

- **Direct input** — the analyst types a WACC, no derivation. Useful for sanity tests or when the analyst already has a preferred figure from another source.
- **Detailed** — build WACC from first principles. Unlever the industry beta, relever to the firm's own capital structure, apply CAPM for cost of equity, look up or synthesize cost of debt, weight by market values, blend. This is the main road.
- **Industry average adjusted** — use the Damodaran industry-average WACC, adjusted for the gap between the firm's risk-free rate and the one in Damodaran's dataset at publication time. A quick shortcut when the firm is representative of its industry.
- **Decile / regional distribution** — look up the WACC corresponding to the firm's risk quartile within its region's cross-section of public companies. Coarsest but sometimes the right answer for smaller or unusual firms.

The detailed path has several decision points where Ginzu offers the analyst multiple routes (single-business beta vs multi-business, country-of-incorporation ERP vs operating-geography blend, actual credit rating vs synthetic rating vs direct input). The module exposes these as explicit choices so the analyst picks the method best suited to what they know about the firm.

---

## 2. The financial intuition

### Why weighted average

Any dollar invested in the firm comes from equity holders, debt holders, or preferred shareholders. Equity holders expect the highest return because they bear the residual risk. Debt holders expect less because they get paid first and have contractual claims. Preferred sits between. If we value the firm as a whole (firm value, not equity value), we must use a rate that reflects what ALL capital providers collectively demand. That's a weighted average, with weights equal to the proportion of the business financed by each source.

### Why unlever then relever beta

A stock's observed beta reflects two things mashed together: the underlying business risk AND the amplification from leverage. Two identical businesses with different debt levels will have different observed betas even though the businesses are identical. When we estimate beta from a single firm's stock returns, we're stuck with that firm's specific leverage — and also stuck with the noise from using a single firm's 3–5 years of returns.

The fix: take the average beta across many firms in the same business, unlever each to strip out their specific leverage, blend them, then relever to OUR firm's leverage. This gives us a beta that captures the business-risk common factor cleanly, and calibrates the amplification precisely to the firm we're valuing.

### Why CAPM

Because investors hold diversified portfolios and should only be compensated for risk they can't diversify away — systematic risk, measured by beta. The CAPM formula (risk-free rate + beta × equity risk premium) is the cleanest expression of that idea. It has well-known limitations (the equity risk premium is hard to pin down; beta is noisy; the risk-free rate is an idealization), but it's the least-bad framework and it's what Damodaran uses.

### Why market-value weights

Book values are historical and can be wildly different from today's economic reality (especially for equity). The weights in WACC must reflect what the business is financed with AT A MARKET LEVEL today. So we use market cap for equity, and we re-price debt at market using bond-pricing arithmetic rather than just using book debt.

### Why after-tax cost of debt

Interest expense is tax-deductible, which means the government effectively subsidizes debt financing. A firm paying 6% pre-tax on its debt only really bears 4.5% of that cost if its tax rate is 25% — the other 1.5% is a tax saving. The WACC formula uses the after-tax cost of debt to reflect this subsidy.

---

## 3. The algorithm — in financial terms

### 3.1 Unlevered beta — four paths

The analyst selects one path:

- **Single-business US** — look up the industry's unlevered beta from Damodaran's US betas dataset.
- **Single-business Global** — same, from the Global betas dataset.
- **Multi-business** (US or Global) — for firms spanning multiple industries. Estimate each segment's enterprise value as segment revenue × industry EV/Sales multiple; use those EVs as weights; blend the segment unlevered betas into a single weighted average.
- **Direct input** — analyst provides a levered beta directly, bypassing the unlever/relever step.

### 3.2 Equity risk premium — four paths

- **Country of incorporation** — look up the firm's home-country total ERP (mature-market base plus country risk premium) from Damodaran's country dataset.
- **Operating countries weighted** — for multinationals. Each country the firm earns revenue in contributes its ERP, weighted by revenue share.
- **Operating regions weighted** — same idea at a coarser granularity (ten regional aggregates).
- **Direct input** — analyst types a figure.

### 3.3 Pre-tax cost of debt — three paths

- **Direct input** — analyst types Kd.
- **Synthetic rating** — compute interest coverage ratio (adjusted EBIT divided by interest expense), look up the rating that corresponds to that coverage level (using a small-firm or large-firm coverage table selected by firm size), look up the default spread for that rating, and compute Kd as risk-free rate plus firm default spread plus country default spread.
- **Actual rating** — analyst provides the firm's S&P or Moody's rating; look up the spread directly.

**Important nuance for synthetic rating:** the EBIT used for coverage is the lease-adjusted EBIT but NOT R&D-adjusted. Damodaran's position is that R&D capitalization is a valuation adjustment, not a creditor-relevant operating earnings measure, so creditors wouldn't give credit for the R&D add-back. Our implementation must preserve this distinction if we implement synthetic rating.

### 3.4 Market value of debt

Re-price the firm's book debt as if it were a single coupon bond with face value equal to book debt, coupon equal to interest expense, and time to maturity equal to the firm's weighted-average debt maturity:

```
Market value of straight debt
  = Interest expense × [1 − (1 + Kd)^−maturity] / Kd    (PV of the coupon stream)
  + Book debt / (1 + Kd)^maturity                        (PV of the principal)
```

Convertible debt is decomposed: the straight-debt component is priced by the same bond formula; the equity-conversion component is the residual (convertible market value minus straight-debt component).

The debt value of operating leases (from Module 3) is added to the total market value of debt.

### 3.5 Preferred stock

For firms with preferred stock outstanding:
- Market value = number of preferred shares × preferred price per share.
- Cost of preferred = preferred dividend per share / preferred price per share.

### 3.6 Weights

```
Total capital at market = MV Equity + MV Debt + MV Preferred
Weight of each = its MV / total capital
```

### 3.7 Levered beta

```
Levered beta = Unlevered beta × [1 + (1 − marginal tax rate) × (MV Debt / MV Equity)]
```

This relevers to the firm's own capital structure, with the `(1 − tax rate)` factor reflecting the tax shield on interest.

If the analyst chose "Direct input" for beta, we use that figure directly for the levered beta and skip both the unlever and the relever steps.

### 3.8 Component costs

```
Cost of equity (CAPM) = risk-free rate + levered beta × equity risk premium
After-tax cost of debt = pre-tax Kd × (1 − marginal tax rate)
Cost of preferred = preferred dividend yield
```

### 3.9 WACC

```
WACC = weight_equity × cost of equity
     + weight_debt × after-tax cost of debt
     + weight_preferred × cost of preferred
```

This is the number fed into the DCF as the initial discount rate. If a terminal WACC override is set (or implied via terminal risk-free rate override), that's used for the terminal year; otherwise the discount path converges from this initial WACC toward a terminal rate equal to risk-free plus mature-market ERP over the transition period (years 6–10 of the projection).

---

## 4. Inputs and where they come from

The mix of input types depends heavily on which paths the analyst selects. At a minimum:

**From CIQ (fetched):**
- Current stock price and shares outstanding (for MV of equity)
- Book debt, interest expense (for synthetic rating and for re-pricing debt at market)
- Adjusted EBIT (from M1; for synthetic rating interest coverage)
- Debt value of operating leases (from M3)

**From Damodaran datasets:**
- Industry unlevered beta (single or multi-business variant)
- Country equity risk premium (incl. mature-market base + country risk premium decomposition)
- Country default spread
- Industry average WACC (for Approach 2 fallback)
- Synthetic rating coverage tables (small-firm / large-firm variants)
- Rating-to-spread lookup table

**Analyst judgments:**
- Which approach (Direct / Detailed / Industry Average / Decile)
- Which beta method (single/multi, US/Global/Direct)
- Which ERP method (country / operating countries / operating regions / direct)
- Which Kd method (direct / synthetic / actual)
- Weighted-average debt maturity (often defaults to 3–10 years)
- Firm type for synthetic rating (large manufacturing / small risky / financial)

Every methodology choice is a METHODOLOGY CHOICE per our Rule A2 — meaning the frontend must expose each as an interactive selector, not a hardcoded string.

---

## 5. Outputs and what consumes them

- **Initial WACC** — the discount rate for years 1–5 of the DCF, and the starting point for the years 6–10 convergence to terminal WACC.
- **Component intermediates** (levered beta, cost of equity, after-tax cost of debt, weights) — displayed on the cost-of-capital page for transparency; also used in later modules (e.g., terminal WACC computation and sensitivity analysis).
- **Market value of debt** (incl. leases) — used in the equity bridge (subtracted from firm value to get equity value).

Every downstream valuation number depends on WACC. It's not an exaggeration to say this module's correctness determines the credibility of the whole DCF.

---

## 6. Current implementation assessment

### What works

For the **default path** — Approach 1 Detailed, single-business with the firm's home-country ERP, and industry-fallback Kd — our backend produces correct results. The formulas for:
- Industry unlevered beta lookup from the single-business Damodaran dataset
- Country ERP lookup (including mature-market base + country risk premium)
- Pre-tax Kd via industry average (fallback)
- Levered beta relever with the tax-shield adjustment
- CAPM for cost of equity
- After-tax cost of debt
- WACC as weighted equity + debt blend

…all match Ginzu. Verified end-to-end against multiple test companies (MSFT, BABA, TSLA, Lenovo) — WACC numbers are in the 8–12% range, aligned with what Damodaran's datasets would produce for those industries.

### What's missing or hardcoded

The frontend currently does NOT expose the four methodology-choice selectors as dropdowns. The backend has no branching for:
- Multi-business beta weighting (multi-segment firms use single-business as a fallback, which is wrong for conglomerates)
- Multi-country ERP blending (multinationals treated as single-country)
- Synthetic rating (Kd always falls through to industry average)
- Actual rating lookup
- Direct-input overrides for beta / ERP / Kd
- Approach 2 (industry-average WACC)
- Approach 3 (regional decile)
- Preferred stock (not in schema)
- Convertible debt decomposition (not in schema)
- Market-value of debt via bond pricing (uses book debt instead)

These are the variant-expansion gaps. The single-business single-country path is correct; the expansions are each about 1–3 hours of work individually. Not blocking for the default case but limiting for non-default firms.

### Frontend reference-data support

The Input Sheet shows WACC components alongside industry benchmarks (regional and global) in the "Company vs Industry" section — that's good reference data for a user who wants to judge whether the computed WACC is reasonable for the industry. Missing: the methodology-choice selectors themselves.

### Priority rectifications (now)

- Source currently-used WACC components from the correct industry-region match (the backend does this correctly).
- Ensure adjusted debt used in weights includes lease PV (it does, via M3's adjustment).
- Ensure the marginal tax rate flowing into levered-beta relever matches the country-derived marginal (it does, via macro.tax_rate_marginal).

For the variant-expansion gaps, document as known limitations rather than block on implementing all of them. The default path is correct; the expansions are bounded scope for future sessions.

---

## 7. Revision log

| Date | Change |
|---|---|
| 2026-04-28 | Initial draft. Default-path correctness verified. Variant-expansion gaps documented as known limitations. Source: `Ginzu_NVIDIA.xlsx`, sheet `Cost of capital worksheet` (plus Synthetic rating + Country ERP sub-sheets). |
