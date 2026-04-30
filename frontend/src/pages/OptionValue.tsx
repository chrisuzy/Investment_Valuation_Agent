import type { ValuationResponse } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';
import { ciq, formula, iterated, user, backendField } from '../lib/sources';

// ---------- helpers ----------

function fmtNum(v: number | null | undefined): number | string {
  if (v === null || v === undefined) return '';
  return v;
}

function pct(v: number | null | undefined): string {
  if (v === null || v === undefined) return '';
  return (v * 100).toFixed(2) + '%';
}

// ---------- component ----------

export default function OptionValue({ data, sessionId }: { data: ValuationResponse; sessionId?: string | null }) {
  const opt = data.inputs.option_inputs;
  const fin0 = data.inputs.raw_financials[0];
  const macro = data.inputs.macro_inputs;
  const fin = data.final;

  // ---------- render helpers ----------

  /** Single input row: label + value */
  function inputRow(label: string, value: number | string | null | undefined, tooltip?: string) {
    return (
      <tr>
        <SpreadsheetCell value={label} type="label" align="left" width="280px" />
        <SpreadsheetCell value={typeof value === 'string' ? value : fmtNum(value)} type="hypothesis" tooltip={tooltip} />
      </tr>
    );
  }

  /** Single calc row: label + value */
  function calcRow(label: string, value: number | string | null | undefined, tooltip?: string) {
    return (
      <tr>
        <SpreadsheetCell value={label} type="label" align="left" width="280px" />
        <SpreadsheetCell value={typeof value === 'string' ? value : fmtNum(value)} type="calc" tooltip={tooltip} />
      </tr>
    );
  }

  const ticker = data.inputs.ticker;

  // ---------- render ----------

  return (
    <div className="p-4 max-w-4xl">
      <h2 className="text-lg font-bold mb-4">Option Value (Black-Scholes)</h2>

      <ColorLegend />

      {!opt.has_options ? (
        <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded text-gray-500">
          No employee options outstanding.
        </div>
      ) : (
        <>
          {/* ===== Section 1: Option Inputs ===== */}
          <SpreadsheetGrid title="Option Inputs">
            <tbody>
              {inputRow('Stock price', fmtNum(fin0?.stock_price),
                ciq(ticker, 'IQ_CLOSEPRICE'))}
              {inputRow('Average strike price', fmtNum(opt.average_strike_price),
                user('Average strike of outstanding employee options', 'From 10-K footnote on stock-based compensation'))}
              {inputRow('Average expiration (years)', fmtNum(opt.average_maturity),
                user('Weighted-average remaining life of outstanding options', 'From 10-K footnote'))}
              {inputRow('Standard deviation', pct(opt.stock_price_std_dev),
                user('Annualized volatility of stock returns', 'Typically 30-60% for public equities; use 3-5 year rolling std dev of weekly returns × √52'))}
              {inputRow('Dividend yield', pct(opt.dividend_yield),
                ciq(ticker, 'IQ_DIV_YIELD'))}
              {inputRow('Risk-free rate', pct(macro.risk_free_rate),
                user('Risk-free rate (10y T-bond)', 'Same RF used in WACC'))}
              {inputRow('Number of options', fmtNum(opt.number_of_options),
                user('Total outstanding options/warrants', 'From 10-K footnote'))}
              {inputRow('Number of shares', fmtNum(fin0?.shares_outstanding),
                ciq(ticker, 'IQ_BASIC_WEIGHT', 'IQ_FQ-0'))}
              {inputRow('Has options', opt.has_options ? 'Yes' : 'No',
                'Toggle: when false, option value = 0 and this page skips BSM')}
            </tbody>
          </SpreadsheetGrid>

          {/* ===== Section 2: Dilution-Adjusted Black-Scholes ===== */}
          <SpreadsheetGrid title="Dilution-Adjusted Black-Scholes">
            <tbody>
              {calcRow(
                'Adjusted S (dilution-adjusted stock price)',
                fin0?.stock_price != null &&
                  fin0?.shares_outstanding != null &&
                  opt.number_of_options != null
                  ? fmtNum(
                      (fin0.stock_price * fin0.shares_outstanding +
                        opt.average_strike_price * opt.number_of_options) /
                        (fin0.shares_outstanding + opt.number_of_options),
                    )
                  : '',
                iterated('Adjusted S = (S·N_shares + K·N_options) / (N_shares + N_options). The backend iterates Adjusted_S ↔ call_value to convergence (≤20 iters, $0.01 tolerance) because dilution depends on the call value which depends on the adjusted price.'),
              )}
              {calcRow('K (strike price)', fmtNum(opt.average_strike_price),
                'Echo of input — average strike of outstanding options')}
              {calcRow('t (time to expiration)', fmtNum(opt.average_maturity),
                'Echo of input — weighted-average remaining life')}
              {calcRow('sigma (std dev)', pct(opt.stock_price_std_dev),
                'Echo of input — annualized volatility')}
              {calcRow(
                'd1',
                (() => {
                  const S =
                    fin0?.stock_price != null &&
                    fin0?.shares_outstanding != null &&
                    opt.number_of_options != null
                      ? (fin0.stock_price * fin0.shares_outstanding +
                          opt.average_strike_price * opt.number_of_options) /
                        (fin0.shares_outstanding + opt.number_of_options)
                      : null;
                  const K = opt.average_strike_price;
                  const t = opt.average_maturity;
                  const sigma = opt.stock_price_std_dev;
                  const r = macro.risk_free_rate;
                  const y = opt.dividend_yield;
                  if (S == null || K === 0 || t === 0 || sigma === 0) return '';
                  const d1 =
                    (Math.log(S / K) + (r - y + (sigma * sigma) / 2) * t) /
                    (sigma * Math.sqrt(t));
                  return d1.toFixed(4);
                })(),
                formula('d1 = [ln(S/K) + (r − y + σ²/2)·t] / (σ·√t)',
                        'Black-Scholes drift-adjusted term for call value.'),
              )}
              {calcRow(
                'N(d1)',
                (() => {
                  const S =
                    fin0?.stock_price != null &&
                    fin0?.shares_outstanding != null &&
                    opt.number_of_options != null
                      ? (fin0.stock_price * fin0.shares_outstanding +
                          opt.average_strike_price * opt.number_of_options) /
                        (fin0.shares_outstanding + opt.number_of_options)
                      : null;
                  const K = opt.average_strike_price;
                  const t = opt.average_maturity;
                  const sigma = opt.stock_price_std_dev;
                  const r = macro.risk_free_rate;
                  const y = opt.dividend_yield;
                  if (S == null || K === 0 || t === 0 || sigma === 0) return '';
                  const d1 =
                    (Math.log(S / K) + (r - y + (sigma * sigma) / 2) * t) /
                    (sigma * Math.sqrt(t));
                  return normCdf(d1).toFixed(4);
                })(),
                'N(d1) = Standard-normal CDF at d1 (Abramowitz & Stegun approximation)',
              )}
              {calcRow(
                'd2',
                (() => {
                  const S =
                    fin0?.stock_price != null &&
                    fin0?.shares_outstanding != null &&
                    opt.number_of_options != null
                      ? (fin0.stock_price * fin0.shares_outstanding +
                          opt.average_strike_price * opt.number_of_options) /
                        (fin0.shares_outstanding + opt.number_of_options)
                      : null;
                  const K = opt.average_strike_price;
                  const t = opt.average_maturity;
                  const sigma = opt.stock_price_std_dev;
                  const r = macro.risk_free_rate;
                  const y = opt.dividend_yield;
                  if (S == null || K === 0 || t === 0 || sigma === 0) return '';
                  const d2 =
                    (Math.log(S / K) + (r - y - (sigma * sigma) / 2) * t) /
                    (sigma * Math.sqrt(t));
                  return d2.toFixed(4);
                })(),
                formula('d2 = d1 − σ·√t = [ln(S/K) + (r − y − σ²/2)·t] / (σ·√t)'),
              )}
              {calcRow(
                'N(d2)',
                (() => {
                  const S =
                    fin0?.stock_price != null &&
                    fin0?.shares_outstanding != null &&
                    opt.number_of_options != null
                      ? (fin0.stock_price * fin0.shares_outstanding +
                          opt.average_strike_price * opt.number_of_options) /
                        (fin0.shares_outstanding + opt.number_of_options)
                      : null;
                  const K = opt.average_strike_price;
                  const t = opt.average_maturity;
                  const sigma = opt.stock_price_std_dev;
                  const r = macro.risk_free_rate;
                  const y = opt.dividend_yield;
                  if (S == null || K === 0 || t === 0 || sigma === 0) return '';
                  const d2 =
                    (Math.log(S / K) + (r - y - (sigma * sigma) / 2) * t) /
                    (sigma * Math.sqrt(t));
                  return normCdf(d2).toFixed(4);
                })(),
                'N(d2) = Standard-normal CDF at d2 — interprets as risk-neutral probability of finishing in-the-money',
              )}
              {calcRow('Value per option', fmtNum(fin?.call_value_per_option),
                formula('Call = S·e^(−y·t)·N(d1) − K·e^(−r·t)·N(d2)',
                        'Black-Scholes-Merton with continuous dividend yield. Output after fixed-point iteration converges.') + ' — ' + backendField('final.call_value_per_option'))}
              {calcRow('Total value of options', fmtNum(fin?.value_of_all_options),
                formula('Total = Call × N_options') + ' — ' + backendField('final.value_of_all_options') + ' (subtracted from equity value in bridge)')}
            </tbody>
          </SpreadsheetGrid>
        </>
      )}
    </div>
  );
}

// ---------- Normal CDF approximation (Abramowitz & Stegun) ----------

function normCdf(x: number): number {
  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const p = 0.3275911;

  const sign = x < 0 ? -1 : 1;
  const z = Math.abs(x) / Math.SQRT2;
  const t = 1.0 / (1.0 + p * z);
  const y = 1.0 - ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t * Math.exp(-z * z);

  return 0.5 * (1.0 + sign * y);
}
