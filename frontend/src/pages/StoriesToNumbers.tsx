import type { ValuationResponse } from '../types/valuation';
import type { PatchValue } from '../api/client';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';
import { baseYear } from '../lib/baseYear';
import { requiredROIC, requiredSC } from '../lib/reverseChecks';
import ClosedLoopStrip from '../components/ClosedLoopStrip';
import StoryValidationBlock from '../components/StoryValidationBlock';
import TaxOverridePanel from '../components/TaxOverridePanel';
import SensitivityPanel from '../components/SensitivityPanel';
import HistoricalDetailTable from '../components/HistoricalDetailTable';

interface Props {
  data: ValuationResponse;
  sessionId?: string | null;
  onPatch?: (path: string, value: PatchValue) => void | Promise<void>;
  onPatchMany?: (overrides: Record<string, PatchValue>) => void | Promise<void>;
}

export default function StoriesToNumbers({ data, onPatch, onPatchMany }: Props) {
  const assumptions = data.inputs.valuation_assumptions;
  const industry = data.inputs.industry_data;
  const cf = data.cashflow;
  const fin = baseYear(data);

  // Industry stats — some fields carry quartile ranges on industry_data.
  // For the three-story blocks we need median, Q1, Q3 for each metric.
  // The current IndustryData shape only exposes single-value medians; if
  // the backend surfaces quartile stats elsewhere, wire them in here.
  // Falls back to median-only for Q1/Q3 if not available.
  const stats = data.industry_stats ?? null;
  const q = (k: 'revenue_growth_3y' | 'pretax_operating_margin' | 'sales_to_capital') =>
    stats?.[k] ?? null;

  const narrative: { narrative: string; driver: string; input: string; value: string | number | null; type: 'hypothesis' | 'calc' | 'reference' }[] = [
    {
      narrative: 'How fast will the company grow revenues?',
      driver: 'Revenue growth (next year)',
      input: 'revenue_growth_next_year',
      value: assumptions.revenue_growth_next_year,
      type: 'hypothesis',
    },
    {
      narrative: 'How fast will it grow after year 1?',
      driver: 'Revenue growth (years 2–5)',
      input: 'revenue_growth_years_2_5',
      value: assumptions.revenue_growth_years_2_5,
      type: 'hypothesis',
    },
    {
      narrative: 'How profitable will the company be at maturity?',
      driver: 'Target pre-tax operating margin',
      input: 'target_operating_margin',
      value: assumptions.target_operating_margin,
      type: 'hypothesis',
    },
    {
      narrative: 'How long until current margin reaches target?',
      driver: 'Margin convergence year (K)',
      input: 'margin_convergence_year',
      value: assumptions.margin_convergence_year,
      type: 'hypothesis',
    },
    {
      narrative: 'How efficiently will capital generate revenue?',
      driver: 'Sales/Capital (years 1–5)',
      input: 'sales_to_capital_high',
      value: assumptions.sales_to_capital_high,
      type: 'hypothesis',
    },
    {
      narrative: 'Reinvestment in the stable phase',
      driver: 'Sales/Capital (years 6–10)',
      input: 'sales_to_capital_stable',
      value: assumptions.sales_to_capital_stable,
      type: 'hypothesis',
    },
    {
      narrative: 'How risky is this company?',
      driver: 'Cost of capital (WACC)',
      input: 'wacc',
      value: data.cost_of_capital?.wacc ?? null,
      type: 'calc',
    },
    {
      narrative: 'What is the long-term growth rate?',
      driver: 'Terminal growth',
      input: 'stable_growth_rate',
      value: assumptions.stable_growth_rate ?? data.inputs.macro_inputs.risk_free_rate,
      type: 'hypothesis',
    },
    {
      narrative: 'Could this company fail?',
      driver: 'Probability of failure',
      input: 'failure_probability',
      value: assumptions.failure_probability,
      type: 'hypothesis',
    },
    {
      narrative: 'Current market price (reference)',
      driver: 'Current stock price',
      input: 'stock_price',
      value: fin?.stock_price ?? null,
      type: 'reference',
    },
  ];

  // Reverse-check values for the three story blocks
  const impliedROIC = requiredROIC(assumptions.target_operating_margin, assumptions.sales_to_capital_high);
  const roicAnchor = assumptions.roic_stable_override ?? cf?.historical_roic_avg_5yr ?? data.cost_of_capital?.wacc ?? null;
  const impliedSCReq = requiredSC(roicAnchor, assumptions.target_operating_margin);

  // Per-cell tooltip builders — surface the exact calculation for every
  // historical annual value, reading from raw_financials so the analyst
  // can cross-check each cell.
  const history = data.inputs.raw_financials ?? [];
  const fmtM = (v: number | null | undefined) =>
    v == null ? '—' : `${(v / 1000).toLocaleString('en-US', { maximumFractionDigits: 1 })}B`;
  const yearLabel = (i: number) => `FY-${i}`;

  const growthTooltip = (i: number): string => {
    const cur = history[i]?.revenues;
    const prev = history[i + 1]?.revenues;
    if (cur == null || prev == null) return `No data for ${yearLabel(i)} (revenue or prior-year revenue missing).`;
    const g = cur / prev - 1;
    return `${yearLabel(i)} revenue growth = (Rev[${yearLabel(i)}] − Rev[${yearLabel(i + 1)}]) / Rev[${yearLabel(i + 1)}]\n= (${fmtM(cur)} − ${fmtM(prev)}) / ${fmtM(prev)}\n= ${(g * 100).toFixed(2)}%\nSource: IQ_TOTAL_REV × IQ_FY-${i} and IQ_FY-${i + 1}.`;
  };

  const marginTooltip = (i: number): string => {
    const ebit = history[i]?.ebit;
    const rev = history[i]?.revenues;
    if (ebit == null || rev == null) return `No data for ${yearLabel(i)} (EBIT or Revenue missing).`;
    const m = ebit / rev;
    return `${yearLabel(i)} pre-tax operating margin = EBIT / Revenue\n= ${fmtM(ebit)} / ${fmtM(rev)}\n= ${(m * 100).toFixed(2)}%\nSource: IQ_EBIT / IQ_TOTAL_REV × IQ_FY-${i}.`;
  };

  const scTooltip = (i: number): string => {
    const rev = history[i]?.revenues;
    const eq = history[i]?.bv_equity;
    const debt = history[i]?.bv_debt;
    const cash = history[i]?.cash_and_marketable_securities;
    if (rev == null || eq == null || debt == null || cash == null) {
      return `No data for ${yearLabel(i)} (Revenue, BV Equity, BV Debt, or Cash missing for this year).`;
    }
    const ic = eq + debt - cash;
    if (ic === 0) return 'Invested Capital is zero — division undefined.';
    const sc = rev / ic;
    return `${yearLabel(i)} Sales / Capital = Revenue / Invested Capital\nIC = BV Equity + BV Debt − Cash\n   = ${fmtM(eq)} + ${fmtM(debt)} − ${fmtM(cash)} = ${fmtM(ic)}\nS/C = ${fmtM(rev)} / ${fmtM(ic)} = ${sc.toFixed(3)}×\nSource: IQ_TOTAL_REV, IQ_TOTAL_EQUITY, IQ_TOTAL_DEBT, IQ_CASH_ST_INVEST × IQ_FY-${i}.`;
  };

  const roicTooltip = (i: number): string => {
    const ebit = history[i]?.ebit;
    const eff = history[i]?.total_tax_expense != null && history[i]?.earnings_before_tax
      ? (history[i]!.total_tax_expense! / history[i]!.earnings_before_tax!)
      : data.inputs.macro_inputs?.tax_rate_effective ?? 0.21;
    const prev = history[i + 1];
    if (!prev || ebit == null || prev.bv_equity == null || prev.bv_debt == null || prev.cash_and_marketable_securities == null) {
      return `No data for ${yearLabel(i)} ROIC — needs current-year EBIT and prior-year (${yearLabel(i + 1)}) Invested Capital.`;
    }
    const nopat = ebit * (1 - eff);
    const icPrev = prev.bv_equity + prev.bv_debt - prev.cash_and_marketable_securities;
    if (icPrev === 0) return 'Prior-year Invested Capital is zero — ROIC undefined.';
    const roic = nopat / icPrev;
    return `${yearLabel(i)} ROIC = NOPAT / Prior-year IC\nNOPAT = EBIT × (1 − eff. tax)\n      = ${fmtM(ebit)} × (1 − ${(eff * 100).toFixed(2)}%)\n      = ${fmtM(nopat)}\nIC[${yearLabel(i + 1)}] = ${fmtM(prev.bv_equity)} + ${fmtM(prev.bv_debt)} − ${fmtM(prev.cash_and_marketable_securities)} = ${fmtM(icPrev)}\nROIC = ${fmtM(nopat)} / ${fmtM(icPrev)} = ${(roic * 100).toFixed(2)}%\nSources: IQ_EBIT, IQ_INC_TAX, IQ_EBT_EXCL × IQ_FY-${i}; IQ_TOTAL_EQUITY, IQ_TOTAL_DEBT, IQ_CASH_ST_INVEST × IQ_FY-${i + 1}.`;
  };

  const avgTooltip = (label: string, n: 3 | 5) => (_w: 3 | 5) =>
    `${n}-year mean of ${label} across FY-0 through FY-${n - 1} (values that resolved to None are skipped).`;

  return (
    <div className="max-w-6xl">
      <h2 className="text-xl font-bold mb-2">Stories to Numbers</h2>
      <ColorLegend />

      <p className="text-sm text-slate-600 mb-3">
        Three stories — Growth, Margin, Capital Efficiency — are mathematically coupled.
        This page surfaces what your inputs imply (Required ROIC, Required S/C) alongside
        historical and industry anchors so you can judge whether the three stories close
        the loop. Edit drivers in the Sensitivity panel below; everything on this page
        recomputes on every change.
      </p>

      {/* Narrative mapping table */}
      <SpreadsheetGrid>
        <thead>
          <tr>
            <SpreadsheetCell type="header" value="Narrative Question" align="left" />
            <SpreadsheetCell type="header" value="Value Driver" align="left" />
            <SpreadsheetCell type="header" value="Input Field" align="left" />
            <SpreadsheetCell type="header" value="Current Value" />
            <SpreadsheetCell type="header" value="Source" />
          </tr>
        </thead>
        <tbody>
          {narrative.map((s, i) => (
            <tr key={i}>
              <SpreadsheetCell type="label" value={s.narrative} align="left" />
              <SpreadsheetCell type="label" value={s.driver} align="left" />
              <SpreadsheetCell type="hint" value={s.input} align="left" />
              <SpreadsheetCell type={s.type} value={s.value} />
              <SpreadsheetCell type="label" value={
                s.type === 'hypothesis' ? 'User Input' :
                s.type === 'reference' ? 'Industry/Market' : 'Calculated'
              } align="center" />
            </tr>
          ))}
        </tbody>
      </SpreadsheetGrid>

      {/* Three-story joint examination */}
      <ClosedLoopStrip data={data} />

      <StoryValidationBlock
        title="Growth Story — how fast will revenue grow? (CAGR as primary average)"
        historical={cf?.historical_revenue_growth_by_year ?? []}
        avg3={cf?.historical_revenue_cagr_3yr ?? null}
        avg5={cf?.historical_revenue_cagr_5yr ?? null}
        industryMedian={industry?.revenue_growth ?? null}
        industryQ1={q('revenue_growth_3y')?.q1 ?? null}
        industryQ3={q('revenue_growth_3y')?.q3 ?? null}
        formatAs="pct"
        cellTooltip={growthTooltip}
        averageTooltip={(w) => `${w}-year CAGR = (Rev[FY-0] / Rev[FY-${w}])^(1/${w}) − 1.\nGeometric — financially correct multi-period growth measure, immune to volatility.\nSee the 10-year detail table below for the arithmetic-mean comparison.`}
      />

      <StoryValidationBlock
        title="Margin Story — pre-tax operating margin (EBIT / Revenue)"
        historical={cf?.historical_margin_by_year ?? []}
        avg3={cf?.historical_margin_avg_3yr ?? null}
        avg5={cf?.historical_margin_avg_5yr ?? null}
        industryMedian={industry?.pretax_operating_margin ?? null}
        industryQ1={q('pretax_operating_margin')?.q1 ?? null}
        industryQ3={q('pretax_operating_margin')?.q3 ?? null}
        formatAs="pct"
        cellTooltip={marginTooltip}
        averageTooltip={avgTooltip('pre-tax operating margin', 5)}
        reverseCheck={{
          label: 'Required ROIC (DuPont: margin × S/C)',
          required: impliedROIC,
          actual: cf?.historical_roic_avg_5yr ?? null,
          unit: 'pp',
        }}
      />

      {/* Historical ROIC block — the closed-loop output measured annually
          from the firm's own history. Mirrors the other three blocks' layout. */}
      <StoryValidationBlock
        title="Historical ROIC — what the firm has actually earned per dollar of capital"
        historical={cf?.historical_roic_by_year ?? []}
        avg3={cf?.historical_roic_avg_3yr ?? null}
        avg5={cf?.historical_roic_avg_5yr ?? null}
        industryMedian={industry?.roic ?? null}
        industryQ1={null}
        industryQ3={null}
        formatAs="pct"
        cellTooltip={roicTooltip}
        averageTooltip={avgTooltip('ROIC', 5)}
      />

      <StoryValidationBlock
        title="Capital-Efficiency Story — how much capital does each dollar of revenue require?"
        historical={cf?.historical_s_c_by_year ?? []}
        avg3={cf?.historical_s_c_avg_3yr ?? null}
        avg5={cf?.historical_s_c_avg_5yr ?? null}
        industryMedian={industry?.sales_to_capital ?? null}
        industryQ1={q('sales_to_capital')?.q1 ?? null}
        industryQ3={q('sales_to_capital')?.q3 ?? null}
        formatAs="dec"
        cellTooltip={scTooltip}
        averageTooltip={avgTooltip('Sales/Capital', 5)}
        reverseCheck={{
          label: 'Required S/C (given roicAnchor / your margin)',
          required: impliedSCReq,
          actual: cf?.historical_s_c_avg_5yr ?? null,
          unit: '×',
        }}
      />

      {/* 10-year detailed historical table — lists every annual value for
          ROIC, S/C, margin, and growth, with per-year tooltips showing the
          exact calculation and dual averaging (arithmetic + CAGR/weighted
          where financially warranted). Sits directly below the three
          Required-X reverse checks so the analyst can scan annual
          history alongside the required-values call-out. */}
      <HistoricalDetailTable data={data} />

      {/* Tax-rate override panel */}
      <TaxOverridePanel data={data} onPatch={onPatch} />

      {/* How these are calculated — explanatory footer */}
      <section className="my-4 bg-slate-50 border border-slate-200 rounded-md p-3 text-xs text-slate-700">
        <h3 className="text-sm font-semibold text-slate-800 mb-2">
          How each number is calculated
        </h3>
        <dl className="space-y-2">
          <div>
            <dt className="font-semibold text-slate-900">Historical Revenue Growth (per year)</dt>
            <dd className="ml-3 font-mono text-[11px]">
              = (Revenue[t] − Revenue[t−1]) / Revenue[t−1]
              <br />
              Source: IQ_TOTAL_REV × IQ_FY-t and IQ_FY-(t+1)
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-900">Historical Pre-tax Operating Margin (per year)</dt>
            <dd className="ml-3 font-mono text-[11px]">
              = EBIT[t] / Revenue[t]
              <br />
              Source: IQ_EBIT / IQ_TOTAL_REV × IQ_FY-t
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-900">Historical Invested Capital (per year)</dt>
            <dd className="ml-3 font-mono text-[11px]">
              IC[t] = BV Equity[t] + BV Debt[t] − Cash[t]
              <br />
              Source: IQ_TOTAL_EQUITY + IQ_TOTAL_DEBT − IQ_CASH_ST_INVEST × IQ_FY-t
              <br />
              <span className="italic text-slate-500">
                Note: for the DCF engine's IC, the R&D capitalization asset is added; this historical diagnostic
                uses raw book values only for cross-checkability against the 10-K.
              </span>
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-900">Historical ROIC (per year)</dt>
            <dd className="ml-3 font-mono text-[11px]">
              = NOPAT[t] / IC[t−1]
              <br />
              NOPAT[t] = EBIT[t] × (1 − effective tax[t])
              <br />
              effective tax[t] = IQ_INC_TAX[t] / IQ_EBT_EXCL[t]
              <br />
              Uses prior-year IC as the denominator (standard convention — matches the capital in place at the
              start of the period during which NOPAT was earned).
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-900">Historical Sales / Capital (per year)</dt>
            <dd className="ml-3 font-mono text-[11px]">
              = Revenue[t] / IC[t]
              <br />
              Uses current-year IC so the ratio reflects the capital in place during the revenue-generating period.
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-900">3-yr and 5-yr averages</dt>
            <dd className="ml-3 font-mono text-[11px]">
              Simple mean across annual values. Years where the ratio resolved to None (missing components,
              zero denominator) are skipped — the average is taken over whatever values were computable.
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-900">Required ROIC (your story implies)</dt>
            <dd className="ml-3 font-mono text-[11px]">
              = target_operating_margin × sales_to_capital_high
              <br />
              DuPont identity: ROIC = margin × asset turnover. The ROIC your three stories force the firm to
              earn for the arithmetic to close. Compare against historical ROIC (has the firm done it?),
              industry median (has any peer done it?), and WACC (does growth create or destroy value?).
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-900">Required Sales / Capital (your story implies)</dt>
            <dd className="ml-3 font-mono text-[11px]">
              = ROIC anchor / target_operating_margin
              <br />
              Where ROIC anchor = roic_stable_override (if set) else historical 5-yr avg ROIC else WACC.
              Answers: given your margin story and a reference ROIC, what asset turnover must the firm achieve?
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-900">Implied ROIC Projections (per year, from the DCF engine)</dt>
            <dd className="ml-3 font-mono text-[11px]">
              Implied ROIC[t] = NOPAT[t] / IC[t−1] from the projection path itself.
              <br />
              As the stories project forward, IC rolls forward as IC[t] = IC[t−1] + Reinvestment[t].
              <br />
              The terminal implied ROIC should converge to terminal WACC (Damodaran: no excess returns in perpetuity).
            </dd>
          </div>
        </dl>
      </section>

      {/* Reuse the existing SensitivityPanel — same archetype presets,
          Reset, tornado, 8-driver sliders, live impact cards. */}
      <SensitivityPanel data={data} onPatch={onPatch} onPatchMany={onPatchMany} />
    </div>
  );
}
