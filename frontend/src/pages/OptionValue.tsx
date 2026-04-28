import type { ValuationResponse } from '../types/valuation';
import SpreadsheetCell from '../components/SpreadsheetCell';
import SpreadsheetGrid from '../components/SpreadsheetGrid';
import ColorLegend from '../components/ColorLegend';

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
  function inputRow(label: string, value: number | string | null | undefined) {
    return (
      <tr>
        <SpreadsheetCell value={label} type="label" align="left" width="280px" />
        <SpreadsheetCell value={typeof value === 'string' ? value : fmtNum(value)} type="hypothesis" />
      </tr>
    );
  }

  /** Single calc row: label + value */
  function calcRow(label: string, value: number | string | null | undefined) {
    return (
      <tr>
        <SpreadsheetCell value={label} type="label" align="left" width="280px" />
        <SpreadsheetCell value={typeof value === 'string' ? value : fmtNum(value)} type="calc" />
      </tr>
    );
  }

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
              {inputRow('Stock price', fmtNum(fin0?.stock_price))}
              {inputRow('Average strike price', fmtNum(opt.average_strike_price))}
              {inputRow('Average expiration (years)', fmtNum(opt.average_maturity))}
              {inputRow('Standard deviation', pct(opt.stock_price_std_dev))}
              {inputRow('Dividend yield', pct(opt.dividend_yield))}
              {inputRow('Risk-free rate', pct(macro.risk_free_rate))}
              {inputRow('Number of options', fmtNum(opt.number_of_options))}
              {inputRow('Number of shares', fmtNum(fin0?.shares_outstanding))}
              {inputRow('Has options', opt.has_options ? 'Yes' : 'No')}
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
              )}
              {calcRow('K (strike price)', fmtNum(opt.average_strike_price))}
              {calcRow('t (time to expiration)', fmtNum(opt.average_maturity))}
              {calcRow('sigma (std dev)', pct(opt.stock_price_std_dev))}
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
              )}
              {calcRow('Value per option', fmtNum(fin?.call_value_per_option))}
              {calcRow('Total value of options', fmtNum(fin?.value_of_all_options))}
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
