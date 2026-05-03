/**
 * Damodaran's six story archetypes, rendered as coherent multi-driver patches.
 *
 * Each archetype returns a patch payload that sets all 8 tornado drivers at
 * once, so the user can say "treat this like a utility" and see the entire
 * dial set snap to a plausible utility-shaped set of assumptions.
 *
 * Values are industry-aware where Damodaran's industry data carries a usable
 * median (growth, margin, sales-to-capital). For drivers without industry
 * comparables (failure probability, convergence year, WACC shift), we use
 * canonical values from Damodaran's published sensitivity examples.
 */

import type { ValuationResponse } from '../../types/valuation';
import type { PatchValue } from '../../api/client';

export interface Archetype {
  id: string;
  emoji: string;
  name: string;
  tagline: string;
  /** Returns the PATCH payload for this archetype given the company's data. */
  build: (data: ValuationResponse) => Record<string, PatchValue>;
}

/** Pull the industry median for a given field, or a fallback if unset. */
function indMedian(data: ValuationResponse, field: keyof ValuationResponse['inputs']['industry_data'], fallback: number): number {
  const v = data.inputs.industry_data?.[field] as number | null | undefined;
  return (typeof v === 'number' && v !== 0) ? v : fallback;
}

/** Build a "tilted" industry value: multiplier × median, clipped to a sensible band. */
function tiltMedian(data: ValuationResponse, field: keyof ValuationResponse['inputs']['industry_data'], mult: number, fallback: number, bounds?: [number, number]): number {
  const median = indMedian(data, field, fallback);
  let v = median * mult;
  if (bounds) v = Math.max(bounds[0], Math.min(bounds[1], v));
  return v;
}

export const ARCHETYPES: Archetype[] = [
  {
    id: 'disruptor',
    emoji: '🚀',
    name: 'Disruptor',
    tagline: 'high growth, margin expanding',
    build: (data) => ({
      'valuation_assumptions.revenue_growth_next_year':
        tiltMedian(data, 'revenue_growth', 3.0, 0.25, [0.15, 0.50]),
      'valuation_assumptions.revenue_growth_years_2_5':
        tiltMedian(data, 'revenue_growth', 2.5, 0.20, [0.10, 0.35]),
      'valuation_assumptions.target_operating_margin':
        tiltMedian(data, 'pretax_operating_margin', 1.3, 0.25, [0.10, 0.40]),
      'valuation_assumptions.margin_convergence_year': 7,
      'valuation_assumptions.sales_to_capital_high':
        indMedian(data, 'sales_to_capital', 2.0),
      'methodology_choices.wacc_level_shift_bps': 100,
      'valuation_assumptions.failure_probability': 0.05,
      'valuation_assumptions.override_growth_perpetuity': false,
    }),
  },
  {
    id: 'growth',
    emoji: '📈',
    name: 'Growth',
    tagline: 'solid growth, established',
    build: (data) => ({
      'valuation_assumptions.revenue_growth_next_year':
        tiltMedian(data, 'revenue_growth', 2.0, 0.15, [0.08, 0.25]),
      'valuation_assumptions.revenue_growth_years_2_5':
        tiltMedian(data, 'revenue_growth', 1.7, 0.12, [0.05, 0.20]),
      'valuation_assumptions.target_operating_margin':
        tiltMedian(data, 'pretax_operating_margin', 1.1, 0.20, [0.08, 0.30]),
      'valuation_assumptions.margin_convergence_year': 5,
      'valuation_assumptions.sales_to_capital_high':
        indMedian(data, 'sales_to_capital', 2.0),
      'methodology_choices.wacc_level_shift_bps': 0,
      'valuation_assumptions.failure_probability': 0.02,
      'valuation_assumptions.override_growth_perpetuity': false,
    }),
  },
  {
    id: 'mature',
    emoji: '🏢',
    name: 'Mature',
    tagline: 'industry-average performer',
    build: (data) => ({
      'valuation_assumptions.revenue_growth_next_year':
        indMedian(data, 'revenue_growth', 0.05),
      'valuation_assumptions.revenue_growth_years_2_5':
        indMedian(data, 'revenue_growth', 0.05),
      'valuation_assumptions.target_operating_margin':
        indMedian(data, 'pretax_operating_margin', 0.15),
      'valuation_assumptions.margin_convergence_year': 3,
      'valuation_assumptions.sales_to_capital_high':
        indMedian(data, 'sales_to_capital', 1.5),
      'methodology_choices.wacc_level_shift_bps': 0,
      'valuation_assumptions.failure_probability': 0.0,
      'valuation_assumptions.override_growth_perpetuity': false,
    }),
  },
  {
    id: 'utility',
    emoji: '⚡',
    name: 'Utility',
    tagline: 'low growth, low risk',
    build: (data) => ({
      'valuation_assumptions.revenue_growth_next_year': 0.03,
      'valuation_assumptions.revenue_growth_years_2_5': 0.03,
      'valuation_assumptions.target_operating_margin':
        tiltMedian(data, 'pretax_operating_margin', 0.7, 0.12, [0.05, 0.20]),
      'valuation_assumptions.margin_convergence_year': 2,
      'valuation_assumptions.sales_to_capital_high':
        tiltMedian(data, 'sales_to_capital', 1.3, 2.0, [0.8, 3.0]),
      'methodology_choices.wacc_level_shift_bps': -50,
      'valuation_assumptions.failure_probability': 0.0,
      'valuation_assumptions.override_growth_perpetuity': false,
    }),
  },
  {
    id: 'cyclical',
    emoji: '🔄',
    name: 'Cyclical',
    tagline: 'mean-reverting, volatile',
    build: (data) => ({
      'valuation_assumptions.revenue_growth_next_year':
        indMedian(data, 'revenue_growth', 0.05),
      'valuation_assumptions.revenue_growth_years_2_5':
        indMedian(data, 'revenue_growth', 0.05),
      'valuation_assumptions.target_operating_margin':
        tiltMedian(data, 'pretax_operating_margin', 0.85, 0.13, [0.05, 0.25]),
      'valuation_assumptions.margin_convergence_year': 5,
      'valuation_assumptions.sales_to_capital_high':
        indMedian(data, 'sales_to_capital', 2.0),
      'methodology_choices.wacc_level_shift_bps': 50,
      'valuation_assumptions.failure_probability': 0.03,
      'valuation_assumptions.override_growth_perpetuity': false,
    }),
  },
  {
    id: 'distressed',
    emoji: '💔',
    name: 'Distressed',
    tagline: 'turnaround / failure risk',
    build: (data) => ({
      'valuation_assumptions.revenue_growth_next_year': -0.05,
      'valuation_assumptions.revenue_growth_years_2_5':
        tiltMedian(data, 'revenue_growth', 0.4, 0.03, [0.0, 0.08]),
      'valuation_assumptions.target_operating_margin':
        tiltMedian(data, 'pretax_operating_margin', 0.5, 0.08, [0.02, 0.15]),
      'valuation_assumptions.margin_convergence_year': 8,
      'valuation_assumptions.sales_to_capital_high':
        indMedian(data, 'sales_to_capital', 1.5),
      'methodology_choices.wacc_level_shift_bps': 150,
      'valuation_assumptions.failure_probability': 0.20,
      'valuation_assumptions.override_growth_perpetuity': false,
    }),
  },
];

