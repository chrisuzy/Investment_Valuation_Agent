/**
 * Per-field vintage cascade for base-year display.
 *
 * When a single field on the base-year row is missing from the LTM-rotated
 * block (thin quarterly feed on some tickers — e.g. Lenovo HK), fall back
 * field-by-field to annual[0] (10-K), then annual[1] (10-K-1). Return the
 * vintage source alongside the value so the UI can attach a small badge
 * telling the user which vintage each individual cell comes from.
 *
 * Use the existing `baseYear()` / `baseYearEbit()` helpers in `baseYear.ts`
 * for single-field access that doesn't need vintage tracking — this module
 * is for pages (ValuationOutput base-year column) that want transparency.
 */

import type { ValuationResponse, RawFinancials } from '../types/valuation';

export type VintageSource = 'LTM' | '10-K' | '10-K-1';

export interface FieldWithVintage<T> {
  value: T | null | undefined;
  vintage: VintageSource | null;
}

/**
 * Per-field cascade: LTM → annual[0] → annual[1].
 * Returns the first non-null value with its provenance. If all three
 * are null, returns { value: null, vintage: null }.
 */
export function getField<K extends keyof RawFinancials>(
  data: ValuationResponse,
  key: K,
): FieldWithVintage<RawFinancials[K]> {
  const ltm = data.ltm_financials;
  if (ltm && ltm[key] != null) {
    return { value: ltm[key], vintage: 'LTM' };
  }
  const fy0 = data.inputs.raw_financials[0];
  if (fy0 && fy0[key] != null) {
    return { value: fy0[key], vintage: '10-K' };
  }
  const fy1 = data.inputs.raw_financials[1];
  if (fy1 && fy1[key] != null) {
    return { value: fy1[key], vintage: '10-K-1' };
  }
  return { value: null, vintage: null };
}
