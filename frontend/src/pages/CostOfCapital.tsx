import { useState } from 'react';
import type {
  ValuationResponse,
  MethodologyChoices,
  BusinessSegment,
  GeographicSegment,
  CostOfCapitalApproach,
  BetaApproach,
  ErpApproach,
  KdApproach,
} from '../types/valuation';
import type { PatchValue } from '../api/client';
import { ciq, damodaran, country as countrySrc, formula, user, tooltipFor, backendField } from '../lib/sources';

function fmtPct(v: number | null | undefined, decimals = 2): string {
  if (v === null || v === undefined) return '—';
  return (v * 100).toFixed(decimals) + '%';
}
function fmtNum(v: number | null | undefined, decimals = 4): string {
  if (v === null || v === undefined) return '—';
  return v.toLocaleString('en-US', { maximumFractionDigits: decimals, minimumFractionDigits: decimals });
}
function fmtCur(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—';
  return v.toLocaleString('en-US', { maximumFractionDigits: 0 });
}

// ──────────────────────────────────────────────────────────────────────────
// Dropdown option tables (must mirror backend MethodologyChoices enum values)
// ──────────────────────────────────────────────────────────────────────────

const APPROACH_OPTIONS: { value: CostOfCapitalApproach; label: string; supported: boolean }[] = [
  { value: 'detailed',         label: 'Detailed (CAPM build-up)',                supported: true },
  { value: 'direct',           label: 'Direct input (type WACC directly)',       supported: true },
  { value: 'industry_average', label: 'Industry average + RF adjustment',        supported: true },
  { value: 'decile',           label: 'Regional decile lookup (5×5)',            supported: true },
];

const BETA_OPTIONS: { value: BetaApproach; label: string; supported: boolean }[] = [
  { value: 'single_business_us',      label: 'Single business — US industry β_u',        supported: true },
  { value: 'single_business_global',  label: 'Single business — Global industry β_u',    supported: true },
  { value: 'multi_business_us',       label: 'Multi-business EV-weighted — US',          supported: true },
  { value: 'multi_business_global',   label: 'Multi-business EV-weighted — Global',      supported: true },
  { value: 'direct_levered',          label: 'Direct input — levered β (skip relever)',  supported: true },
  { value: 'direct_unlevered',        label: 'Direct input — unlevered β (relever)',     supported: true },
];

const ERP_OPTIONS: { value: ErpApproach; label: string; supported: boolean }[] = [
  { value: 'country_of_incorporation', label: 'Country of incorporation',                supported: true },
  { value: 'operating_countries',      label: 'Operating countries (rev-weighted)',      supported: true },
  { value: 'operating_regions',        label: 'Operating regions (rev-weighted)',        supported: true },
  { value: 'direct',                   label: 'Direct input',                            supported: true },
];

const KD_OPTIONS: { value: KdApproach; label: string; supported: boolean }[] = [
  { value: 'industry_fallback',  label: 'Industry-average Kd',                 supported: true },
  { value: 'direct',             label: 'Direct input',                        supported: true },
  { value: 'synthetic_rating',   label: 'Synthetic rating (coverage→spread)',  supported: true },
  { value: 'actual_rating',      label: 'Actual rating → spread',              supported: true },
];

const RATINGS = ['Aaa/AAA','Aa2/AA','A1/A+','A2/A','A3/A-','Baa2/BBB','Ba1/BB+','Ba2/BB','B1/B+','B2/B','B3/B-','Caa/CCC','Ca2/CC','C2/C','D2/D'];
const DECILE_REGIONS = ['US','Europe','Japan','Emerging','Global'];
const DECILE_RISK_GROUPS = ['First Decile','First Quartile','Median','Third Quartile','Ninth Decile'];
const FIRM_TYPES = ['large','small','financial'];

// ──────────────────────────────────────────────────────────────────────────
// Small building blocks
// ──────────────────────────────────────────────────────────────────────────

function Section({ title, children, subtitle }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="bg-white border border-gray-300 rounded-md shadow-sm">
      <header className="px-4 py-2 bg-gray-100 border-b border-gray-300">
        <h2 className="text-sm font-bold text-gray-800">{title}</h2>
        {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <div className="mb-3">
      <label className="block text-xs font-semibold text-gray-700 mb-1">{label}</label>
      {children}
      {hint && <p className="text-xs text-gray-500 mt-0.5">{hint}</p>}
    </div>
  );
}

