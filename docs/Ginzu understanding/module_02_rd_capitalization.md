# Module 02 — R&D Capitalization

**Ginzu source:** `knowledge_base/Ginzu_NVIDIA.xlsx`, sheet titled `R& D converter`. Cell-level corpus in `docs/brainstorm_cache/ginzu_extracted.json`; this document presents only the financial meaning.

---

## 1. What this module is trying to do

Research and development spending is treated by GAAP as an operating expense — subtracted in full from the year it is incurred. But economically, R&D is not consumed in the year it's spent. A firm that spent a billion dollars on R&D this year is building a body of know-how, patents, process improvements, and product pipelines that will generate revenue for the next several years. That body of intangible capital **is an asset**, and spending on it **is an investment**, not a cost.

Damodaran's R&D capitalization module performs the accrual-accounting conversion that accountants would perform if they agreed R&D was an asset: it moves R&D off the income statement as an expense and onto the balance sheet as a capital asset, then depreciates that asset over its useful life. Doing this changes three things:

1. **Operating income goes up** in most cases, because the full year's R&D is added back and only a partial-year depreciation is subtracted.
2. **Book equity goes up** by the accumulated unamortized R&D (the "research asset").
3. **Return on invested capital becomes more meaningful** because both the numerator (operating income) and the denominator (invested capital) now reflect the economic reality that R&D is a capital investment.

For companies where R&D is material — technology, pharmaceuticals, biotech, semiconductors — this adjustment materially changes the picture of profitability and capital efficiency.

---

## 2. The financial intuition

### Why expensing R&D distorts the income statement

Imagine two identical software firms. Firm A is in year 1 of operation and spent $100M on R&D this year. Firm B has been operating for five years, spent $100M on R&D every year, and has built up a mature product portfolio. Under GAAP:

- Firm A's operating income is reduced by $100M.
- Firm B's operating income is also reduced by $100M.

But Firm B has five years of accumulated research investment creating revenue, while Firm A has just one. The two firms are at completely different stages of their R&D "depreciation cycle." Treating both years of R&D expense identically misrepresents this. Firm B's current-year R&D is building future capital; only a fraction of last year's R&D should properly be charged against this year's income.

### Why capitalization fixes it

When we capitalize R&D, we treat it like a building or a machine:
- The full year's R&D spend is recognized as an **investment** (added to the balance sheet).
- Each year, some fraction of every past year's R&D — the portion whose useful life has elapsed — is **depreciated** and flows back through the income statement as an expense.

The net effect on operating income in any given year:

```
Current year's R&D added back  
   minus  
Sum of depreciation on all past years' R&D still in its useful life
```

If R&D is **growing**, the current-year add-back exceeds the accumulated depreciation (which is an average over smaller past values). Operating income rises. This reflects the economic truth that an investing-for-the-future firm is not actually as unprofitable as GAAP says.

If R&D is **flat**, add-back equals depreciation in steady state. Operating income is unchanged. GAAP's implicit assumption happens to be correct here — expensing and depreciating are the same when volumes don't change.

If R&D is **shrinking**, accumulated depreciation of past (larger) investments exceeds current-year R&D. Operating income falls. This reflects the economic truth that a firm winding down its R&D base is consuming more of its intangible capital than it's replenishing.

### The balance-sheet side

Every year's past R&D that hasn't yet been fully depreciated sits on the balance sheet as the "value of research asset." This is the accumulated intangible capital. The balance-sheet identity is:

```
Value of research asset
   =  Current year's R&D spending (100% undepreciated, just invested)
    + Last year's R&D × (fraction of useful life remaining)
    + Two-years-ago R&D × (fraction of useful life remaining)
    + ... 
    + N-years-ago R&D × (last sliver of useful life remaining)
```

Where N is the amortization period. Adding this research asset to the reported book value of equity gives the adjusted book equity that reflects economic reality. That adjusted equity becomes part of the invested-capital calculation used for ROIC, and the R&D add-back to operating income flows into every downstream valuation metric.

