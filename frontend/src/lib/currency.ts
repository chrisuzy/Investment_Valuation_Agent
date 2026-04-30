/**
 * Currency formatting + FX conversion helpers.
 *
 * Convention across the app:
 *   - ALL monetary numbers are displayed with an explicit currency code suffix.
 *   - When a number can be shown in both listing and reporting currency, render
 *     the reporting-ccy value as primary (for WACC-math consistency) and the
 *     listing-ccy value as secondary via <DualCurrency>.
 *   - fx_rate multiplies a LISTING-ccy value to yield a REPORTING-ccy value.
 *
 * Example for Lenovo (listing HKD, reporting USD, fx_rate ≈ 0.128):
 *   stock_price = 11.83 HKD      (listing)
 *   stock_price_reporting = 1.52 USD (= 11.83 × 0.128)
 */

/** Symbols we recognize; others fall through to plain `amount CCY`. */
const CURRENCY_SYMBOL: Record<string, string> = {
  USD: "$",
  CAD: "C$",
  AUD: "A$",
  NZD: "NZ$",
  HKD: "HK$",
  SGD: "S$",
  TWD: "NT$",
  GBP: "£",
  EUR: "€",
  JPY: "¥",
  CNY: "¥",
  CHF: "CHF ",
  KRW: "₩",
  INR: "₹",
  RUB: "₽",
  TRY: "₺",
  ZAR: "R",
  BRL: "R$",
};

export function fmtMoney(
  value: number | null | undefined,
  ccy: string | null | undefined,
  decimals = 2,
): string {
  if (value == null || Number.isNaN(value)) return "—";
  const sym = ccy ? CURRENCY_SYMBOL[ccy] ?? "" : "";
  const abs = Math.abs(value);
  const formatted =
    abs >= 1e9
      ? (value / 1e9).toLocaleString("en-US", { maximumFractionDigits: 2 }) + "B"
      : abs >= 1e6
      ? (value / 1e6).toLocaleString("en-US", { maximumFractionDigits: 1 }) + "M"
      : value.toLocaleString("en-US", { maximumFractionDigits: decimals, minimumFractionDigits: decimals });
  if (sym) return `${sym}${formatted}${ccy && !CURRENCY_SYMBOL[ccy] ? "" : ""}${ccy ? ` ${ccy}` : ""}`;
  return ccy ? `${formatted} ${ccy}` : formatted;
}

/** Short form: "$2.37" or "HK$11.83" — used inline when the currency is obvious from context. */
export function fmtMoneyShort(
  value: number | null | undefined,
  ccy: string | null | undefined,
  decimals = 2,
): string {
  if (value == null || Number.isNaN(value)) return "—";
  const sym = ccy ? CURRENCY_SYMBOL[ccy] ?? "" : "";
  const formatted = value.toLocaleString("en-US", { maximumFractionDigits: decimals, minimumFractionDigits: decimals });
  if (sym) return `${sym}${formatted}`;
  return ccy ? `${formatted} ${ccy}` : formatted;
}

/** FX banner string: "1 HKD = 0.1286 USD  (CIQ, 2025-06-30)" */
export function fmtFxRate(
  fxRate: number | null | undefined,
  listingCcy: string | null | undefined,
  reportingCcy: string | null | undefined,
  source: string | null | undefined,
  date: string | null | undefined,
): string {
  if (fxRate == null || listingCcy == null || reportingCcy == null) return "FX rate unavailable";
  if (listingCcy === reportingCcy) return `${listingCcy} (no conversion)`;
  const rate = fxRate.toFixed(6).replace(/\.?0+$/, "");
  const meta = [source, date].filter(Boolean).join(", ");
  return `1 ${listingCcy} = ${rate} ${reportingCcy}${meta ? `  (${meta})` : ""}`;
}

/** Convert a LISTING-currency value to REPORTING currency using fx_rate. */
export function toReporting(valueListing: number | null | undefined, fxRate: number | null | undefined): number | null {
  if (valueListing == null || fxRate == null) return null;
  return valueListing * fxRate;
}

/** Convert a REPORTING-currency value to LISTING currency (for showing VPS in exchange ccy). */
export function toListing(valueReporting: number | null | undefined, fxRate: number | null | undefined): number | null {
  if (valueReporting == null || fxRate == null || fxRate === 0) return null;
  return valueReporting / fxRate;
}
