/** Sensitivity-tornado response shape from POST /api/valuation/{sid}/sensitivity. */

export interface SensitivityBar {
  driver: string;
  label: string;
  patch_path: string;
  range_lo: number;
  range_hi: number;
  vps_lo: number | null;
  vps_hi: number | null;
  delta_lo: number | null;
  delta_hi: number | null;
  range_source: 'industry_q1_q3' | 'canonical' | 'industry_fallback_canonical';
}

export interface SensitivityResponse {
  baseline_vps: number | null;
  currency: string | null;
  bars: SensitivityBar[];
}