---

## 3. The algorithm — in financial terms

### 3.1 Core assumptions

Ginzu uses **straight-line amortization over N years**. N is an analyst choice, typically:

- **3 years** for industries where R&D payoffs are short (some consumer internet, fast-moving electronics).
- **5 years** for general technology (software, computer services, semiconductors in some frameworks).
- **10 years** for long-horizon R&D (pharmaceuticals, biotech, aerospace).

Damodaran publishes industry-specific recommendations derived from empirical analysis of how long R&D investments typically generate revenue. The "right" N for a specific firm is a matter of judgment but should be informed by the industry norm.

Straight-line is used rather than an accelerated or declining-balance depreciation because (a) it keeps the math interpretable and (b) R&D payoffs tend to be relatively uniform over their useful life compared to, say, equipment which degrades faster in later years.

### 3.2 The per-vintage calculation

For each past year of R&D — let's index it by t, where t = 1 is "one year ago", t = 2 is "two years ago", and so on — two numbers are computed:

**Unamortized fraction** — the portion of that year's R&D investment whose useful life has NOT yet been consumed:

```
Unamortized fraction for t-year-old R&D = (N − t) / N
```

- For one-year-old R&D with N = 5: (5 − 1) / 5 = 4/5 = 80%. Still 80% undepreciated.
- For three-year-old R&D with N = 5: (5 − 3) / 5 = 2/5 = 40% undepreciated.
- For five-year-old R&D with N = 5: (5 − 5) / 5 = 0%. Fully depreciated; drops off the balance sheet.

**Annual depreciation charge** — the portion of that year's R&D investment whose useful life IS being consumed in the current year:

```
Depreciation in current year from t-year-old vintage = (past R&D at year t) / N
```

One-fifth of every vintage within the amortization window is depreciated each year. A vintage stays on the balance sheet for exactly N years before it's fully depreciated.

### 3.3 The aggregate outputs

Summing across all vintages within the amortization window (t = 1 through t = N), plus the current year (which is 100% undepreciated):

**Value of research asset** (goes on the adjusted balance sheet):
```
= Current year's R&D (100% undepreciated)
  + Σ [past R&D at year t] × (N − t) / N,  for t = 1 to N
```

This is the accumulated intangible capital the firm has built through its R&D program, net of the depreciation already charged.

**Total depreciation this year** (flows through the income statement):
```
= Σ [past R&D at year t] / N,  for t = 1 to N
```

Each vintage within the amortization window contributes its 1/N slice. Notice that the current year is NOT included here — current-year R&D is the investment just made; it hasn't had time to depreciate yet.

**Adjustment to operating income** (the add-back to adjust GAAP EBIT):
```
= Current year's R&D − Total depreciation this year
```

This is the pre-tax net correction. Positive when R&D is growing, zero when flat, negative when shrinking.

### 3.4 Applied to the financial statements

```
Adjusted EBIT = Reported EBIT + Adjustment to operating income (pre-tax)
Adjusted Net Income = Reported Net Income + Adjustment (also pre-tax; tax effect ignored here)
Adjusted Book Equity = Reported Book Equity + Value of research asset
```

The tax effect of the EBIT adjustment — what the tax on the adjustment WOULD have been if R&D had been capitalized for tax purposes — is computed in Ginzu as a reference number but **not wired into any downstream calculation**. The assumption is that the firm's effective tax rate captures the real cash tax impact of however accountants actually treated R&D.

---

## 4. Inputs and where they come from

Ginzu's `R& D converter` sheet asks the analyst to type in both the amortization period and every year of past R&D expense. In our system, only one of these is genuinely a judgment call:

- **Amortization period (N)** — this is the one true analyst judgment. Should be 3, 5, or 10 depending on the industry. The user may override, but the default should be set intelligently based on the industry Damodaran has classified the firm into.
- **Current year's R&D expense** — fetched from CIQ. Ideally this should be the LTM-rotated R&D (consistent with the LTM base year used elsewhere in the pipeline), not the stale FY-0 R&D.
- **Past years' R&D expenses** — fetched from CIQ. Ten years of history are fetched routinely; the N most recent are consumed. Ginzu treats these as analyst-typed; we treat them as pure CIQ facts.

The sheet formally has capacity for up to 10 past years; if the analyst sets N = 3, only the first three are used. Our code mirrors this: the past-R&D list is sliced to the first N entries.

---

## 5. Outputs and what consumes them

Three outputs flow downstream:

- **Value of research asset** enters the **invested capital calculation** (via the adjusted book equity) in the cost-of-capital sheet and in the ROIC diagnostic row of the valuation output. Higher value of research asset means higher invested capital, which reduces ROIC for a given NOPAT — a critical correction for R&D-heavy firms whose GAAP ROIC looks artificially high precisely because their GAAP invested capital is artificially low.

- **Total depreciation this year** flows into the adjusted cash-flow calculation (as an add-back to D&A for accrual-to-cash reconciliation) and into the adjusted invested-capital ROIC numerator alongside the EBIT adjustment.

- **Adjustment to operating income** flows directly into **adjusted EBIT**, which is the base-year EBIT entering the DCF and which seeds the implied base-year operating margin. Because the DCF projects forward from this base, the R&D adjustment has a direct multiplier effect on every projected year of FCFF.

Every downstream module therefore sees a different version of the company's profitability than what GAAP reports: one that treats R&D as capital investment, not as operating expense.

---

## 6. Reasoning behind design choices

### Why include the current year's R&D at 100% undepreciated?

The intuition is "investment just made, no depreciation yet earned." When we capitalize a machine we just bought, its full cost sits on the balance sheet and the first year of depreciation starts flowing through the income statement in the NEXT fiscal period. Same logic applies to R&D: the investment just made hasn't been consumed yet.

### Why straight-line? Why not accelerated?

Empirically, R&D payoffs don't decline over time in the way a machine's productivity declines. A software platform built five years ago often generates the same revenue today as the platform built one year ago — sometimes more. Straight-line captures this relatively level contribution of each vintage.

Accelerated schedules would overweight the near-term benefit of R&D, implying the payoff drops off quickly — that matches R&D in fast-moving industries (3-year amortization handles this) more than it matches pharma or aerospace.

### Why is the current year excluded from the depreciation sum?

Because the depreciation is already captured in the reported income statement AS an operating expense. The current year's R&D has been fully deducted already by GAAP; we're adding it back and re-classifying as investment. Only the PAST vintages are depreciating in the current period.

### Why is the tax effect ignored downstream?

The reported tax expense on the income statement already reflects whatever the firm paid in cash taxes, which depends on whatever R&D treatment their tax filings used (in the US, R&D is partially deductible for tax under various rules). Re-computing the tax as if R&D had been capitalized for tax purposes would double-count the tax adjustment. Ginzu pragmatically uses the reported effective tax rate and lets the R&D add-back flow through pre-tax, accepting the minor inconsistency in exchange for avoiding a hornets' nest of tax accounting.

---

## 7. Edge cases

### Amortization period = 0

An N of zero would imply R&D has no useful life — economically nonsense, mathematically a division-by-zero. Code guards against this by returning zero for all outputs when N ≤ 0.

### No past R&D history

A company just starting to disclose R&D (or with no prior R&D at all) has no past vintages to amortize. Value of research asset collapses to just the current year's spend. Total depreciation is zero. Adjustment to operating income equals current R&D — a pure add-back. This is correct behavior for a firm in its first year of R&D investment.

### Past history shorter than N

The sum over past vintages simply terminates at whatever history is available. If N = 10 but only 6 years of history exist, we sum over 6 years. The value of research asset is slightly understated (we're missing four vintages' worth of accumulated capital), but this is a data limitation, not a methodology flaw.