function KV({ label, value, bold, tooltip }: { label: string; value: string; bold?: boolean; tooltip?: string }) {
  const hasTip = Boolean(tooltip && tooltip.length > 0);
  return (
    <div
      className={`flex justify-between items-center py-1 border-b border-gray-100 last:border-0 ${hasTip ? 'cursor-help hover:bg-sky-50/60' : ''}`}
      title={tooltip}
    >
      <span className={`text-xs ${bold ? 'font-bold' : 'text-gray-700'}`}>{label}</span>
      <span className={`text-xs tabular-nums inline-flex items-center gap-1 ${bold ? 'font-bold' : 'text-gray-900'}`}>
        {value}
        {hasTip && <span aria-hidden className="w-1.5 h-1.5 rounded-full bg-sky-500 opacity-60" />}
      </span>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Main component
// ──────────────────────────────────────────────────────────────────────────

interface Props {
  data: ValuationResponse;
  sessionId?: string | null;
  onPatch?: (path: string, value: PatchValue) => void | Promise<void>;
  setData?: (r: ValuationResponse) => void;
}

export default function CostOfCapital({ data, onPatch }: Props) {
  const coc = data.cost_of_capital;
  const macro = data.inputs.macro_inputs;
  const ind = data.inputs.industry_data;
  const indGlobal = data.inputs.industry_data_global;
  const fin = data.ltm_financials ?? data.inputs.raw_financials[0];
  const m: MethodologyChoices = data.inputs.methodology_choices;

  // local state (optimistic) for segment editors so user can add/edit rows without
  // round-tripping to backend on every keystroke.
  const [busSegs, setBusSegs] = useState<BusinessSegment[]>(m.business_segments ?? []);
  const [geoSegs, setGeoSegs] = useState<GeographicSegment[]>(m.geographic_segments ?? []);

  // Shared context for tooltip composers — avoids recomputing per cell.
  const ticker = data.inputs.ticker;
  const tipCtx = {
    ticker,
    industry: ind?.industry_name,
    country: data.inputs.country,
    taxRate: macro.tax_rate_marginal,
    coc,
  };
  const tip = (path: string) => tooltipFor(path, tipCtx);

  // Patch helper — all methodology changes funnel through this.
  const patch = (path: string, value: PatchValue) => onPatch?.(path, value);

  const patchM = (key: keyof MethodologyChoices, value: PatchValue) => patch(`methodology_choices.${key}`, value);

  const saveBusSegs = (rows: BusinessSegment[]) => {
    setBusSegs(rows);
    patchM('business_segments', rows as unknown as unknown[]);
  };
  const saveGeoSegs = (rows: GeographicSegment[]) => {
    setGeoSegs(rows);
    patchM('geographic_segments', rows as unknown as unknown[]);
  };

  return (
    <div className="max-w-6xl space-y-4 p-4">
      <div className="bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-300 rounded-md p-4">
        <h1 className="text-2xl font-bold text-gray-800">Cost of Capital (M2)</h1>
        <p className="text-xs text-gray-600 mt-1">
          Ginzu-faithful WACC engine: 4 approaches × 6 β variants × 4 ERP variants × 4 Kd variants.
          Change the dropdowns below to test alternate methodologies. Every branch reports what it used.
        </p>
      </div>

      {/* ─── BRANCH LABELS: what the backend actually used this run ─── */}
      <Section title="Current Run — Branch Trace" subtitle="What the backend actually computed on this response.">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
          <div className="bg-gray-50 rounded px-2 py-1.5 cursor-help hover:bg-sky-50" title="Top-level cost-of-capital approach. Set via methodology_choices.cost_of_capital_approach. One of: detailed (CAPM build-up), direct (user WACC), industry_average, decile.">
            <div className="text-gray-500 uppercase tracking-wide">Approach</div>
            <div className="font-semibold text-gray-800">{coc?.approach_used ?? '—'}</div>
          </div>
          <div className="bg-gray-50 rounded px-2 py-1.5 cursor-help hover:bg-sky-50" title="Which β source was used. Set via methodology_choices.beta_approach. single_business_us → betas.xls; single_business_global → betaGlobal.xls; multi_business_* → EV-weighted across segments.">
            <div className="text-gray-500 uppercase tracking-wide">β branch</div>
            <div className="font-semibold text-gray-800">{coc?.beta_branch_used ?? '—'}</div>
          </div>
          <div className="bg-gray-50 rounded px-2 py-1.5 cursor-help hover:bg-sky-50" title="How ERP was determined. Set via methodology_choices.erp_approach. country_of_incorporation → base ERP + CRP of the home country; operating_countries/regions → revenue-weighted blend.">
            <div className="text-gray-500 uppercase tracking-wide">ERP branch</div>
            <div className="font-semibold text-gray-800">{coc?.erp_branch_used ?? '—'}</div>
          </div>
          <div className="bg-gray-50 rounded px-2 py-1.5 cursor-help hover:bg-sky-50" title="How pre-tax Kd was determined. Set via methodology_choices.kd_approach. industry_fallback → wacc.xls industry Kd; synthetic_rating → interest-coverage → rating → spread; actual_rating → user-supplied rating → spread.">
            <div className="text-gray-500 uppercase tracking-wide">Kd branch</div>
            <div className="font-semibold text-gray-800">{coc?.kd_branch_used ?? '—'}</div>
          </div>
        </div>

        {(coc?.warnings?.length ?? 0) > 0 && (
          <div className="mt-3 bg-amber-50 border border-amber-300 rounded-md p-3">
            <div className="text-xs font-bold text-amber-800 mb-1">Warnings / Fallbacks ({coc!.warnings.length})</div>
            <ul className="list-disc list-inside text-xs text-amber-900 space-y-0.5">
              {coc!.warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </div>
        )}
      </Section>

      {/* ─── APPROACH PICKER ─── */}
      <Section title="1. Cost-of-Capital Approach" subtitle="Top-level selector: which of Ginzu's four methods to use.">
        <Field label="Approach">
          <select
            value={m.cost_of_capital_approach}
            onChange={(e) => patchM('cost_of_capital_approach', e.target.value)}
            className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
          >
            {APPROACH_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </Field>

        {m.cost_of_capital_approach === 'direct' && (
          <Field label="Direct WACC input" hint="Used when approach=direct. Enter as decimal (e.g. 0.10 = 10%).">
            <input
              type="number" step="0.0001" defaultValue={m.wacc_direct_input ?? ''}
              onBlur={(e) => patchM('wacc_direct_input', e.target.value === '' ? null : parseFloat(e.target.value))}
              className="w-40 border border-gray-300 rounded px-2 py-1 text-sm"
            />
          </Field>
        )}

        {m.cost_of_capital_approach === 'decile' && (
          <div className="grid grid-cols-2 gap-3">
            <Field label="Region" hint="Damodaran regional decile tables.">
              <select
                value={m.decile_region}
                onChange={(e) => patchM('decile_region', e.target.value)}
                className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
              >
                {DECILE_REGIONS.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </Field>
            <Field label="Risk group">
              <select
                value={m.decile_risk_group}
                onChange={(e) => patchM('decile_risk_group', e.target.value)}
                className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
              >
                {DECILE_RISK_GROUPS.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </Field>
          </div>
        )}

        {m.cost_of_capital_approach === 'industry_average' && (
          <p className="text-xs text-gray-600 bg-blue-50 border border-blue-200 rounded p-2">
            Uses Damodaran industry-average WACC ({fmtPct(ind.wacc)}) + (your RF − Damodaran publication RF 3.88%).
          </p>
        )}
      </Section>

      {/* Only show component-level controls if approach is detailed */}
      {m.cost_of_capital_approach === 'detailed' && (
        <>
          {/* ─── BETA ─── */}
          <Section title="2. Unlevered Beta (β_u) Methodology">
            <Field label="Beta approach">
              <select
                value={m.beta_approach}
                onChange={(e) => patchM('beta_approach', e.target.value)}
                className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
              >
                {BETA_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </Field>

            {/* Reference panel: what the industry β_u looks like */}
            <div className="bg-gray-50 border border-gray-200 rounded p-2 mb-3">
              <div className="text-xs font-semibold text-gray-700 mb-1">Reference — Damodaran industry β_u</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>US: <span className="font-mono cursor-help" title={damodaran("betas.xls", "Unlevered beta", ind.industry_name)}>{fmtNum(ind.beta_u)}</span> (cash-corrected: <span className="font-mono cursor-help" title={damodaran("betas.xls", "Unlevered beta corrected for cash", ind.industry_name)}>{fmtNum(ind.beta_u_corrected_for_cash)}</span>)</div>
                <div>Global: <span className="font-mono cursor-help" title={damodaran("betaGlobal.xls", "Unlevered beta", ind.industry_name)}>{fmtNum(indGlobal?.beta_u)}</span> (cash-corrected: <span className="font-mono cursor-help" title={damodaran("betaGlobal.xls", "Unlevered beta corrected for cash", ind.industry_name)}>{fmtNum(indGlobal?.beta_u_corrected_for_cash)}</span>)</div>
              </div>
            </div>

            {(m.beta_approach === 'direct_levered' || m.beta_approach === 'direct_unlevered') && (
              <Field label={m.beta_approach === 'direct_levered' ? 'β_L (levered) direct input' : 'β_U (unlevered) direct input'}>
                <input
                  type="number" step="0.001" defaultValue={m.beta_direct_input ?? ''}
                  onBlur={(e) => patchM('beta_direct_input', e.target.value === '' ? null : parseFloat(e.target.value))}
                  className="w-40 border border-gray-300 rounded px-2 py-1 text-sm"
                />
              </Field>
            )}

            {(m.beta_approach === 'multi_business_us' || m.beta_approach === 'multi_business_global') && (
              <SegmentEditor
                title="Business segments"
                columns={[
                  { key: 'name', label: 'Segment name', type: 'text' },
                  { key: m.beta_approach === 'multi_business_global' ? 'industry_global' : 'industry_us', label: 'Industry (Damodaran)', type: 'text' },
                  { key: 'revenue', label: 'Revenue', type: 'number' },
                ]}
                rows={busSegs as unknown as Record<string, string | number | null>[]}
                onChange={(rows) => saveBusSegs(rows as unknown as BusinessSegment[])}
                blankRow={{ name: '', industry_us: null, industry_global: null, revenue: 0 }}
              />
            )}
          </Section>

          {/* ─── ERP ─── */}
          <Section title="3. Equity Risk Premium (ERP) Methodology">
            <Field label="ERP approach">
              <select
                value={m.erp_approach}
                onChange={(e) => patchM('erp_approach', e.target.value)}
                className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
              >
                {ERP_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </Field>

            <div className="bg-gray-50 border border-gray-200 rounded p-2 mb-3">
              <div className="text-xs font-semibold text-gray-700 mb-1">Reference — Country ERP components</div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>Base mature-market ERP: <span className="font-mono cursor-help" title={countrySrc("ERP", "mature markets (US)")}>{fmtPct(macro.equity_risk_premium)}</span></div>
                <div>Country risk premium: <span className="font-mono cursor-help" title={countrySrc("CRP", data.inputs.country || "?")}>{fmtPct(macro.country_risk_premium)}</span></div>
                <div>Total (base + CRP): <span className="font-mono cursor-help" title={formula("ERP_total = base ERP + CRP")}>{fmtPct((macro.equity_risk_premium || 0) + (macro.country_risk_premium || 0))}</span></div>
              </div>
            </div>

            {m.erp_approach === 'direct' && (
              <Field label="Direct ERP input">
                <input
                  type="number" step="0.0001" defaultValue={m.erp_direct_input ?? ''}
                  onBlur={(e) => patchM('erp_direct_input', e.target.value === '' ? null : parseFloat(e.target.value))}
                  className="w-40 border border-gray-300 rounded px-2 py-1 text-sm"
                />
              </Field>
            )}

            {(m.erp_approach === 'operating_countries' || m.erp_approach === 'operating_regions') && (
              <SegmentEditor
                title={m.erp_approach === 'operating_countries' ? 'Operating countries' : 'Operating regions'}
                columns={[
                  { key: 'name', label: m.erp_approach === 'operating_countries' ? 'Country' : 'Region', type: 'text' },
                  { key: 'revenue', label: 'Revenue', type: 'number' },
                ]}
                rows={geoSegs as unknown as Record<string, string | number | null>[]}
                onChange={(rows) => saveGeoSegs(rows as unknown as GeographicSegment[])}
                blankRow={{ name: '', revenue: 0 }}
                hint={m.erp_approach === 'operating_regions'
                  ? "Region names: 'North America', 'Western Europe', 'Asia', 'Central and South America', 'Africa', 'Eastern Europe', 'Middle East', 'Australia & New Zealand', 'Caribbean'."
                  : 'Enter Damodaran country names as they appear in the country-risk dataset.'}
              />
            )}
          </Section>

          {/* ─── Kd ─── */}
          <Section title="4. Cost of Debt (Kd) Methodology">
            <Field label="Kd approach">
              <select
                value={m.kd_approach}
                onChange={(e) => patchM('kd_approach', e.target.value)}
                className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
              >
                {KD_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </Field>

            <div className="bg-gray-50 border border-gray-200 rounded p-2 mb-3">
              <div className="text-xs font-semibold text-gray-700 mb-1">Reference</div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>Industry Kd pre-tax: <span className="font-mono cursor-help" title={damodaran("wacc.xls", "Cost of Debt (pre-tax)", ind.industry_name)}>{fmtPct(ind.cost_of_debt_pretax)}</span></div>
                <div>Risk-free rate: <span className="font-mono cursor-help" title={user("Risk-free rate", "10y US Treasury ≈ 4.25%")}>{fmtPct(macro.risk_free_rate)}</span></div>
                <div>Country default spread: <span className="font-mono cursor-help" title={countrySrc("DefaultSpread", data.inputs.country || "?")}>{fmtPct(macro.default_spread)}</span></div>
                <div>Interest expense (LTM): <span className="font-mono cursor-help" title={ciq(ticker, "IQ_INTEREST_EXP", "LTM")}>{fmtCur(fin?.interest_expense)}</span></div>
                <div>Book debt: <span className="font-mono cursor-help" title={ciq(ticker, "IQ_TOTAL_DEBT", "IQ_FY-0")}>{fmtCur(fin?.bv_debt)}</span></div>
                <div>EBIT (adjusted): <span className="font-mono cursor-help" title={backendField("adjusted.adjusted_ebit", "Raw EBIT + R&D current − R&D amort + lease adj")}>{fmtCur(data.adjusted?.adjusted_ebit)}</span></div>
              </div>
            </div>

            {m.kd_approach === 'direct' && (
              <Field label="Direct Kd pre-tax input">
                <input
                  type="number" step="0.0001" defaultValue={m.kd_direct_input ?? ''}
                  onBlur={(e) => patchM('kd_direct_input', e.target.value === '' ? null : parseFloat(e.target.value))}
                  className="w-40 border border-gray-300 rounded px-2 py-1 text-sm"
                />
              </Field>
            )}

            {m.kd_approach === 'synthetic_rating' && (
              <>
                <Field label="Firm type (for coverage table)">
                  <select
                    value={m.synthetic_rating_firm_type}
                    onChange={(e) => patchM('synthetic_rating_firm_type', e.target.value)}
                    className="w-48 border border-gray-300 rounded px-2 py-1 text-sm"
                  >
                    {FIRM_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </Field>
                {coc?.interest_coverage_ratio !== null && coc?.interest_coverage_ratio !== undefined && (
                  <div className="bg-blue-50 border border-blue-200 rounded p-2 text-xs">
                    Inferred: coverage ratio <span className="font-mono cursor-help" title={formula("Coverage = Adjusted EBIT / Interest expense")}>{fmtNum(coc.interest_coverage_ratio, 2)}</span> →
                    rating <span className="font-semibold cursor-help" title="Coverage-to-rating table (large/small firms) from cost_of_capital_reference.json">{coc.synthetic_rating ?? '—'}</span> → Kd_pretax <span className="font-mono cursor-help" title={formula("Kd = RF + rating spread")}>{fmtPct(coc.cost_of_debt_pretax)}</span>
                  </div>
                )}
              </>
            )}

            {m.kd_approach === 'actual_rating' && (
              <Field label="Actual rating">
                <select
                  value={m.actual_rating ?? ''}
                  onChange={(e) => patchM('actual_rating', e.target.value || null)}
                  className="w-48 border border-gray-300 rounded px-2 py-1 text-sm"
                >
                  <option value="">— select —</option>
                  {RATINGS.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </Field>
            )}
          </Section>

          {/* ─── Debt pricing + Preferred + Convertibles ─── */}
          <Section title="5. MV of Debt, Preferred & Convertibles (advanced)">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Field label="MV of debt calculation method">
                  <div className="flex items-center gap-2">
                    <label className="flex items-center gap-1 text-xs">
                      <input
                        type="radio" checked={!m.use_bond_pricing_for_debt}
                        onChange={() => patchM('use_bond_pricing_for_debt', false)}
                      />
                      <span>Book ≈ MV (default)</span>
                    </label>
                    <label className="flex items-center gap-1 text-xs">
                      <input
                        type="radio" checked={m.use_bond_pricing_for_debt}
                        onChange={() => patchM('use_bond_pricing_for_debt', true)}
                      />
                      <span>Bond pricing</span>
                    </label>
                  </div>
                </Field>
                {m.use_bond_pricing_for_debt && (
                  <Field label="Weighted avg debt maturity (years)">
                    <input
                      type="number" step="0.5" defaultValue={m.debt_maturity_years}
                      onBlur={(e) => patchM('debt_maturity_years', parseFloat(e.target.value))}
                      className="w-32 border border-gray-300 rounded px-2 py-1 text-sm"
                    />
                  </Field>
                )}
              </div>

              <div>
                <Field label="Preferred stock">
                  <label className="flex items-center gap-2 text-xs">
                    <input
                      type="checkbox" checked={m.has_preferred}
                      onChange={(e) => patchM('has_preferred', e.target.checked)}
                    />
                    Firm has preferred stock outstanding
                  </label>
                </Field>
                {m.has_preferred && (
                  <div className="grid grid-cols-3 gap-2">
                    <Field label="Shares">
                      <input type="number" defaultValue={m.preferred_stock.shares}
                        onBlur={(e) => patchM('preferred_stock', { ...m.preferred_stock, shares: parseFloat(e.target.value) || 0 })}
                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm" />
                    </Field>
                    <Field label="Price/sh">
                      <input type="number" step="0.01" defaultValue={m.preferred_stock.price_per_share}
                        onBlur={(e) => patchM('preferred_stock', { ...m.preferred_stock, price_per_share: parseFloat(e.target.value) || 0 })}
                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm" />
                    </Field>
                    <Field label="Div/sh">
                      <input type="number" step="0.01" defaultValue={m.preferred_stock.dividend_per_share}
                        onBlur={(e) => patchM('preferred_stock', { ...m.preferred_stock, dividend_per_share: parseFloat(e.target.value) || 0 })}
                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm" />
                    </Field>
                  </div>
                )}
              </div>

              <div className="md:col-span-2">
                <Field label="Convertible debt">
                  <label className="flex items-center gap-2 text-xs">
                    <input
                      type="checkbox" checked={m.has_convertible}
                      onChange={(e) => patchM('has_convertible', e.target.checked)}
                    />
                    Firm has convertible debt
                  </label>
                </Field>
                {m.has_convertible && (
                  <div className="grid grid-cols-4 gap-2">
                    <Field label="Book value">
                      <input type="number" defaultValue={m.convertible_debt.book_value}
                        onBlur={(e) => patchM('convertible_debt', { ...m.convertible_debt, book_value: parseFloat(e.target.value) || 0 })}
                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm" />
                    </Field>
                    <Field label="Interest expense">
                      <input type="number" defaultValue={m.convertible_debt.interest_expense}
                        onBlur={(e) => patchM('convertible_debt', { ...m.convertible_debt, interest_expense: parseFloat(e.target.value) || 0 })}
                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm" />
                    </Field>
                    <Field label="Maturity (yrs)">
                      <input type="number" step="0.5" defaultValue={m.convertible_debt.maturity_years}
                        onBlur={(e) => patchM('convertible_debt', { ...m.convertible_debt, maturity_years: parseFloat(e.target.value) || 0 })}
                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm" />
                    </Field>
                    <Field label="Total market value">
                      <input type="number" defaultValue={m.convertible_debt.market_value}
                        onBlur={(e) => patchM('convertible_debt', { ...m.convertible_debt, market_value: parseFloat(e.target.value) || 0 })}
                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm" />
                    </Field>
                  </div>
                )}
              </div>
            </div>
          </Section>
        </>
      )}

      {/* ─── RESULTS ─── */}
      <Section title="Computed WACC" subtitle={`Result of the methodology selected above. Market values in reporting currency.`}>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">Beta & Risk</h3>
            <KV label="β_u (unlevered)"     value={fmtNum(coc?.beta_u)}     tooltip={tip("cost_of_capital.beta_u")} />
            <KV label="β_L (levered)"       value={fmtNum(coc?.beta_l)}     tooltip={tip("cost_of_capital.beta_l")} />
            <KV label="D/E ratio"           value={fmtNum(coc?.d_e_ratio)}  tooltip={tip("cost_of_capital.d_e_ratio")} />
            <KV label="Risk-free rate"      value={fmtPct(coc?.risk_free_rate)}
                                            tooltip={user("Risk-free rate (10y treasury)", "user-supplied via upload form; typically 4.25% US T-bond")} />
            <KV label="ERP (used)"          value={fmtPct(coc?.equity_risk_premium)}
                                            tooltip={tip("cost_of_capital.equity_risk_premium")} />
            {coc?.interest_coverage_ratio !== null && coc?.interest_coverage_ratio !== undefined && (
              <KV label="Interest coverage" value={fmtNum(coc.interest_coverage_ratio, 2)}
                                            tooltip={formula("Coverage = Adjusted EBIT / Interest expense",
                                                             `${fmtCur(data.adjusted?.adjusted_ebit)} / ${fmtCur(fin?.interest_expense)} = ${fmtNum(coc.interest_coverage_ratio, 2)}`)} />
            )}
            {coc?.synthetic_rating && (
              <KV label="Inferred rating"   value={coc.synthetic_rating}
                                            tooltip={`Coverage-to-rating table (large/small firms) from cost_of_capital_reference.json`} />
            )}
          </div>

          <div>
            <h3 className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">Capital Structure</h3>
            <KV label="MV equity"                   value={fmtCur(coc?.mv_equity)}
                                                    tooltip={formula("MV_equity = shares × price",
                                                                      `${fmtNum(fin?.shares_outstanding, 2)} × ${fmtNum(fin?.stock_price, 2)} = ${fmtCur(coc?.mv_equity)}`) + " — " + ciq(ticker, "IQ_MARKETCAP")} />
            <KV label="MV straight debt"            value={fmtCur(coc?.mv_straight_debt)}
                                                    tooltip={m.use_bond_pricing_for_debt
                                                      ? `Bond-priced: book debt × coupon-annuity at Kd=${fmtPct(coc?.cost_of_debt_pretax)}, maturity ${m.debt_maturity_years}y`
                                                      : `= Book debt (fallback when bond-pricing disabled) — ${ciq(ticker, "IQ_TOTAL_DEBT", "IQ_FY-0")}`} />
            <KV label="MV convertibles (straight)"  value={fmtCur(coc?.mv_convertible_straight_part)}
                                                    tooltip={m.has_convertible ? "Bond-priced value of the straight-debt portion of convertibles" : "No convertible debt — disabled"} />
            <KV label="Equity in convertibles"      value={fmtCur(coc?.equity_in_convertible)}
                                                    tooltip={m.has_convertible ? "= Convertible MV − straight-debt bond value" : "N/A"} />
            <KV label="MV leases (as debt)"         value={fmtCur(coc?.mv_leases)}
                                                    tooltip={m.has_operating_leases ? "PV of lease commitments discounted at Kd" : "Leases not capitalized (post-ASC 842 they are in bv_debt)"} />
            <KV label="MV debt total"               value={fmtCur(coc?.mv_debt_total)}
                                                    tooltip={tip("cost_of_capital.mv_debt_total")} />
            <KV label="MV preferred"                value={fmtCur(coc?.mv_preferred)}
                                                    tooltip={m.has_preferred ? "Preferred shares × price per share" : "No preferred stock"} />
            <KV label="Total capital"               value={fmtCur(coc?.total_capital)} bold
                                                    tooltip={formula("Total = MV_equity + MV_debt_total + MV_preferred")} />
          </div>

          <div>
            <h3 className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">Component Costs & Weights</h3>
            <KV label="Cost of equity"      value={fmtPct(coc?.cost_of_equity)}
                                            tooltip={tip("cost_of_capital.cost_of_equity")} />
            <KV label="Kd pre-tax"          value={fmtPct(coc?.cost_of_debt_pretax)}
                                            tooltip={tip("cost_of_capital.cost_of_debt_pretax")} />
            <KV label="Kd after-tax"        value={fmtPct(coc?.cost_of_debt_aftertax)}
                                            tooltip={tip("cost_of_capital.cost_of_debt_aftertax")} />
            <KV label="Cost of preferred"   value={fmtPct(coc?.cost_of_preferred)}
                                            tooltip={m.has_preferred ? "= dividend per share / price per share" : "N/A (no preferred stock)"} />
            <KV label="Weight equity"       value={fmtPct(coc?.weight_equity)}
                                            tooltip={tip("cost_of_capital.weight_equity")} />
            <KV label="Weight debt"         value={fmtPct(coc?.weight_debt)}
                                            tooltip={tip("cost_of_capital.weight_debt")} />
            <KV label="Weight preferred"    value={fmtPct(coc?.weight_preferred)}
                                            tooltip={formula("W_p = MV_preferred / Total Capital")} />
            <div
              className="mt-3 bg-indigo-50 border border-indigo-300 rounded px-3 py-2 cursor-help hover:bg-indigo-100"
              title={tip("cost_of_capital.wacc")}
            >
              <div className="text-xs text-gray-600">WACC <span className="text-sky-500">ⓘ</span></div>
              <div className="text-2xl font-bold text-indigo-900 tabular-nums">{fmtPct(coc?.wacc, 2)}</div>
            </div>
          </div>
        </div>
      </Section>

      {/* ─── INDUSTRY REFERENCE ─── */}
      <Section title="Industry Reference" subtitle={`Damodaran ${ind.region} industry averages for "${ind.industry_name}".`}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          <KV label="Industry β_u"             value={fmtNum(ind.beta_u)}
                                               tooltip={damodaran("betas.xls", "Unlevered beta", ind.industry_name)} />
          <KV label="Industry β_u (cash-corr)" value={fmtNum(ind.beta_u_corrected_for_cash)}
                                               tooltip={damodaran("betas.xls", "Unlevered beta corrected for cash", ind.industry_name)} />
          <KV label="Industry D/E"           value={fmtNum(ind.industry_d_e_ratio)}
                                             tooltip={damodaran("betas.xls", "D/E Ratio", ind.industry_name)} />
          <KV label="Industry effective tax" value={fmtPct(ind.industry_effective_tax_rate)}
                                             tooltip={damodaran("betas.xls", "Effective Tax rate", ind.industry_name)} />
          <KV label="Industry Ke"            value={fmtPct(ind.cost_of_equity)}
                                             tooltip={damodaran("wacc.xls", "Cost of Equity", ind.industry_name)} />
          <KV label="Industry Kd pre-tax"    value={fmtPct(ind.cost_of_debt_pretax)}
                                             tooltip={damodaran("wacc.xls", "Cost of Debt (pre-tax)", ind.industry_name)} />
          <KV label="Industry WACC"          value={fmtPct(ind.wacc)}
                                             tooltip={damodaran("wacc.xls", "Cost of Capital", ind.industry_name)} />
          <KV label="Industry ROIC"          value={fmtPct(ind.roic)}
                                             tooltip={damodaran("EVA.xls", "ROIC", ind.industry_name)} />
        </div>
      </Section>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Segment editor (shared between business segments and geographic segments)
// ──────────────────────────────────────────────────────────────────────────

interface SegCol {
  key: string;
  label: string;
  type: 'text' | 'number';
}

function SegmentEditor({
  title,
  columns,
  rows,
  onChange,
  blankRow,
  hint,
}: {
  title: string;
  columns: SegCol[];
  rows: Record<string, string | number | null>[];
  onChange: (rows: Record<string, string | number | null>[]) => void;
  blankRow: Record<string, string | number | null>;
  hint?: string;
}) {
  const setCell = (rowIdx: number, key: string, val: string) => {
    const copy = rows.map(r => ({ ...r }));
    const col = columns.find(c => c.key === key);
    copy[rowIdx][key] = col?.type === 'number' ? (parseFloat(val) || 0) : val;
    onChange(copy);
  };

  const addRow = () => onChange([...rows, { ...blankRow }]);
  const delRow = (i: number) => onChange(rows.filter((_, idx) => idx !== i));

  return (
    <div className="mt-3 border border-gray-300 rounded">
      <div className="bg-gray-100 px-3 py-1.5 border-b border-gray-300 flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-700">{title}</span>
        <button
          onClick={addRow}
          className="text-xs bg-indigo-600 text-white px-2 py-0.5 rounded hover:bg-indigo-700"
        >+ Add row</button>
      </div>
      {hint && <p className="text-xs text-gray-500 px-3 py-1 bg-gray-50">{hint}</p>}
      <table className="w-full text-xs">
        <thead className="bg-gray-50">
          <tr>
            {columns.map(c => <th key={c.key} className="px-2 py-1 text-left font-semibold text-gray-600">{c.label}</th>)}
            <th className="w-8"></th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr><td colSpan={columns.length + 1} className="px-2 py-3 text-center text-gray-400">No segments yet — click "Add row".</td></tr>
          )}
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-gray-100">
              {columns.map(c => (
                <td key={c.key} className="px-1 py-1">
                  <input
                    type={c.type}
                    defaultValue={r[c.key] ?? ''}
                    onBlur={(e) => setCell(i, c.key, e.target.value)}
                    className="w-full border border-gray-200 rounded px-1 py-0.5 text-xs"
                  />
                </td>
              ))}
              <td className="px-1 py-1 text-center">
                <button onClick={() => delRow(i)} className="text-red-500 hover:text-red-700 text-xs">✕</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
