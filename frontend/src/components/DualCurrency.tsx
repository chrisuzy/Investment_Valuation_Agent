import { fmtMoneyShort, toListing } from '../lib/currency';

/**
 * Inline dual-currency display. Shows the reporting-currency value as primary
 * and the listing-currency equivalent in parentheses. Collapses to single
 * rendering when both currencies match or FX is unavailable.
 *
 * Usage:
 *   <DualCurrency valueReporting={2.37} reportingCcy="USD" listingCcy="HKD" fxRate={0.128} />
 *   → "$2.37 USD  (≈ HK$18.45)"
 */
export default function DualCurrency({
  valueReporting,
  valueListing,
  reportingCcy,
  listingCcy,
  fxRate,
  decimals = 2,
  primary = "reporting",
}: {
  valueReporting?: number | null;
  valueListing?: number | null;
  reportingCcy: string | null | undefined;
  listingCcy: string | null | undefined;
  fxRate?: number | null;
  decimals?: number;
  primary?: "reporting" | "listing";
}) {
  // Derive missing side from whichever is provided + FX
  const rep = valueReporting ?? (valueListing != null && fxRate != null ? valueListing * fxRate : null);
  const lst = valueListing ?? toListing(valueReporting, fxRate);

  const sameCcy = reportingCcy && listingCcy && reportingCcy === listingCcy;
  if (sameCcy || lst == null || rep == null) {
    const v = primary === "reporting" ? rep : lst;
    const c = primary === "reporting" ? reportingCcy : listingCcy;
    return <span className="tabular-nums">{fmtMoneyShort(v, c, decimals)}</span>;
  }

  const mainVal = primary === "reporting" ? rep : lst;
  const mainCcy = primary === "reporting" ? reportingCcy : listingCcy;
  const altVal = primary === "reporting" ? lst : rep;
  const altCcy = primary === "reporting" ? listingCcy : reportingCcy;
  return (
    <span className="tabular-nums">
      {fmtMoneyShort(mainVal, mainCcy, decimals)}
      <span className="text-gray-500 ml-1">
        (≈ {fmtMoneyShort(altVal, altCcy, decimals)})
      </span>
    </span>
  );
}