### Past history longer than N

Only vintages within the amortization window matter. Any R&D older than N years has been fully depreciated already — its unamortized fraction is zero. Code explicitly caps the loop at N vintages.

### R&D that moved across classifications

Some companies have reclassified R&D between line items in their history (e.g., capitalized portions, R&D-in-process acquired). Our CIQ fetch uses a primary mnemonic with a documented fallback; if a year's R&D shows zero but the firm clearly has been doing R&D, analyst intervention is required. This is a data-quality concern, not a capitalization-methodology flaw.

---

## 8. Current implementation assessment

### Formula correctness

The backend implements the Ginzu R&D capitalization formulas exactly as Damodaran specifies. The per-vintage unamortized fraction uses (N − t) / N. The per-vintage annual depreciation uses past R&D divided by N. The aggregate value of research asset correctly includes the current year at 100% plus accumulated unamortized past vintages. The aggregate depreciation excludes the current year. The adjustment to EBIT is pre-tax. The adjusted book equity correctly adds the value of research asset to the reported book equity. All tests in the existing suite covering R&D capitalization pass.

### Data-flow consistency

One known inconsistency: the R&D module takes its "current year's R&D" from the FY-0 annual value stored in the adjustment-inputs object, not from the LTM-rotated R&D. Every other module in the pipeline now operates on the LTM base year. Using FY-0 R&D mixes time windows — we're adding back an FY-0 R&D figure on top of an LTM EBIT base. For Microsoft this creates a roughly 0.8% distortion in adjusted EBIT. Not large, but inconsistent with the principle that the pipeline should operate on a single time window. Fixable by sourcing `r_and_d_expense_current` from the LTM rotated value.

### Frontend display — the inputs

The Input Sheet shows the R&D section with the capitalize-yes-no toggle, the amortization period, current year R&D, and the N most recent past-year R&D values. Tooltips on each value show the CIQ mnemonic and period used to fetch it. However, the Input Sheet does **not** show any derived outputs of the R&D capitalization — the value of research asset, the annual depreciation, the adjustment to EBIT — all of which are the economically interesting numbers. The analyst has to click through to the dedicated R&D Converter page to see the outputs.

### Frontend display — the R&D Converter page

The R&D Converter page shows the full amortization schedule: every vintage with its unamortized fraction, unamortized amount, and annual depreciation, plus a totals row. This is Ginzu-faithful and fully auditable. The summary section at the bottom shows value of research asset, unamortized R&D, annual amortization, and adjusted EBIT — all the outputs present.

### Reference-data support for the analyst judgment (N)

The amortization period is the one true judgment input. The frontend currently shows only the static hint "3, 5, or 10" next to the N input cell. There is **no industry-specific recommendation** — for a software company the UI doesn't tell the analyst "5 is the convention for your industry"; for a pharmaceutical company it doesn't say "use 10." Damodaran publishes these industry defaults; we have the industry classification in the response; connecting them would take a simple lookup table.

There is also no contextual information about the **historical pattern of R&D spending** — the ratio of R&D to revenue per year, the growth rate of R&D over 5 or 10 years, or how the firm's R&D intensity compares to industry peers. All of this is derivable from already-fetched data. Adding these would materially improve the analyst's ability to sanity-check whether a 5-year or 10-year amortization is appropriate.

### Summary

The core capitalization math is correct. The in-pipeline data-flow has one minor inconsistency (FY-0 R&D vs LTM EBIT). The frontend presentation is good on the derivation page but weak on the Input Sheet (inputs shown, outputs hidden) and weak on reference-data support for the one genuine analyst judgment (amortization period).

---

## 9. Revision log

| Date | Change |
|---|---|
| 2026-04-28 | Initial draft. Pure financial-reasoning presentation per user's preference. Source: `Ginzu_NVIDIA.xlsx`, sheet `R& D converter`. |
