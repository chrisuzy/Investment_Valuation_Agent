# Three-Story Joint Examination of the Growth Stories

**Source:** Aswath Damodaran, *Narrative and Numbers* (the coupling of three authored stories into a single arithmetically consistent valuation). Grounded in the existing folder: `module_05_dcf_projection.md §2` (philosophy of the three levers), `module_06_terminal_and_pv.md §3` (terminal reinvestment identity), `module_03_operating_leases.md §5` and `module_02_rd_capitalization.md §5` (Invested Capital composition).

---

## 1. What this module is trying to do

Every intrinsic DCF is the composition of three narrative judgments an analyst makes about the future — the *growth story*, the *margin story*, and the *capital-efficiency story*. The analyst writes these three as if they were independent: a story of market opportunity, a story of competitive positioning, a story of asset productivity.

At the arithmetic level they are not independent. Once the three stories are on the page, they mechanically imply a fourth quantity — the return on invested capital the firm must earn for the three stories to be internally consistent. If that implied ROIC is absurd (far above the firm's history, far above what any firm in the industry produces, or far above the cost of capital), the story is broken regardless of how plausible each individual piece sounds in isolation.

This module — the three-story joint examination — is the discipline that confronts the analyst with the arithmetic their three stories just committed to. It does not judge the story. It does not warn. It does not flag. It displays: *here is what your story requires, here is what the firm has historically delivered, here is what the industry delivers, here is the cost of capital.* The analyst reads the comparison and decides.

---

## 2. The financial intuition

A DCF asks the analyst to tell three stories:

- **Growth story** — How fast will revenue grow? (A claim about market opportunity and market share.)
- **Margin story** — How profitable will each dollar of revenue be at maturity? (A claim about pricing power and competitive moat.)
- **Capital-efficiency story** — How much new capital is required to produce each new dollar of revenue? (A claim about asset productivity and business model.)

The analyst writes each narrative independently. They feel separate because they describe different aspects of the business — demand, profitability, productivity.

But they are tied together by a mathematical identity every finance student learns: the DuPont decomposition.

```
ROIC = NOPAT / Invested Capital
     = (NOPAT / Revenue) × (Revenue / Invested Capital)
     = Operating Margin after tax × Sales-to-Capital
```

Once the analyst has chosen a margin and a sales-to-capital ratio, **they have simultaneously chosen an ROIC**. There is no optional fourth judgment about ROIC — it is forced by the first two.

A parallel identity ties growth to reinvestment:

```
Expected Growth = Reinvestment Rate × ROIC
```

If the analyst's growth story outruns what the firm's historical ROIC × RIR supports, the story is implicitly assuming the firm will either earn higher returns on capital, reinvest more aggressively, or both. That assumption may be defensible, but it should be an explicit narrative claim — not an accidental one hidden in the arithmetic.

This is what Damodaran means when he writes that *every number in a DCF is the echo of a story and every story has a numerical consequence.* The three stories project forward; the arithmetic echoes back and demands coherence.

---

## 3. The algorithm — in financial terms

### 3.1 Implied ROIC from the three stories

Given the analyst's three story inputs, the implied ROIC at any projection year is:

```
Revenue[t]           = Revenue[t-1] × (1 + growth_story[t])
Margin[t]            = margin_story convergence path
Invested_Capital[t]  = Invested_Capital[t-1] + ΔRevenue[t] / S_C_story[t]
NOPAT[t]             = Revenue[t] × Margin[t] × (1 − tax_rate[t])
Implied_ROIC[t]      = NOPAT[t] / Invested_Capital[t-1]
```

The terminal-year Implied_ROIC is the most important single diagnostic because, per `module_06_terminal_and_pv.md §4`, the terminal state should have no excess returns — the terminal Implied_ROIC should converge to the terminal WACC. If it doesn't, the story is asking the firm to earn permanent super-normal returns in perpetuity, which contradicts the Gordon-growth assumption.

### 3.2 Required ROIC — reverse calculation

If the analyst has already committed to a margin and an S/C, the ROIC required to make the three stories internally consistent is forced by DuPont:

```
Required_ROIC = margin_story × S_C_story
```

This is a DIRECT calculation, not an inverse-solve. It answers the question: *"What ROIC does the analyst's story require?"*

### 3.3 Required S/C — reverse calculation

If the analyst has committed to a growth rate and a margin, the sales-to-capital ratio required for the reinvestment math to close is derived from the fundamental growth identity combined with the Ginzu reinvestment formula. Starting from `g = ROIC × RIR` and substituting the reinvestment formula `Reinvestment = ΔRevenue / S/C`:

```
ΔRevenue / S/C = Required Reinvestment
             = g × NOPAT / ROIC_target

Required_S_C = ΔRevenue × ROIC_target / (g × NOPAT)
            = ROIC_target / margin_story     (after algebraic simplification)
```

Where `ROIC_target` is whatever benchmark ROIC the analyst wants to anchor against — historical ROIC, industry median ROIC, or the firm's cost of capital.

This answers: *"Given your growth and margin stories, what S/C must the firm achieve for this story to produce the ROIC you think is realistic?"*

### 3.4 Historical and industry anchors

The analyst has two natural reference points to compare `Implied_ROIC`, `Required_ROIC`, and `Required_S_C` against:

- **The firm's own history.** Annual ROIC for the last 5 fiscal years, 3-year average, 5-year average. Annual Sales/IC for the last 5 fiscal years, 3-year average, 5-year average. Annual revenue growth for the last 5 fiscal years. These anchor the judgment: *"Has this firm actually done what the story assumes?"*

- **The industry.** Damodaran's industry dataset provides median ROIC, median Sales/IC, median operating margin, and quartile ranges (Q1–Q3) across all firms in the relevant industry. These anchor a different judgment: *"Has any firm in this industry done what the story assumes?"*

The joint examination displays the analyst's implied/required numbers side-by-side with both anchors. The gaps between them are the story the analyst is implicitly telling about how this firm will differ from itself and from its peers.

---

## 4. Inputs — classified by source

**JUDGMENT (analyst story):**
- `revenue_growth_next_year`
- `revenue_growth_years_2_5`
- `operating_margin_next_year` (Year 1 margin)
- `target_operating_margin`
- `margin_convergence_year` K
- `sales_to_capital_high` (Years 1–5)
- `sales_to_capital_stable` (Years 6–10)

**HISTORICAL (computed from CIQ-fetched annual data):**
- Annual revenue growth for the last 5 years (derived from `raw_financials[0..4].revenues`)
- Annual ROIC for the last 5 years (NOPAT_t / Invested_Capital_{t-1})
- Annual Sales/IC for the last 5 years (Revenue_t / Invested_Capital_t)
- Annual pre-tax operating margin for the last 5 years (EBIT_t / Revenue_t)
- 3-year and 5-year averages of each of the above

**INDUSTRY BENCHMARKS (from Damodaran industry dataset):**
- Industry median ROIC
- Industry median Sales/IC
- Industry median pre-tax operating margin
- Industry median revenue growth (recent)
- Q1 and Q3 of each across all firms in the industry

**MACRO:**
- WACC (from `CostOfCapital.wacc`)
- Risk-free rate (from `MacroInputs.risk_free_rate`)
- Marginal tax rate (from `MacroInputs.tax_rate_marginal`)

---

## 5. Outputs and what consumes them

This module has **no downstream valuation consumers** — it does not feed Modules 5, 6, or the equity bridge. Its outputs are diagnostic only:

- `implied_roic_per_year[1..10]` — the ROIC forced by the three stories in each projection year
- `implied_roic_terminal` — the ROIC at the terminal state
- `required_roic_from_stories` — DuPont-derived from the story inputs (margin × S/C)
- `required_s_c_for_growth` — reverse-derived from growth + margin vs. an ROIC target
- `historical_roic_by_year[0..4]` + `avg_3yr`, `avg_5yr`
- `historical_s_c_by_year[0..4]` + `avg_3yr`, `avg_5yr`
- `historical_margin_by_year[0..4]` + `avg_3yr`, `avg_5yr`
- `historical_revenue_growth_by_year[0..4]` + `avg_3yr`, `avg_5yr`

All consumed by the **Stories to Numbers** page in the frontend, where they are displayed alongside the editable story inputs and the industry benchmarks for visual comparison.

---

## 6. Reasoning — why this shape

**Why display-only and never judging.** The three-story examination is a *tool for the analyst*, not a gate on the valuation. The analyst may deliberately tell a story where required ROIC is far above historical — they may be forecasting a regime change, a new product, a cost-structure overhaul. The arithmetic cannot distinguish between a reckless assumption and a bold but well-reasoned one. Only the analyst can. The module surfaces the number the analyst's story commits to; the judgment is theirs.

**Why the comparison against three anchors (implied vs historical vs industry vs WACC).** Each anchor tells a different question:

- *Historical* answers: has this firm done it before?
- *Industry* answers: has any firm like this done it before?
- *WACC* answers: is this firm creating value, or merely moving money through the business?

Damodaran calls the triangulation across these three anchors the **3P** test — does the story produce a *Possible*, *Plausible*, or *Probable* outcome? A story above the cost of capital is Possible (the math works). A story within the industry's Q1–Q3 range is Plausible (peers do this). A story within the firm's own historical range is Probable (the firm has actually demonstrated it). Gaps between the anchors and the implied number tell the analyst exactly which level of claim their story is making.

**Why the reverse calculations are raw numbers plus a factual gap.** A bare number ("Required ROIC = 18%") invites the analyst to mentally compute the delta. Showing the delta explicitly ("Required ROIC is 6pp above historical") makes the implicit story explicit without crossing into judgment. The gap is a fact about the arithmetic, not an opinion about the story.

---

## 7. Edge cases and quirks

- **Negative historical NOPAT.** A loss-making firm has undefined ROIC (division by zero or negative). The historical row displays "—" with a tooltip: "No historical ROIC — firm has negative NOPAT in this year."
- **Negative or zero `Invested_Capital`.** Rare but occurs when R&D-heavy firms have very negative book equity. Displays "—"; the implied and required ROIC calculations skip these years.
- **Reinvestment rate > 1 in any year.** The story is asking the firm to plow back more than it earns — requires external financing. Shown as a factual note under Section 3.3's required S/C row: "Reinvestment rate this year = 1.3 — firm must raise external capital to fund growth."
- **Terminal state with ROIC override above WACC.** If the analyst has set `roic_stable_override` above terminal WACC (asserting durable moat), the terminal invariant check will *always* show a gap — this is the analyst's deliberate claim of excess returns. The module shows the gap without comment.
- **No industry data available.** If Damodaran industry lookup fails (unusual industry classification), the industry column shows "—" with source note; historical and required columns remain fully populated.
- **Fresh upload with all story inputs blank.** Implied ROIC cannot be computed (inputs missing). The module shows the historical and industry columns only, with a note: "Enter your story inputs above to see the cross-examination."

---

## 8. Current implementation assessment

**Not yet implemented.** This module is proposed in `docs/superpowers/specs/2026-05-04-three-story-consistency-and-lenovo-anomalies-design.md`.

When implemented, the module will consist of:
- Backend: historical-series computations in `module_3_cashflow.py` (annual ROIC, annual S/C, 3yr/5yr averages); reverse-calculation helpers; extension of `DCFResult` to expose `implied_roic_projections` and `implied_roic_terminal`.
- Frontend: Section 1 of the Stories to Numbers page, restructured around three story blocks with co-located historical + industry + reverse-check rows, plus a top-of-page closed-loop summary strip.

No valuation math changes. The existing DCF engine continues to project FCFF exactly as today; the three-story examination is layered on top as a diagnostic read-out of the same numbers, organized around the three narrative questions rather than around the 10-year time axis.

---

## 9. Revision log

| Date | Change |
|---|---|
| 2026-05-04 | Initial draft. Documents the three-story closed-loop examination as the conceptual foundation for the redesigned Stories to Numbers page. |
