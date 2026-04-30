/**
 * Tooltip source composers — every number in the UI should trace back to
 * one of: CIQ data, Damodaran reference data, a computed formula, or a
 * user hypothesis / Ginzu-default override.
 *
 * Use these helpers so tooltip formatting stays consistent across pages.
 * Matches the Input Sheet's established conventions.
 */

/** CIQ formula as shown to the user — the raw mnemonic + period they'd type in Excel. */
export function ciq(ticker: string | null | undefined, mnemonic: string, period?: string): string {
  const t = ticker || "TICKER";
  return period ? `=CIQ("${t}","${mnemonic}","${period}")` : `=CIQ("${t}","${mnemonic}")`;
}

/** Damodaran file/column lookup — for β, industry WACC, country ERP, etc. */
export function damodaran(file: string, column: string, industry_or_country?: string): string {
  const loc = industry_or_country ? ` → ${industry_or_country}` : "";
  return `Damodaran ${file} → Industry Averages${loc} → "${column}" (Jan 2026 vintage)`;
}

/** Country-level macro lookup from the ctryprem / countrytaxrates files. */
export function country(kind: "ERP" | "CRP" | "Tax" | "DefaultSpread" | "Rating", name: string): string {
  const file = kind === "Tax" ? "countrytaxrates.xls" : "ctryprem.xlsx";
  return `Damodaran ${file} → ${name} → ${kind}`;
}

/** Computed formula. Pass the formula plus numeric substitution for clarity. */
export function formula(expression: string, substitution?: string): string {
  return substitution ? `${expression}\n  = ${substitution}` : expression;
}

/** User hypothesis — value that can be analyst-overridden. Optionally mention Ginzu default. */
export function user(field: string, defaultRule?: string): string {
  return defaultRule
    ? `User hypothesis: ${field} (Ginzu default: ${defaultRule})`
    : `User hypothesis: ${field}`;
}

/** Fixed-point iteration result (BSM options). */
export function iterated(description: string): string {
  return `Fixed-point iteration — ${description}`;
}

/** Pass-through from a Pydantic model field in the backend response. */
export function backendField(path: string, note?: string): string {
  return note ? `Backend: report.${path}  (${note})` : `Backend: report.${path}`;
}

/** Ginzu methodology reference pointer. */
export function ginzu(sheet_and_cell: string, note?: string): string {
  return note ? `Ginzu workbook ${sheet_and_cell}  — ${note}` : `Ginzu workbook ${sheet_and_cell}`;
}

// ──────────────────────────────────────────────────────────────────────────
// Field-path registry — common numbers get a canonical tooltip here so each
// page doesn't have to reinvent them.
// ──────────────────────────────────────────────────────────────────────────

type CoCData = {
  approach_used?: string; beta_branch_used?: string; erp_branch_used?: string; kd_branch_used?: string;
  beta_u?: number; beta_l?: number;
  d_e_ratio?: number; mv_equity?: number; mv_debt_total?: number; mv_preferred?: number;
  weight_equity?: number; weight_debt?: number; weight_preferred?: number;
  cost_of_equity?: number; cost_of_debt_pretax?: number; cost_of_debt_aftertax?: number;
  cost_of_preferred?: number; risk_free_rate?: number; equity_risk_premium?: number;
  wacc?: number; synthetic_rating?: string | null; interest_coverage_ratio?: number | null;
};

export function tooltipFor(
  path: string,
  ctx: { ticker?: string | null; industry?: string | null; country?: string | null;
         taxRate?: number | null; coc?: CoCData | null }
): string {
  const t = ctx.ticker;
  const c = ctx.coc || {};

  // Compact formatter for embedded numbers
  const f = (v: number | null | undefined, pct = false, dp = 4) =>
    v == null ? "?" : pct ? `${(v * 100).toFixed(2)}%` : v.toFixed(dp);

  switch (path) {
    // ── Cost of Capital ──
    case "cost_of_capital.beta_u":
      return damodaran("betas.xls", "Unlevered beta corrected for cash", ctx.industry || undefined)
           + ` (${c.beta_branch_used || "Single Business(US)"})`;

    case "cost_of_capital.beta_l": {
      const bu = f(c.beta_u); const t2 = f(ctx.taxRate, true); const de = f(c.d_e_ratio);
      return formula("β_L = β_u × [1 + (1 − t) × D/E]",
                     `${bu} × [1 + (1 − ${t2}) × ${de}] = ${f(c.beta_l)}`);
    }

    case "cost_of_capital.equity_risk_premium":
      if (c.erp_branch_used === "country_of_incorporation")
        return country("ERP", ctx.country || "?") + " + CRP";
      if (c.erp_branch_used?.startsWith("operating_"))
        return `Revenue-weighted ERP blend (${c.erp_branch_used})`;
      return `ERP = ${f(c.equity_risk_premium, true)} (${c.erp_branch_used || "?"})`;

    case "cost_of_capital.cost_of_equity":
      return formula("Ke = RF + β_L × ERP",
                     `${f(c.risk_free_rate, true)} + ${f(c.beta_l)} × ${f(c.equity_risk_premium, true)} = ${f(c.cost_of_equity, true)}`);

    case "cost_of_capital.cost_of_debt_pretax":
      if (c.kd_branch_used === "industry_fallback")
        return damodaran("wacc.xls", "Cost of Debt (pre-tax)", ctx.industry || undefined);
      if (c.kd_branch_used?.startsWith("synthetic_rating"))
        return `Synthetic rating: coverage ${f(c.interest_coverage_ratio, false, 2)} → rating ${c.synthetic_rating} → RF + spread`;
      if (c.kd_branch_used?.startsWith("actual_rating"))
        return `Actual rating: RF + rating spread`;
      return "Direct input";

    case "cost_of_capital.cost_of_debt_aftertax":
      return formula("Kd_aftertax = Kd_pretax × (1 − t)",
                     `${f(c.cost_of_debt_pretax, true)} × (1 − ${f(ctx.taxRate, true)}) = ${f(c.cost_of_debt_aftertax, true)}`);

    case "cost_of_capital.weight_equity":
      return formula("W_e = MV_equity / (MV_equity + MV_debt + MV_preferred)",
                     `${f(c.mv_equity, false, 0)} / ${f((c.mv_equity||0)+(c.mv_debt_total||0)+(c.mv_preferred||0), false, 0)} = ${f(c.weight_equity, true)}`);

    case "cost_of_capital.weight_debt":
      return formula("W_d = MV_debt / Total Capital",
                     `${f(c.mv_debt_total, false, 0)} / ${f((c.mv_equity||0)+(c.mv_debt_total||0)+(c.mv_preferred||0), false, 0)} = ${f(c.weight_debt, true)}`);

    case "cost_of_capital.wacc":
      return formula("WACC = W_e·Ke + W_d·Kd_at + W_p·Kp",
                     `${f(c.weight_equity, true)}·${f(c.cost_of_equity, true)} + ${f(c.weight_debt, true)}·${f(c.cost_of_debt_aftertax, true)} = ${f(c.wacc, true)}`);

    case "cost_of_capital.d_e_ratio":
      return formula("D/E = MV_debt / MV_equity",
                     `${f(c.mv_debt_total, false, 0)} / ${f(c.mv_equity, false, 0)} = ${f(c.d_e_ratio)}`);

    case "cost_of_capital.mv_equity":
      return ciq(t, "IQ_MARKETCAP");

    case "cost_of_capital.mv_debt_total":
      return "MV straight debt + MV convertible-straight-part + MV leases";
  }
  return ""; // no registry entry; caller can pass a custom tooltip
}
