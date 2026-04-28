# The Damodaran Valuation Framework

## A Textbook-Style Planning Document

**Source of truth:** Aswath Damodaran's "fcffsimpleginzu" workbook structure.
**Financial dictionary reference:** `PRD.md` (Chinese).
**Scope:** Generic — applicable to any publicly traded company.

---

## Table of Contents

1. [Scope, Audience, and Philosophy](#1-scope-audience-and-philosophy)
2. [Prerequisites: Data Inputs and Their Sources](#2-prerequisites-data-inputs-and-their-sources)
3. [Stage 1 — Base Year Normalization (Trailing Twelve Months)](#stage-1--base-year-normalization-trailing-twelve-months)
4. [Stage 2 — Financial Statement Adjustments](#stage-2--financial-statement-adjustments)
5. [Stage 3 — Cost of Capital Construction](#stage-3--cost-of-capital-construction)
6. [Stage 4 — Story Calibration (User Assumptions)](#stage-4--story-calibration-user-assumptions)
7. [Stage 5 — Ten-Year Explicit Projection](#stage-5--ten-year-explicit-projection)
8. [Stage 6 — Terminal Value](#stage-6--terminal-value)
9. [Stage 7 — Discounting to Present Value](#stage-7--discounting-to-present-value)
10. [Stage 8 — Failure Probability Overlay](#stage-8--failure-probability-overlay)
11. [Stage 9 — Equity Value Bridge](#stage-9--equity-value-bridge)
12. [Stage 10 — Per-Share Value and Market Verdict](#stage-10--per-share-value-and-market-verdict)
13. [Feedback Loops and Iterative Solutions](#13-feedback-loops-and-iterative-solutions)
14. [Dependency Graph](#14-dependency-graph)
15. [Diagnostic Sanity Checks](#15-diagnostic-sanity-checks)
16. [Generic Application Checklist](#16-generic-application-checklist)
17. [Glossary of Variable Names](#17-glossary-of-variable-names)

---

## 1. Scope, Audience, and Philosophy

### Purpose of this document

This is a complete, executable specification of how to perform an intrinsic equity valuation for *any* publicly traded company using Damodaran's methodology. Follow the stages in order. Every calculation is defined with (a) its financial meaning, (b) its inputs and their sources, (c) the exact formula, and (d) why the formula is structured that way.

### Core philosophical principles

1. **Value the whole firm, not the equity directly.** The firm (Value_of_Operating_Assets) is what generates cash flow. Equity is what remains after creditors (debt holders, minority interests) are paid.
2. **Free Cash Flow to the Firm (Free_Cash_Flow_to_Firm) is the cash available to all capital providers after operating expenses, taxes on operating income, and reinvestment in productive capacity.**
3. **Value today equals the discounted sum of all future Free_Cash_Flow_to_Firm.** Discount rate is the Weighted_Average_Cost_of_Capital (a blended cost that reflects the risk borne by both equity and debt holders).
4. **Separate three periods.** A high-growth period (typically years 1 through 5), a transition period (years 6 through 10 where growth, margin, tax, and cost of capital converge linearly toward maturity), and a stable/terminal period (year 11 onward, captured in a single Terminal_Value).
5. **Every assumption must be defensible as a story.** Growth rate tells a story about market opportunity. Margin tells a story about competitive position. Reinvestment rate tells a story about capital efficiency. Cost of capital tells a story about risk.
6. **The valuation is self-consistent.** Cost of capital depends on market equity value, which depends on the valuation itself. The correct answer requires iterative (fixed-point) solution, not a one-pass calculation.

### Audience

This document is written for an implementer (either a human analyst or an automated system) who has the raw data but needs the method.

---

## 2. Prerequisites: Data Inputs and Their Sources

Before starting, assemble the following data. Each item below must be obtainable for any publicly traded firm, or the valuation cannot proceed.

### A. Company identification
| Variable | Source |
|---|---|
| Company_Name | Company's website, SEC filings, or exchange listing |
| Primary_Ticker_Symbol | Exchange listing |
| Country_of_Incorporation | Legal formation country from latest 10-K cover page |
| US_Industry_Classification | Map company to one of Damodaran's ~95 US industry groups (via SIC/GICS code or manual classification) |
| Global_Industry_Classification | Same, using the Global industry list |
| Fiscal_Year_End_Date | 10-K front matter |
| Most_Recent_10K_Period_End_Date | 10-K |
| Most_Recent_10Q_Period_End_Date | 10-Q |

### B. Base-year financial statement data

Pulled from the most recent 10-Q (for Last_Twelve_Months flow items) and the most recent balance sheet:

| Variable | Financial meaning | Source |
|---|---|---|
| Total_Revenue_Last_Twelve_Months | Top-line revenue over the 12 months ending at most recent 10-Q | 10-K + adjustment via 10-Q |
| Operating_Income_Last_Twelve_Months | EBIT = Operating Income before interest and tax | Same |
| Interest_Expense_Last_Twelve_Months | Total interest expense on debt | Same |
| Book_Value_of_Equity | Total stockholders' equity at most recent quarter | Most recent 10-Q balance sheet |
| Book_Value_of_Debt | Short-term debt + long-term debt (interest-bearing) | Same |
| Cash_and_Marketable_Securities | Cash + short-term investments | Same |
| Cross_Holdings_and_Non_Operating_Assets | Investments in affiliates, unconsolidated JVs, other non-operating assets | Same |
| Minority_Interests | Non-controlling interests | Same |
| Research_and_Development_Expense_Current_Year | Current year R&D spend | Income statement |
| Research_and_Development_Expense_Past_Years | R&D spend for each of past 5–10 years | Historical 10-Ks |
| Operating_Lease_Expense_Current_Year | Current year lease expense (if not already capitalized) | Income statement or lease footnote |
| Operating_Lease_Commitments_Year_1_to_5 | Future contractual commitments years 1–5 | Lease footnote in 10-K |
| Operating_Lease_Commitments_Beyond_Year_5 | Total lump sum beyond year 5 | Same |

### C. Market data
| Variable | Source |
|---|---|
| Primary_Shares_Outstanding | Most recent 10-Q cover page |
| Current_Stock_Price | Market data feed (real-time) |
| Effective_Tax_Rate | Income taxes paid / Pre-tax income from 10-K |
| Marginal_Tax_Rate | Statutory corporate rate for country of incorporation (for US: 21% federal + ~4% state = ~25%) |
| Credit_Rating | S&P or Moody's if rated; otherwise skip and use synthetic rating |

### D. Employee stock options (if applicable)
| Variable | Source |
|---|---|
| Number_of_Options_Outstanding | Proxy statement or 10-K footnote |
| Weighted_Average_Strike_Price | Same |
| Weighted_Average_Remaining_Life_in_Years | Same |
| Annualized_Stock_Return_Standard_Deviation | Computed from 2-5 years of daily stock returns |

### E. Geographic revenue breakdown
| Variable | Source |
|---|---|
| Revenue_by_Country_or_Region | 10-K segment disclosure (for multi-national ERP calculation) |

### F. Macroeconomic inputs
| Variable | Source |
|---|---|
| Risk_Free_Rate | Yield on 10-year government bond in the reporting currency |
| Country_Equity_Risk_Premium | Damodaran annual "ctryprem.xls" dataset |
| Country_Default_Spread | Same dataset |

### G. Industry reference data (from Damodaran's annual Excel datasets)
| Variable | Source file |
|---|---|
| Industry_Unlevered_Beta (US) | `betas.xls` |
| Industry_Unlevered_Beta (Global) | `betaGlobal.xls` |
| Industry_Average_Pretax_Operating_Margin | `margin.xls` |
| Industry_Average_Sales_to_Capital_Ratio | `capex.xls` |
| Industry_Average_Return_on_Invested_Capital | `EVA.xls` |
| Industry_Average_Stock_Standard_Deviation | `betas.xls` |
| Industry_Average_Cost_of_Capital | `wacc.xls` |
| Industry_EV_to_Sales_Multiple | `psdata.xls` |
| Industry_EV_to_EBITDA_Multiple | `vebitda.xls` |
| Industry_Distribution_Quartiles | `fundgrEB.xls` and related |

### H. Credit and rating data (Damodaran tables)
- Rating → default spread lookup table
- Interest coverage ratio → synthetic rating table (small-firm and large-firm variants)
- Failure probability by rating and corporate age

---

## Stage 1 — Base Year Normalization (Trailing Twelve Months)

### Purpose

The most recent 10-K may be up to 12 months out of date. Because valuation is forward-looking, we must start from the freshest possible picture: the Trailing Twelve Months (Last_Twelve_Months, abbreviated LTM). This normalization replaces stale 10-K flows with LTM flows computed from the 10-K plus year-to-date 10-Q data.

### Inputs required

- Last_10K_Value (for each flow item)
- Current_Year_Year_to_Date_Value (from most recent 10-Q)
- Prior_Year_Same_Year_to_Date_Value (from the 10-Q of the same fiscal period, one year earlier)
- Most_Recent_10Q_Balance_Sheet_Value (for balance sheet items)

### Calculation — Flow items (Revenue, Operating Income, Interest Expense, R&D Expense, etc.)

```
Last_Twelve_Months_Value = 
    Last_10K_Value 
  + Current_Year_Year_to_Date_Value 
  - Prior_Year_Same_Year_to_Date_Value
```

### Calculation — Balance sheet items (Book Equity, Book Debt, Cash, etc.)

```
Base_Year_Balance_Sheet_Value = Most_Recent_10Q_Balance_Sheet_Value
```

No subtraction or addition — balance sheet items are point-in-time snapshots.

### Reasoning

The LTM identity works because:
- Last_10K_Value covers fiscal year N (full 12 months of year N).
- Current_Year_Year_to_Date_Value covers the first K quarters of year N+1.
- Prior_Year_Same_Year_to_Date_Value covers the first K quarters of year N.
- Subtracting the third from the first removes the stale early quarters of year N.
- Adding the second fills in the fresh early quarters of year N+1.
- Net result: exactly the 12 months ending at the most recent 10-Q.

For balance sheets we do not sum quarters because a balance sheet is already a total — taking the most recent 10-Q gives the most current snapshot.

### Outputs

Normalized base-year Revenue, Operating_Income, Interest_Expense, Research_and_Development_Expense, and all balance sheet items.

### Generic applicability

Works for any company with at least one annual and one quarterly report. For companies that report only annually, skip this stage and use the most recent 10-K values directly.

---

## Stage 2 — Financial Statement Adjustments

### Purpose

Accounting standards treat two kinds of capital-like investments as operating expenses: Research_and_Development and Operating_Leases (in older filings). Both economically create assets that produce revenue for multiple years, but GAAP expenses them immediately. This:

- Understates Operating_Income (subtracts the entire investment instead of amortizing)
- Understates Book_Equity (does not record the intangible asset)
- Understates Debt (operating leases are contractually committed future payments = debt)
- Distorts Return_on_Invested_Capital and all multiples

We correct both.

### 2a. Research and Development Capitalization

#### Financial reasoning

Research and Development spending produces intangible assets: patents, know-how, proprietary technology, brand. These assets generate revenue for a useful life of typically 3 to 10 years. Under accrual accounting, expensing R&D immediately misrepresents both the income statement (understates profits from legacy R&D that is still productive) and the balance sheet (omits the research asset).

#### Inputs required

- Research_and_Development_Expense_Current_Year
- Research_and_Development_Expense_Past_Years (a list, indexed by how many years ago: year –1 is one year ago, year –2 is two years ago, etc.)
- Amortization_Period_in_Years (typical: 5 for most industries; 3 for fast-moving tech like semiconductors; 10 for pharmaceuticals and aerospace)
- Marginal_Tax_Rate (for computing tax effect)

#### Calculation

For each past year at index t (where t = 1 means one year ago, t = 2 means two years ago, up to t = Amortization_Period_in_Years):

```
Unamortized_Fraction_at_t = 
    (Amortization_Period_in_Years - t) / Amortization_Period_in_Years

Unamortized_Value_at_t = 
    Research_and_Development_Expense_Past_Year_t × Unamortized_Fraction_at_t

Amortization_This_Year_from_Year_t = 
    Research_and_Development_Expense_Past_Year_t / Amortization_Period_in_Years
```

Aggregate across all past years:

```
Value_of_Research_Asset = 
    Research_and_Development_Expense_Current_Year 
  + Σ Unamortized_Value_at_t (for t = 1 to Amortization_Period_in_Years)

Total_Amortization_of_Research_Asset_This_Year = 
    Σ Amortization_This_Year_from_Year_t (for t = 1 to Amortization_Period_in_Years)
```

Apply adjustments:

```
Adjusted_Operating_Income (first pass) = 
    Reported_Operating_Income 
  + Research_and_Development_Expense_Current_Year 
  - Total_Amortization_of_Research_Asset_This_Year

Adjusted_Book_Value_of_Equity = 
    Reported_Book_Value_of_Equity 
  + Value_of_Research_Asset
```

#### Reasoning for each line

- Add back the full current year's R&D: it was expensed by accounting, but it belongs on the balance sheet.
- Subtract amortization of all past years: we now recognize it as a cost of doing business, spread over the amortization period.
- Net effect: if R&D is growing, adjusted EBIT > reported EBIT. If R&D is flat, they are equal. If R&D is shrinking, adjusted EBIT < reported.

#### Generic applicability

Apply to any firm with material R&D. For companies where R&D is negligible (retail, real estate, consumer staples), skip this stage.

### 2b. Operating Lease Capitalization

#### Financial reasoning

Before 2019, operating leases were kept off the balance sheet as "rental expense." Economically, a multi-year lease obligation is a debt contract. A firm that leases its headquarters for $10 million per year for 20 years has a $10 million × 20 = $200 million nominal debt-like obligation, discounted by the firm's cost of borrowing.

After ASC 842 (US GAAP 2019) and IFRS 16 (IFRS 2019), most leases are already on the balance sheet. Still apply this stage if:
- Financial statements predate 2019
- The firm reports material off-balance-sheet commitments
- The data is from a jurisdiction that has not yet adopted the new standards

#### Inputs required

- Operating_Lease_Expense_Current_Year
- Operating_Lease_Commitment_Year_1 through Operating_Lease_Commitment_Year_5
- Operating_Lease_Commitment_Beyond_Year_5 (total lump sum, from lease footnote)
- Pre_Tax_Cost_of_Debt (from Stage 3 — requires either iteration or an initial estimate)

#### Calculation

**Step 1: Estimate the annuity length for the "beyond year 5" lump sum.**

```
Number_of_Additional_Years_Beyond_Five = 
    ROUND(
        Operating_Lease_Commitment_Beyond_Year_5 
        / AVERAGE(Operating_Lease_Commitments_Year_1_to_5), 
        0
    )

Annual_Annuity_Beyond_Year_Five = 
    Operating_Lease_Commitment_Beyond_Year_5 
    / Number_of_Additional_Years_Beyond_Five
```

**Reasoning:** The footnote gives a single lump sum for "beyond year 5" without specifying years 6, 7, 8... Damodaran's rule: assume the lump sum is an annuity whose duration equals the lump amount divided by the average of years 1–5. A company paying $200 with avg yr 1–5 = $100 has 2 more years (6 and 7) of $100 each.

**Step 2: Present value of years 1 through 5:**

```
Present_Value_of_Lease_Years_1_to_5 = 
    Σ [Operating_Lease_Commitment_Year_t / (1 + Pre_Tax_Cost_of_Debt)^t]
    for t = 1 to 5
```

**Step 3: Present value of the annuity beyond year 5:**

```
Present_Value_of_Annuity_at_Year_Five = 
    Annual_Annuity_Beyond_Year_Five 
    × [1 - (1 + Pre_Tax_Cost_of_Debt)^(-Number_of_Additional_Years_Beyond_Five)] 
    / Pre_Tax_Cost_of_Debt

Present_Value_of_Beyond_Year_Five_Commitments = 
    Present_Value_of_Annuity_at_Year_Five 
    / (1 + Pre_Tax_Cost_of_Debt)^5
```

**Reasoning:** First compute the annuity's value at time year 5 (standard annuity PV formula). Then discount back 5 years to present.

**Step 4: Total debt value of operating leases:**

```
Debt_Value_of_Operating_Leases = 
    Present_Value_of_Lease_Years_1_to_5 
  + Present_Value_of_Beyond_Year_Five_Commitments
```

**Step 5: Derive depreciation and adjustments.**

```
Total_Lease_Years = 5 + Number_of_Additional_Years_Beyond_Five

Straight_Line_Depreciation_on_Lease_Asset = 
    Debt_Value_of_Operating_Leases / Total_Lease_Years

Adjustment_to_Operating_Income_from_Leases = 
    Operating_Lease_Expense_Current_Year 
  - Straight_Line_Depreciation_on_Lease_Asset

Adjustment_to_Book_Debt_from_Leases = Debt_Value_of_Operating_Leases
```

**Reasoning:**
- The operating lease expense already on the income statement includes both (a) an economic interest component on the lease-debt and (b) an economic depreciation component on the lease-asset. We separate them.
- Adding back the full lease expense and subtracting only the depreciation portion leaves behind the implicit interest — which correctly raises EBIT (because interest expense is below-the-line in a proper capitalized treatment).
- Total debt increases by the full PV of the lease obligation.

**Step 6: Apply adjustments.**

```
Adjusted_Operating_Income (second pass) = 
    Adjusted_Operating_Income (from Stage 2a) 
  + Adjustment_to_Operating_Income_from_Leases

Adjusted_Book_Value_of_Debt = 
    Reported_Book_Value_of_Debt 
  + Adjustment_to_Book_Debt_from_Leases
```

### Outputs of Stage 2

- Adjusted_Operating_Income
- Adjusted_Book_Value_of_Equity
- Adjusted_Book_Value_of_Debt
- Value_of_Research_Asset (for invested capital calculation in Stage 5)
- Total_Amortization_of_Research_Asset_This_Year (for reinvestment in Stage 5)

---

## Stage 3 — Cost of Capital Construction

### Purpose

Compute the Weighted_Average_Cost_of_Capital — the discount rate that reflects the blended risk borne by the firm's capital providers (equity, debt, preferred stock). This is the single most influential number in the valuation; a 1% error in cost of capital shifts per-share value by 10-20%.

### Inputs required

- Risk_Free_Rate (from macro data)
- Country_Equity_Risk_Premium (for each country of operation)
- Industry_Unlevered_Beta (from Damodaran data by industry)
- Revenue_by_Country (for multi-country ERP blending)
- Revenue_by_Business_Segment (for multi-business unlevered beta blending)
- Adjusted_Book_Value_of_Debt
- Interest_Expense_Last_Twelve_Months
- Weighted_Average_Debt_Maturity_in_Years (typically 3–10; from 10-K debt schedule)
- Credit_Rating (if actual), or compute synthetic
- Market_Value_of_Equity (shares × price)
- Number_of_Preferred_Shares, Preferred_Dividend_per_Share, Preferred_Price_per_Share (if any)
- Marginal_Tax_Rate

### 3a. Unlevered Beta

#### Financial reasoning

Beta measures a firm's sensitivity to systematic market risk. Measuring it from a regression of the firm's own stock returns against the market is noisy (standard errors often ±0.4). Damodaran's preferred approach: use the industry-average beta, measured across dozens of firms, then unlevered to strip out capital-structure effects. This gives a stable estimate.

#### Four variants

**Variant 1: Single Business (US industry classification)**
```
Unlevered_Beta = VLOOKUP(
    US_Industry_Classification, 
    Damodaran_Industry_Averages_US_Table
)
```

**Variant 2: Multi-Business (US industries)**

When a firm operates in multiple distinct industries (for example, a conglomerate with semiconductor + automotive + industrial segments), compute a revenue-weighted unlevered beta, but weight by *enterprise value*, not revenue, because higher-multiple businesses contribute more to the firm's risk profile.

For each business segment i:
```
Revenue_of_Segment_i = reported segment revenue
EV_to_Sales_Multiple_of_Segment_i = industry multiple for segment i's industry
Estimated_Enterprise_Value_of_Segment_i = 
    Revenue_of_Segment_i × EV_to_Sales_Multiple_of_Segment_i
Unlevered_Beta_of_Segment_i = 
    Damodaran industry unlevered beta for segment i's industry
```

Then:
```
Total_Estimated_Enterprise_Value = Σ Estimated_Enterprise_Value_of_Segment_i
Weight_of_Segment_i = Estimated_Enterprise_Value_of_Segment_i / Total_Estimated_Enterprise_Value
Unlevered_Beta = Σ (Weight_of_Segment_i × Unlevered_Beta_of_Segment_i)
```

**Variant 3: Single or Multi-Business (Global industries)** — same as variants 1 and 2 but using the global industry tables.

**Variant 4: Direct Regression Input** — if the analyst prefers their own estimate, input directly. Least preferred due to noise.

### 3b. Equity Risk Premium

#### Financial reasoning

Equity Risk Premium is the extra return equity investors demand over the risk-free rate for bearing equity risk. It varies by country because country risk varies. Firms operating in multiple countries have a blended ERP weighted by where they earn revenue.

#### Three variants

**Variant 1: Country of Incorporation**
```
Equity_Risk_Premium = VLOOKUP(
    Country_of_Incorporation, 
    Damodaran_Country_ERP_Table
)
```

**Variant 2: Operating Countries (revenue-weighted)**

For each country where the firm earns revenue:
```
Revenue_in_Country_i = reported segment revenue for that country
Country_ERP_i = ERP lookup for country i
Weight_of_Country_i = Revenue_in_Country_i / Total_Revenue
Weighted_ERP_Contribution_i = Weight_of_Country_i × Country_ERP_i
```

Then:
```
Equity_Risk_Premium = Σ Weighted_ERP_Contribution_i
```

**Variant 3: Operating Regions** — same but aggregated to Damodaran region groupings (Developed Europe, Emerging Asia, etc.).

#### Generic applicability

Use Variant 1 for single-country firms. Use Variant 2 for multi-nationals. Variant 3 when country-level data is unavailable or too granular.

### 3c. Pre-Tax Cost of Debt

#### Financial reasoning

Cost_of_Debt is the yield a creditor demands to lend to this firm. It is a function of (a) the risk-free rate in the firm's reporting currency and (b) the default spread, which reflects the firm's credit quality.

#### Three variants

**Variant 1: Actual Credit Rating**
```
Default_Spread = VLOOKUP(Credit_Rating, Rating_to_Spread_Table)
Pre_Tax_Cost_of_Debt = Risk_Free_Rate + Default_Spread
```

For firms headquartered in risky countries, additionally add the country default spread:
```
Pre_Tax_Cost_of_Debt = Risk_Free_Rate + Default_Spread + Country_Default_Spread
```

**Variant 2: Synthetic Rating (for unrated firms)**
```
Interest_Coverage_Ratio = Adjusted_Operating_Income / Interest_Expense_Last_Twelve_Months

Synthetic_Rating = VLOOKUP(Interest_Coverage_Ratio, Coverage_to_Rating_Table)
    (use small-firm table if Market_Value_of_Equity < $5B, else large-firm table)

Default_Spread = VLOOKUP(Synthetic_Rating, Rating_to_Spread_Table)
Pre_Tax_Cost_of_Debt = Risk_Free_Rate + Default_Spread
```

**Variant 3: Direct Input** — analyst provides a number directly.

#### Reasoning

The synthetic rating approach creates a feedback loop: Operating_Income affects Interest_Coverage_Ratio → Synthetic_Rating → Pre_Tax_Cost_of_Debt → Weighted_Average_Cost_of_Capital → firm value. If we solve this loop self-consistently, the valuation remains coherent under changes to any operating input. Most real implementations iterate to convergence.

### 3d. Market Value of Debt (Bond Pricing Approach)

#### Financial reasoning

Weights in the Weighted_Average_Cost_of_Capital must reflect current market values, not book values. Book Debt may be stale (issued when rates were different); re-price it as if it were a single coupon bond.

#### Calculation

Treat the entire book debt as a coupon bond with:
- Face value = Book_Value_of_Debt
- Coupon = Interest_Expense_Last_Twelve_Months
- Yield to maturity = Pre_Tax_Cost_of_Debt
- Time to maturity = Weighted_Average_Debt_Maturity_in_Years

```
Market_Value_of_Debt = 
    Interest_Expense_Last_Twelve_Months 
    × [1 - (1 + Pre_Tax_Cost_of_Debt)^(-Weighted_Average_Debt_Maturity_in_Years)] 
    / Pre_Tax_Cost_of_Debt
  + Book_Value_of_Debt 
    / (1 + Pre_Tax_Cost_of_Debt)^Weighted_Average_Debt_Maturity_in_Years
```

The first term is the present value of the coupon stream (annuity). The second is the present value of the principal (single payment).

If the firm has operating leases, add:
```
Market_Value_of_Debt += Debt_Value_of_Operating_Leases
```

### 3e. Market Value of Equity

```
Market_Value_of_Equity = Primary_Shares_Outstanding × Current_Stock_Price
```

Simple and direct. No book value adjustment.

### 3f. Market Value of Preferred Stock (if applicable)

```
Market_Value_of_Preferred = Number_of_Preferred_Shares × Preferred_Price_per_Share
Preferred_Dividend_Yield = Preferred_Dividend_per_Share / Preferred_Price_per_Share
```

### 3g. Weights

```
Total_Market_Value_of_Capital = 
    Market_Value_of_Equity 
  + Market_Value_of_Debt 
  + Market_Value_of_Preferred

Weight_of_Equity = Market_Value_of_Equity / Total_Market_Value_of_Capital
Weight_of_Debt = Market_Value_of_Debt / Total_Market_Value_of_Capital
Weight_of_Preferred = Market_Value_of_Preferred / Total_Market_Value_of_Capital
```

### 3h. Levered Beta

```
Debt_to_Equity_Ratio_at_Market = Market_Value_of_Debt / Market_Value_of_Equity

Levered_Beta = 
    Unlevered_Beta 
    × (1 + (1 - Marginal_Tax_Rate) × Debt_to_Equity_Ratio_at_Market)
```

**Reasoning:** Leverage amplifies systematic risk. A debt-heavy firm's equity beta is higher than the underlying business beta. The `(1 - Marginal_Tax_Rate)` factor accounts for the tax shield on interest, which partially offsets leverage risk.

### 3i. Cost of Equity

```
Cost_of_Equity = 
    Risk_Free_Rate 
  + Levered_Beta × Equity_Risk_Premium
```

This is the Capital Asset Pricing Model. It assumes investors hold diversified portfolios and are compensated only for systematic (non-diversifiable) risk.

### 3j. After-Tax Cost of Debt

```
After_Tax_Cost_of_Debt = Pre_Tax_Cost_of_Debt × (1 - Marginal_Tax_Rate)
```

**Reasoning:** Interest is tax-deductible, so the true economic cost to the firm is the pre-tax rate reduced by the tax shield.

### 3k. Weighted Average Cost of Capital

```
Weighted_Average_Cost_of_Capital = 
    Weight_of_Equity × Cost_of_Equity 
  + Weight_of_Debt × After_Tax_Cost_of_Debt 
  + Weight_of_Preferred × Preferred_Dividend_Yield
```

This is the blended discount rate. It represents the opportunity cost of the firm's capital — the return the firm must earn on its assets to satisfy all capital providers.

### Alternate approaches (when detailed data is unavailable)

**Approach 2: Industry Average WACC, adjusted for risk-free differential**
```
Weighted_Average_Cost_of_Capital = 
    Industry_Average_WACC 
  + (Current_Risk_Free_Rate - Industry_Base_Risk_Free_Rate)
```

**Approach 3: Regional Decile/Quartile Lookup**
```
Weighted_Average_Cost_of_Capital = lookup(
    Region, 
    Risk_Grouping (First Decile | First Quartile | Median | Third Quartile | Ninth Decile)
)
```

Used when the firm is too small or too unusual for detailed calculation.

---

## Stage 4 — Story Calibration (User Assumptions)

### Purpose

Specify the company's forward narrative in numerical form. Every input in this stage tells part of the story: "How fast will revenue grow? How profitable will it become? How efficiently will it reinvest? How will it end?"

### Inputs — Growth and Profitability Story

| Variable | Default | Story told |
|---|---|---|
| Revenue_Growth_Rate_Next_Year | user input | "Top line in year 1" |
| Revenue_Growth_Rate_Years_2_to_5 | = Next_Year by default | "Growth sustains through high-growth period" |
| Target_Pre_Tax_Operating_Margin | user input | "Margin at maturity" |
| Year_of_Convergence_for_Margin | 5 | "Pace of margin change" |
| Sales_to_Capital_Ratio_Years_1_to_5 | user input (or industry avg) | "Capital efficiency in growth phase" |
| Sales_to_Capital_Ratio_Years_6_to_10 | user input | "Capital efficiency as firm matures" |

### Inputs — Terminal Period Overrides (Optional)

| Variable | Default | Override if... |
|---|---|---|
| Terminal_Weighted_Average_Cost_of_Capital | = industry_WACC_after_year_10 | Company risk profile differs from industry at maturity |
| Terminal_Return_on_Invested_Capital | = Terminal_WACC (no excess returns assumption) | Company has durable competitive moat |
| Probability_of_Failure | 0 | Young or distressed company |
| Distress_Proceeds_Percentage | 0.5 | Recovery rate if firm fails |
| Failure_Tie_To | "V" (fair value) | Could be "B" for book value |
| Reinvestment_Lag_in_Years | 1 (standard) | Long capital cycle industries (semis = 3; real estate = 5) |
| Override_Tax_Rate_Convergence | No (converges to marginal) | Tax-advantaged structure persists |
| Net_Operating_Loss_Carryforward_Amount | 0 | Company has unused past losses |
| Override_Risk_Free_Rate_After_Year_10 | No | Expect rate regime change |
| Override_Perpetuity_Growth_Rate | No (uses risk-free) | Specific terminal growth thesis |
| Trapped_Cash_Amount | 0 | Material foreign cash subject to repatriation tax |
| Foreign_Tax_Rate_on_Trapped_Cash | 0 | Same |

### Reasoning

Each assumption pair creates a "lever" in the story:
- **Growth lever** (Revenue_Growth_Rate) — the top-line story
- **Profitability lever** (Target_Pre_Tax_Operating_Margin) — the competitive story
- **Speed of convergence** (Year_of_Convergence_for_Margin) — the speed-of-maturity story
- **Efficiency lever** (Sales_to_Capital_Ratio) — the capital-productivity story

No assumption is "right" or "wrong" in isolation. They must cohere: a firm claiming 30% revenue growth for 5 years cannot simultaneously claim a Sales-to-Capital of 0.5 (that implies growing assets 60% per year — industrially absurd).

---

## Stage 5 — Ten-Year Explicit Projection

### Purpose

Project, year by year, the cash generated by the business over the next 10 years. This is the "guts" of the DCF. Years 1–5 are the high-growth period (inputs hold constant). Years 6–10 are the transition period (inputs linearly converge from high-growth values to terminal values).

### 5a. Revenue Path

For each year t from 1 to 10:

```
Revenue_Growth_Rate_Year_t:
    If t ≤ 5:             Revenue_Growth_Rate_Next_Year (constant in high-growth period)
    If 5 < t ≤ 10:        Revenue_Growth_Rate_Year_5 
                          - (Revenue_Growth_Rate_Year_5 - Terminal_Growth_Rate) 
                          × (t - 5) / 5
                          (linear convergence)

Revenue_Year_t = Revenue_Year_{t-1} × (1 + Revenue_Growth_Rate_Year_t)
```

Where:
```
Terminal_Growth_Rate:
    If Override_Perpetuity_Growth_Rate = Yes: user value
    Else if Override_Risk_Free_Rate_After_Year_10 = Yes: new risk-free rate
    Else: Current_Risk_Free_Rate
```

**Reasoning for terminal growth capped at risk-free:** In perpetuity, no firm can grow faster than the economy — otherwise it would eventually be larger than the economy. Empirically, the risk-free rate (long-term government yield) approximates long-term nominal GDP growth.

### 5b. Operating Margin Path

For each year t:

```
Operating_Margin_Year_t:
    If t ≤ Year_of_Convergence_for_Margin:
        Target_Pre_Tax_Operating_Margin 
      - (Target_Pre_Tax_Operating_Margin - Year_1_Operating_Margin) 
        × (Year_of_Convergence_for_Margin - t) 
        / Year_of_Convergence_for_Margin
    Else:
        Target_Pre_Tax_Operating_Margin
```

**Reasoning:** Margin drifts linearly from year 1 to target over K years, then stays at target.

### 5c. Operating Income Path

```
Operating_Income_Year_t = Revenue_Year_t × Operating_Margin_Year_t
```

### 5d. Tax Rate Path

```
Tax_Rate_Year_t:
    If t ≤ 5:             Effective_Tax_Rate (flat)
    If 5 < t ≤ 10:        Tax_Rate_Year_{t-1} + (Marginal_Tax_Rate - Effective_Tax_Rate) / 5
    Terminal:             Marginal_Tax_Rate (unless Override_Tax_Rate_Convergence = Yes, then stay at Effective)
```

**Reasoning:** The current effective tax rate reflects tax optimization (R&D credits, foreign IP holding cos, depreciation shields). These erode as the firm matures and as tax law tightens. By year 10, assume the statutory marginal rate applies.

### 5e. Net Operating Loss Carryforward (Dynamic Tracking)

For each year t:

```
NOL_Start_Year_t = NOL_End_Year_{t-1}

NOL_Consumed_Year_t = MIN(NOL_Start_Year_t, MAX(0, Operating_Income_Year_t))

NOL_End_Year_t:
    If Operating_Income_Year_t < 0:
        NOL_Start_Year_t - Operating_Income_Year_t (grows by the loss)
    Else:
        NOL_Start_Year_t - NOL_Consumed_Year_t (depletes)

Taxable_Income_Year_t = MAX(0, Operating_Income_Year_t - NOL_Start_Year_t)
```

**Reasoning:** NOLs shield income from tax until exhausted. Critical for young firms with past losses (Uber, early Tesla).

### 5f. After-Tax Operating Income

```
After_Tax_Operating_Income_Year_t:
    If Operating_Income_Year_t > 0:
        Operating_Income_Year_t - (Taxable_Income_Year_t × Tax_Rate_Year_t)
    Else:
        Operating_Income_Year_t (loss — no tax to pay)
```

### 5g. Reinvestment (Sales-to-Capital with Lag)

**Core formula (no lag):**
```
Reinvestment_Year_t = 
    (Revenue_Year_{t+1} - Revenue_Year_t) 
    / Sales_to_Capital_Ratio_Year_t
```

**With lag = k years:**
```
Reinvestment_Year_t = 
    (Revenue_Year_{t+k+1} - Revenue_Year_{t+k}) 
    / Sales_to_Capital_Ratio_Year_t
```

**Reasoning:** The Sales-to-Capital approach treats revenue growth as a function of capital invested: each $1 of new capital produces $(1 / Sales_to_Capital_Ratio) of new revenue. The lag captures industries where capital today produces revenue years later (semiconductor fabs: 3-year lag; oil discoveries: 5+ year lag; software: 0-year lag).

### 5h. Free Cash Flow to Firm

```
Free_Cash_Flow_to_Firm_Year_t = 
    After_Tax_Operating_Income_Year_t 
  - Reinvestment_Year_t
```

**Reasoning:** This is the cash generated by operations, after taxes, after funding the reinvestment needed to sustain the projected growth. It is available to all capital providers (equity, debt, preferred).

### 5i. Cost of Capital Path

```
Weighted_Average_Cost_of_Capital_Year_t:
    If t ≤ 5:             Initial_Weighted_Average_Cost_of_Capital (from Stage 3)
    If 5 < t ≤ 10:        Initial_WACC 
                         - (Initial_WACC - Terminal_WACC) × (t - 5) / 5
                          (linear convergence)
```

Where:
```
Terminal_Weighted_Average_Cost_of_Capital:
    If Override_Terminal_WACC = Yes: user value
    Else if Override_Risk_Free_Rate = Yes: 
        new_Risk_Free_Rate + US_Mature_Market_ERP
    Else: Initial_Weighted_Average_Cost_of_Capital
```

**Reasoning:** As a firm matures, its risk profile converges to the industry/market average. A high-beta growth firm at year 1 becomes a more stable firm at year 10, with lower beta and lower cost of capital.

### 5j. Invested Capital Path (for ROIC tracking)

```
Invested_Capital_Base_Year = 
    Adjusted_Book_Value_of_Equity 
  + Adjusted_Book_Value_of_Debt 
  - Cash_and_Marketable_Securities

For each year t:
    Invested_Capital_Year_t = Invested_Capital_Year_{t-1} + Reinvestment_Year_t

Return_on_Invested_Capital_Year_t = 
    After_Tax_Operating_Income_Year_t 
    / Invested_Capital_Year_{t-1}
```

**Reasoning:** Tracking Return_on_Invested_Capital over time tells whether the firm is earning excess returns (ROIC > WACC) and by how much. Terminal ROIC determines terminal reinvestment rate.

---

## Stage 6 — Terminal Value

### Purpose

Capture the value of all Free_Cash_Flow_to_Firm beyond year 10 in a single number. This is typically 50–75% of total firm value, so it's not a "tail" — it's the bulk of the valuation.

### Calculation

**Step 1: Terminal year (year 11) cash flow.**

```
Revenue_Terminal_Year = Revenue_Year_10 × (1 + Terminal_Growth_Rate)
Operating_Income_Terminal_Year = Revenue_Terminal_Year × Target_Pre_Tax_Operating_Margin
Tax_Rate_Terminal = Marginal_Tax_Rate (unless override keeps effective)
After_Tax_Operating_Income_Terminal = Operating_Income_Terminal_Year × (1 - Tax_Rate_Terminal)
```

**Step 2: Terminal reinvestment rate.**

```
Terminal_Reinvestment_Rate = Terminal_Growth_Rate / Terminal_Return_on_Invested_Capital
```

**Reasoning:** In stable growth, to grow at g the firm must plow back (g / ROIC) of its earnings. For example: to grow 4% with 20% ROIC, reinvest 4/20 = 20% of earnings; 80% flows out as FCFF. If ROIC = WACC (no excess returns), reinvestment rate = g / WACC.

**Step 3: Terminal Free Cash Flow to Firm.**

```
Free_Cash_Flow_to_Firm_Terminal = 
    After_Tax_Operating_Income_Terminal × (1 - Terminal_Reinvestment_Rate)
```

**Step 4: Terminal Value (Gordon Growth Formula).**

```
Terminal_Value = 
    Free_Cash_Flow_to_Firm_Terminal 
    / (Terminal_Weighted_Average_Cost_of_Capital - Terminal_Growth_Rate)
```

**Reasoning:** The Gordon formula prices a perpetual growing cash flow. It requires Terminal_WACC > Terminal_Growth_Rate, otherwise value is infinite (or negative). The constraint `Terminal_Growth_Rate ≤ Risk_Free_Rate` ensures this always holds.

### Outputs

- Terminal_Value (a single number, conceptually sitting at end of year 10)

---

## Stage 7 — Discounting to Present Value

### Purpose

Translate future Free_Cash_Flow_to_Firm and Terminal_Value into today's dollars using the cost-of-capital path.

### 7a. Cumulative Discount Factors

```
For each year t from 1 to 10:
    Cumulative_Discount_Factor_Year_t = 
        Cumulative_Discount_Factor_Year_{t-1} × 1 / (1 + WACC_Year_t)
        (where Cumulative_Discount_Factor_Year_0 = 1)
```

**Reasoning:** Year-by-year multiplication is necessary because WACC changes over time. A single compounded factor would be wrong.

### 7b. Present Value of Each Year's FCFF

```
Present_Value_of_FCFF_Year_t = 
    Free_Cash_Flow_to_Firm_Year_t × Cumulative_Discount_Factor_Year_t
```

### 7c. Present Value of Terminal Value

```
Present_Value_of_Terminal_Value = 
    Terminal_Value × Cumulative_Discount_Factor_Year_10
```

### 7d. Value of Operating Business (Going Concern)

```
Value_as_Going_Concern = 
    Σ Present_Value_of_FCFF_Year_t (for t = 1 to 10) 
  + Present_Value_of_Terminal_Value
```

**Reasoning:** This is the intrinsic value of the firm's operating assets, assuming it continues as a going concern indefinitely.

---

## Stage 8 — Failure Probability Overlay

### Purpose

Adjust the going-concern value for the possibility that the firm fails (bankruptcy, liquidation). Essential for young, small, or distressed companies. Optional for mature blue-chips.

### Inputs required

- Probability_of_Failure (user-provided or derived from age + rating)
- Distress_Proceeds_Percentage (typical recovery rate 30–70%)
- Failure_Tie_To ("B" for book value, "V" for fair/going-concern value)
- Adjusted_Book_Value_of_Equity + Adjusted_Book_Value_of_Debt (if tied to book)

### Calculation

```
If Failure_Tie_To = "B":
    Distress_Value = 
        (Adjusted_Book_Value_of_Equity + Adjusted_Book_Value_of_Debt) 
        × Distress_Proceeds_Percentage

Else (Failure_Tie_To = "V"):
    Distress_Value = Value_as_Going_Concern × Distress_Proceeds_Percentage

Value_of_Operating_Assets = 
    Value_as_Going_Concern × (1 - Probability_of_Failure) 
  + Distress_Value × Probability_of_Failure
```

**Reasoning:** This is an expected-value calculation over two scenarios: survival (with full going-concern value) and failure (with fire-sale recovery). Even a small probability of failure can materially lower value for leveraged or distressed firms.

### Outputs

- Value_of_Operating_Assets

### Generic applicability

Probability_of_Failure can be estimated from:
- Bond rating (failure probability by rating and time horizon from default tables)
- Corporate age (failure rate by age from Bureau of Labor Statistics sector data)
- Interest coverage and leverage (qualitative)

---

## Stage 9 — Equity Value Bridge

### Purpose

Move from firm value (what the business is worth) to common equity value (what the common shareholders own).

### Calculation

```
Value_of_Operating_Assets             [from Stage 8]
- Adjusted_Book_Value_of_Debt         (includes lease-debt from Stage 2b)
- Minority_Interests                  (non-controlling interests' claim)
+ Cash_and_Marketable_Securities      (with trapped cash adjustment if applicable)
+ Cross_Holdings_and_Non_Operating_Assets
= Value_of_Equity_Before_Options
```

### Trapped Cash Adjustment (if applicable)

When material cash is held abroad and would owe repatriation tax:

```
If Override_Trapped_Cash = Yes:
    Usable_Cash = 
        Cash_and_Marketable_Securities 
      - Trapped_Cash_Amount × (Marginal_Tax_Rate - Foreign_Tax_Rate_on_Trapped_Cash)
Else:
    Usable_Cash = Cash_and_Marketable_Securities
```

### Employee Stock Options (Dilution-Adjusted Black-Scholes)

If the firm has material employee options, compute their dilution-adjusted value and subtract.

**Iterative fixed-point solution required** — the option value depends on the diluted stock price, which depends on the option value.

**Step 1: Initial estimate.**
```
Stock_Price_Pre_Dilution = Current_Stock_Price (from market)
Call_Value_Initial_Guess = max(0, Stock_Price_Pre_Dilution - Weighted_Average_Strike_Price)
```

**Step 2: Dilution-adjusted stock price.**
```
Dilution_Adjusted_Stock_Price = 
    (Stock_Price_Pre_Dilution × Primary_Shares_Outstanding 
   + Call_Value × Number_of_Options_Outstanding) 
    / (Primary_Shares_Outstanding + Number_of_Options_Outstanding)
```

**Step 3: Black-Scholes with dilution-adjusted price.**
```
d1 = [ln(Dilution_Adjusted_Stock_Price / Weighted_Average_Strike_Price) 
       + (Risk_Free_Rate - Dividend_Yield + Variance/2) 
         × Weighted_Average_Remaining_Life_in_Years]
     / (Standard_Deviation × sqrt(Weighted_Average_Remaining_Life_in_Years))

d2 = d1 - Standard_Deviation × sqrt(Weighted_Average_Remaining_Life_in_Years)

Call_Value = 
    Dilution_Adjusted_Stock_Price × e^(-Dividend_Yield × Time) × Normal_CDF(d1) 
  - Weighted_Average_Strike_Price × e^(-Risk_Free_Rate × Time) × Normal_CDF(d2)
```

**Step 4: Iterate until Call_Value stabilizes.**

**Step 5: Compute total option value.**
```
Value_of_All_Employee_Options = Call_Value × Number_of_Options_Outstanding
```

### Final equity bridge

```
Value_of_Equity_in_Common_Stock = 
    Value_of_Equity_Before_Options - Value_of_All_Employee_Options
```

---

## Stage 10 — Per-Share Value and Market Verdict

### Calculation

```
Intrinsic_Value_per_Share = 
    Value_of_Equity_in_Common_Stock / Primary_Shares_Outstanding

Market_to_Intrinsic_Ratio = Current_Stock_Price / Intrinsic_Value_per_Share
```

### Interpretation

```
If Market_to_Intrinsic_Ratio > 1.20:        Stock is significantly overvalued
If 1.00 ≤ Market_to_Intrinsic_Ratio ≤ 1.20: Stock is modestly overvalued
If 0.80 ≤ Market_to_Intrinsic_Ratio < 1.00: Stock is modestly undervalued
If Market_to_Intrinsic_Ratio < 0.80:        Stock is significantly undervalued
```

**Caveat:** Intrinsic valuation is an opinion. A 20% gap may reflect the analyst's story being wrong, not the market. Re-examine assumptions before declaring market mispricing.

---

## 13. Feedback Loops and Iterative Solutions

Three interlocking circular references prevent a one-pass calculation. Any serious implementation must iterate.

### Loop 1: Cost of Capital ↔ Firm Value

- Weighted_Average_Cost_of_Capital weights depend on Market_Value_of_Equity.
- Market_Value_of_Equity is observed from the market — but if the analyst's view of intrinsic value differs materially from market, there is an inconsistency.
- In Damodaran's workbook, market equity is used for WACC weights (accepting the inconsistency). In more rigorous implementations, iterate: use intrinsic equity to re-weight WACC, re-value, iterate until fixed point.

### Loop 2: Synthetic Rating ↔ Cost of Debt ↔ Operating Income

- If using synthetic rating: Operating_Income drives Interest_Coverage_Ratio drives Synthetic_Rating drives Default_Spread drives Pre_Tax_Cost_of_Debt drives Weighted_Average_Cost_of_Capital drives firm value.
- Firm value does not circle back to Operating_Income in this valuation framework — so this loop is only one-way from operations to WACC. But if the analyst revises their Operating_Income assumption, Kd must be re-derived.

### Loop 3: Option Dilution ↔ Equity Value per Share

- Call_Value depends on Dilution_Adjusted_Stock_Price.
- Dilution_Adjusted_Stock_Price depends on Call_Value.
- Solve by fixed-point iteration (5–10 iterations typically converge).

### Implementation guidance

- Iterate until all three loops converge to within 0.01% tolerance.
- In Excel, enable iterative calculations (Preferences > Formulas > Iterative).
- In Python, use a fixed-point solver (e.g., scipy.optimize.fixed_point).

---

## 14. Dependency Graph

```
                  [Stage 1: LTM Normalization]
                            │
                            ▼
                  [Stage 2: Adjustments]
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
        [Stage 3a:      [Stage 3c:    [Stage 2b:
        Unlevered     Cost of Debt     Lease Debt]
        Beta]         inc. Synthetic]      │
                            │               │
                            └────────┐ ┌────┘
                                     ▼ ▼
                     [Stage 3d: Market Value of Debt]
                            │
                     [Stage 3e: Market Value Equity]
                            │
                     [Stage 3h-k: Levered Beta, WACC]
                            │
                            ▼
                     [Stage 4: Story Calibration]
                            │
                            ▼
                     [Stage 5: 10-Year Projection]
                            │
                            ▼
                     [Stage 6: Terminal Value]
                            │
                            ▼
                     [Stage 7: Discount to PV]
                            │
                            ▼
                     [Stage 8: Failure Overlay]
                            │
                            ▼
                     [Stage 9: Equity Bridge]
                            │
                            ▼
                     [Stage 10: Per-Share Value]
```

---

## 15. Diagnostic Sanity Checks

After completing the valuation, verify these invariants. Failures indicate either data errors or inconsistent assumptions.

### Input coherence

- [ ] `Revenue_Growth_Rate_Next_Year ≤ 1.0` (no firm sustainably grows >100% per year over 5 years)
- [ ] `Target_Pre_Tax_Operating_Margin ≤ historical_industry_maximum_margin` (firm cannot exceed best-in-class in perpetuity without a clear competitive advantage story)
- [ ] `Sales_to_Capital_Ratio × Revenue_Growth_Rate < Target_ROIC` (reinvestment implied must be < earnings; otherwise the story is self-contradictory)

### Stage output coherence

- [ ] `After_Tax_Cost_of_Debt < Weighted_Average_Cost_of_Capital < Cost_of_Equity` (WACC must be between its components; otherwise weights or costs are wrong)
- [ ] `Terminal_Growth_Rate ≤ Risk_Free_Rate` (mathematical requirement for Gordon formula)
- [ ] `Terminal_Return_on_Invested_Capital ≥ Terminal_Weighted_Average_Cost_of_Capital` (if firm is creating any excess returns; else excess return = 0 assumption)
- [ ] `Value_of_Operating_Assets > 0` (if negative, assumptions collapse the firm)
- [ ] `Present_Value_of_Terminal_Value / Value_as_Going_Concern` ∈ [0.4, 0.85] typically (outside this range, high-growth period is unrealistically long or short)

### Implied metrics

- [ ] `Implied_Return_on_Invested_Capital_Year_t = Expected_Revenue_Growth_Year_t / Sales_to_Capital_Ratio_Year_t × Operating_Margin_Year_t × (1 - Tax_Rate_Year_t)` — should roughly track the projected After_Tax_Operating_Income / Invested_Capital path

### Narrative coherence

- [ ] Does the story (15% growth + 60% margin + 2.5 S/C + 20% ROIC) make sense for this industry?
- [ ] Are the story's drivers consistent (high margin usually requires competitive moat; moat usually implies low S/C; low S/C implies high ROIC)?
- [ ] Does the valuation explain, rather than just produce, a number?

---

## 16. Generic Application Checklist

To apply this framework to any publicly traded company, execute the following checklist:

1. **Identify the company.** Ticker, country, industry (US + Global).
2. **Collect base-year data** (Prerequisites section above). Pull 10-K + most recent 10-Q; compute LTM for all flow items.
3. **Execute Stage 1**: produce Last_Twelve_Months values for all flow items; copy 10-Q values for all balance sheet items.
4. **Execute Stage 2a**: if R&D is material, capitalize. Otherwise skip.
5. **Execute Stage 2b**: if off-balance-sheet leases are material, capitalize. Otherwise skip.
6. **Execute Stage 3a**: look up industry unlevered beta (choose single or multi-business).
7. **Execute Stage 3b**: compute ERP (country of incorporation or operating-country weighted).
8. **Execute Stage 3c**: compute Pre_Tax_Cost_of_Debt (actual rating, synthetic, or direct).
9. **Execute Stage 3d**: price debt at market.
10. **Execute Stage 3e–k**: compute market-weighted WACC.
11. **Execute Stage 4**: specify the growth story (all input assumptions).
12. **Execute Stage 5**: generate the 10-year projection with all paths.
13. **Execute Stage 6**: compute Terminal Value.
14. **Execute Stage 7**: discount all future flows to PV.
15. **Execute Stage 8**: apply failure overlay (use Probability_of_Failure = 0 for mature blue-chips).
16. **Execute Stage 9**: bridge firm value to equity value, subtract options.
17. **Execute Stage 10**: divide by shares, compare to market price.
18. **Execute diagnostics** (Section 15): verify all invariants.
19. **If iterations required** (Synthetic Rating, Option Dilution, Equity-Weighting): iterate to convergence.
20. **Produce narrative**: write a 1-page summary tying the inputs to the valuation conclusion.

---

## 17. Glossary of Variable Names

Preferred convention: snake_case_with_full_financial_name.

| Full name | Common abbreviation | Definition |
|---|---|---|
| Adjusted_Book_Value_of_Debt | BV_D_adj | Book Debt + PV of Operating Leases |
| Adjusted_Book_Value_of_Equity | BV_E_adj | Book Equity + Value of Research Asset |
| Adjusted_Operating_Income | EBIT_adj | EBIT + R&D add-back – R&D amortization + Lease adj |
| After_Tax_Cost_of_Debt | Kd_after_tax | Pre_Tax_Cost_of_Debt × (1 – Marginal_Tax_Rate) |
| After_Tax_Operating_Income | EBIT(1-t) | Operating_Income × (1 – Tax_Rate) |
| Amortization_Period_in_Years | N | Years over which R&D amortizes (3–10) |
| Annual_Interest_Expense | — | Interest paid per year |
| Annual_Annuity_Beyond_Year_Five | — | Implied annuity for post-year-5 lease commitments |
| Book_Value_of_Debt | BV_D | Reported debt on balance sheet |
| Book_Value_of_Equity | BV_E | Reported stockholders' equity |
| Cash_and_Marketable_Securities | Cash | Liquid assets |
| Call_Value_per_Option | C* | Black-Scholes value per option |
| Cost_of_Equity | Ke | Return equity holders demand (CAPM) |
| Country_Default_Spread | CDS | Extra spread for country credit risk |
| Country_Equity_Risk_Premium | CRP | Extra ERP for country-level risk |
| Cross_Holdings_and_Non_Operating_Assets | — | Stakes in other firms, real estate, etc. |
| Cumulative_Discount_Factor | — | Product of 1/(1+WACC) from year 1 to year t |
| Current_Stock_Price | P_0 | Market price today |
| Debt_to_Equity_Ratio_at_Market | D/E | MV_D / MV_E |
| Debt_Value_of_Operating_Leases | PV_Leases | PV of future lease commitments |
| Default_Spread | DS | Credit spread over risk-free |
| Dilution_Adjusted_Stock_Price | S* | Stock price after accounting for option dilution |
| Distress_Proceeds_Percentage | — | Recovery rate in bankruptcy |
| Effective_Tax_Rate | t_eff | Taxes paid / Pre-tax income |
| Equity_Risk_Premium | ERP | Extra return demanded over risk-free by equity |
| Free_Cash_Flow_to_Equity | FCFE | FCFF – After-tax interest + Net new debt |
| Free_Cash_Flow_to_Firm | FCFF | After_Tax_Operating_Income – Reinvestment |
| Industry_Unlevered_Beta | β_U (industry) | Average beta across industry firms, unlevered |
| Initial_Weighted_Average_Cost_of_Capital | WACC_initial | Current WACC (year 1) |
| Interest_Coverage_Ratio | — | EBIT / Interest_Expense |
| Intrinsic_Value_per_Share | — | Total equity value / shares |
| Invested_Capital | IC | Adjusted_BV_E + Adjusted_BV_D – Cash |
| Last_Twelve_Months_Value | LTM | Rolling 12-month flow from last 10-K + 10-Q adjustment |
| Levered_Beta | β_L | β_U × (1 + (1–t) × D/E) |
| Marginal_Tax_Rate | t_marg | Statutory corporate tax rate |
| Market_Value_of_Debt | MV_D | Book_Debt repriced at Pre_Tax_Cost_of_Debt |
| Market_Value_of_Equity | MV_E | Shares × Stock_Price |
| Market_Value_of_Preferred | MV_P | Preferred_Shares × Preferred_Price |
| Minority_Interests | — | Non-controlling interests |
| Net_Operating_Loss_Carryforward | NOL | Past accumulated losses that shield future income |
| Number_of_Options_Outstanding | — | Employee options not yet exercised |
| Operating_Income | EBIT | Revenue – Operating Expenses (before interest, tax) |
| Operating_Lease_Commitment_Year_t | — | Future contractual lease payment for year t |
| Operating_Margin_Year_t | — | Operating_Income_Year_t / Revenue_Year_t |
| Pre_Tax_Cost_of_Debt | Kd_pretax | Risk_Free + Default_Spread |
| Present_Value_of_Beyond_Year_Five_Commitments | — | PV of lease annuity for years 6+ |
| Present_Value_of_FCFF_Year_t | PV_FCFF_t | FCFF_t × Cumulative_Discount_Factor_t |
| Present_Value_of_Terminal_Value | PV_TV | Terminal_Value × Discount_Factor_Year_10 |
| Primary_Shares_Outstanding | Shares | Basic shares (not diluted) |
| Probability_of_Failure | p_fail | Probability firm goes bankrupt |
| Reinvestment_Lag_in_Years | — | Years between capital spend and revenue realization |
| Reinvestment_Rate | RIR | Reinvestment / After_Tax_Operating_Income |
| Research_and_Development_Expense | R&D | Annual R&D spend |
| Return_on_Invested_Capital | ROIC | EBIT(1-t) / Invested_Capital |
| Return_on_Equity | ROE | Net_Income / Book_Equity |
| Revenue | — | Top-line sales |
| Revenue_Growth_Rate_Year_t | — | (Rev_t – Rev_{t-1}) / Rev_{t-1} |
| Risk_Free_Rate | RF | 10-year government bond yield |
| Sales_to_Capital_Ratio | S/C | Revenue / Invested_Capital |
| Standard_Deviation_of_Stock_Returns | σ | Annualized volatility |
| Synthetic_Rating | — | Rating derived from interest coverage |
| Target_Pre_Tax_Operating_Margin | — | Terminal-period operating margin |
| Tax_Rate_Year_t | — | Effective tax rate applied in year t |
| Terminal_Growth_Rate | g | Perpetual growth after year 10 |
| Terminal_Return_on_Invested_Capital | ROIC_terminal | ROIC at maturity |
| Terminal_Value | TV | Value of all FCFF beyond year 10 |
| Terminal_Weighted_Average_Cost_of_Capital | WACC_terminal | WACC at maturity |
| Total_Estimated_Enterprise_Value | Total_EV | Σ (Segment_Revenue × EV/Sales) |
| Total_Market_Value_of_Capital | — | MV_E + MV_D + MV_P |
| Unamortized_Fraction_at_t | — | (N – t) / N |
| Unlevered_Beta | β_U | Business risk, without capital structure |
| Value_as_Going_Concern | — | PV of all future FCFF + TV (assuming no failure) |
| Value_of_All_Employee_Options | — | C* × Number_of_Options |
| Value_of_Equity_in_Common_Stock | — | Firm value – debt – MI + cash + non-op – options |
| Value_of_Operating_Assets | — | Value_as_Going_Concern adjusted for failure probability |
| Value_of_Research_Asset | — | Unamortized R&D capital (built up from past spending) |
| Weight_of_Equity, Weight_of_Debt, Weight_of_Preferred | w_E, w_D, w_P | Market-value weights in WACC |
| Weighted_Average_Cost_of_Capital | WACC | w_E × Ke + w_D × Kd_aftertax + w_P × Preferred_Yield |
| Weighted_Average_Debt_Maturity_in_Years | — | Duration of outstanding debt |
| Weighted_Average_Remaining_Life_in_Years | t_option | Average time to option expiration |
| Weighted_Average_Strike_Price | K | Average strike across outstanding options |
| Year_of_Convergence_for_Margin | K | Year by which target margin is reached |

---

*End of planning document. This document is complete for implementation by an engineer or analyst. All stages, inputs, formulas, and interpretations are specified. Use it as the canonical reference for any company valuation.*