/** Identify which archetype the current dials are closest to (L2 normalized distance). */
export function closestArchetype(data: ValuationResponse): string | null {
  const va = data.inputs.valuation_assumptions;
  const mc = data.inputs.methodology_choices;
  if (!va || !mc) return null;

  const cur = [
    va.revenue_growth_next_year ?? 0,
    va.revenue_growth_years_2_5 ?? 0,
    va.target_operating_margin ?? 0.15,
    (va.margin_convergence_year ?? 5) / 10,      // scale to same order-of-magnitude
    (va.sales_to_capital_high ?? 2) / 5,          // scale down
    ((mc.wacc_level_shift_bps ?? 0) / 1000),      // 150 bps → 0.15
    va.failure_probability ?? 0,
  ];

  let bestId: string | null = null;
  let bestDist = Infinity;
  for (const a of ARCHETYPES) {
    const payload = a.build(data);
    const pro = [
      payload['valuation_assumptions.revenue_growth_next_year'],
      payload['valuation_assumptions.revenue_growth_years_2_5'],
      payload['valuation_assumptions.target_operating_margin'],
      (payload['valuation_assumptions.margin_convergence_year'] as number) / 10,
      (payload['valuation_assumptions.sales_to_capital_high'] as number) / 5,
      ((payload['methodology_choices.wacc_level_shift_bps'] as number) / 1000),
      payload['valuation_assumptions.failure_probability'],
    ] as number[];
    let d = 0;
    for (let i = 0; i < cur.length; i++) d += (cur[i] - pro[i]) ** 2;
    if (d < bestDist) { bestDist = d; bestId = a.id; }
  }
  // Only call it a "match" if we're reasonably close
  return bestDist < 0.25 ? bestId : null;
}

/** Piecewise-linear percentile: where does `value` fall within Q1/Median/Q3? */
export function percentile(value: number, q1: number, median: number, q3: number): number | null {
  if (q1 === undefined || median === undefined || q3 === undefined) return null;
  if (q1 >= q3) return null;
  if (value <= q1) {
    // extrapolate below Q1: linear toward 0
    const span = median - q1;
    if (span <= 0) return 25;
    return Math.max(0, 25 - ((q1 - value) / span) * 25);
  }
  if (value >= q3) {
    const span = q3 - median;
    if (span <= 0) return 75;
    return Math.min(100, 75 + ((value - q3) / span) * 25);
  }
  if (value <= median) return 25 + ((value - q1) / (median - q1)) * 25;
  return 50 + ((value - median) / (q3 - median)) * 25;
}
