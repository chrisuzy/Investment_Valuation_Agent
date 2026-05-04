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
        title="Growth Story — how fast will revenue grow?"
        historical={cf?.historical_revenue_growth_by_year ?? []}
        avg3={null /* not tracked as named field; rely on visible 3yr from cells */}
        avg5={null}
        industryMedian={industry?.revenue_growth ?? null}
        industryQ1={q('revenue_growth_3y')?.q1 ?? null}
        industryQ3={q('revenue_growth_3y')?.q3 ?? null}
        formatAs="pct"
      />

      <StoryValidationBlock
        title="Margin Story — how profitable will each dollar of revenue be?"
        historical={cf?.historical_margin_by_year ?? []}
        avg3={cf?.historical_margin_avg_3yr ?? null}
        avg5={cf?.historical_margin_avg_5yr ?? null}
        industryMedian={industry?.pretax_operating_margin ?? null}
        industryQ1={q('pretax_operating_margin')?.q1 ?? null}
        industryQ3={q('pretax_operating_margin')?.q3 ?? null}
        formatAs="pct"
        reverseCheck={{
          label: 'Required ROIC (DuPont: margin × S/C)',
          required: impliedROIC,
          actual: cf?.historical_roic_avg_5yr ?? null,
          unit: 'pp',
        }}
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
        reverseCheck={{
          label: 'Required S/C (given roicAnchor / your margin)',
          required: impliedSCReq,
          actual: cf?.historical_s_c_avg_5yr ?? null,
          unit: '×',
        }}
      />

      {/* Tax-rate override panel */}
      <TaxOverridePanel data={data} onPatch={onPatch} />

      {/* Reuse the existing SensitivityPanel — same archetype presets,
          Reset, tornado, 8-driver sliders, live impact cards. */}
      <SensitivityPanel data={data} onPatch={onPatch} onPatchMany={onPatchMany} />
    </div>
  );
}
