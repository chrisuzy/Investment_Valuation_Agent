/**
 * Canonical base-year accessors for the frontend.
 *
 * The engine's modules (M1–M6) all run on `ltm_financials` — the
 * LTM-rotated raw financials produced by M0. Most frontend pages were
 * historically reading `data.inputs.raw_financials[0]` (plain FY0),
 * which is a different base year for any firm with quarterly data past
 * the last 10-K. This drifted the displayed "current" numbers away from
 * the numbers the DCF actually uses.
 *
 * Use `baseYear(data)` whenever a page wants to show a "current" or
 * "base year" financial line; use `baseYearEbit(data)` when the line
 * is EBIT / operating margin and you want the Damodaran-adjusted value
 * (post R&D capitalization, post operating-lease capitalization) rather
 * than raw reported EBIT.
 */

import type { ValuationResponse, RawFinancials } from '../types/valuation';

/** The financial period the engine's DCF is anchored on.
 *  LTM if available, else plain FY0 from the raw data. */
export function baseYear(data: ValuationResponse): RawFinancials | undefined {
  return data.ltm_financials ?? data.inputs.raw_financials[0];
}

/** The prior annual period (for YoY / marginal ratios).
 *  When the engine rotates LTM, the first raw_financials row IS the
 *  most-recent 10-K annual — which functions as "FY-1" relative to LTM. */
export function priorYear(data: ValuationResponse): RawFinancials | undefined {
  if (data.ltm_financials) return data.inputs.raw_financials[0];
  return data.inputs.raw_financials[1];
}

/** EBIT for display / ratio calculations — Damodaran-adjusted where
 *  available (adjusted_ebit = raw EBIT + R&D add-back + lease add-back).
 *  Falls back to raw EBIT from the base year if no adjustments ran. */
export function baseYearEbit(data: ValuationResponse): number | null | undefined {
  if (data.adjusted?.adjusted_ebit != null) return data.adjusted.adjusted_ebit;
  return baseYear(data)?.ebit;
}

/** Operating margin using adjusted EBIT over base-year revenue. */
export function baseYearMargin(data: ValuationResponse): number | null {
  const by = baseYear(data);
  const ebit = baseYearEbit(data);
  if (!by?.revenues || ebit == null) return null;
  return ebit / by.revenues;
}
