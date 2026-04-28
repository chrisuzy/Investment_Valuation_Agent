"""
LTM (Trailing Twelve Month) Calculator — Ginzu formula.

Per the Ginzu `Trailing 12 month` sheet (rows 2,3,4,5 → E = B − C + D):

  For flow items:  LTM = Last_10K − Prior_Year_YTD + Current_Year_YTD
  For balance sheet items: use most recent 10-Q point-in-time value (no rotation).

Where YTDs are aligned by calendar window: if K quarters have elapsed since the
last fiscal year end, Current_YTD = FQ-0..FQ-(K-1) and Prior_YTD = FQ-4..FQ-(K+3).
"""

from __future__ import annotations

from .data_dictionary import RawFinancials


FLOW_FIELDS = {
    "revenues", "ebit", "ebitda", "net_income", "interest_expense",
    "d_a", "capex", "r_and_d_expense", "earnings_before_tax", "total_tax_expense",
    "change_in_noncash_wc", "net_debt_issued",
}

BALANCE_SHEET_FIELDS = {
    "cash_and_marketable_securities", "bv_equity", "bv_debt",
    "noncash_wc", "shares_outstanding", "cross_holdings", "minority_interests",
    "mv_equity", "mv_debt", "stock_price",
}


def compute_ltm_financials(
    fy0: RawFinancials,
    quarterly: list[RawFinancials],
    quarters_since_10k: int,
) -> RawFinancials:
    """Build a RawFinancials with LTM-rotated flow values + FQ-0 balance-sheet snapshot.

    If quarters_since_10k == 0, returns FY0 unchanged.
    If insufficient quarterly data (have fewer than K+4 quarters), falls back to FY0 flows.
    """
    K = max(0, min(4, quarters_since_10k))

    if K == 0:
        # No rotation needed — most recent 10-Q is the 10-K itself
        return fy0.model_copy()

    sufficient = len(quarterly) >= K + 4
    data = fy0.model_dump()

    for field in FLOW_FIELDS:
        fy0_val = data.get(field)
        if fy0_val is None:
            continue
        if not sufficient:
            continue  # keep FY0 value; no rotation possible
        current_sum = 0.0
        prior_sum = 0.0
        for i in range(K):
            cv = getattr(quarterly[i], field, None)
            pv = getattr(quarterly[i + 4], field, None)
            if cv is not None:
                current_sum += cv
            if pv is not None:
                prior_sum += pv
        data[field] = fy0_val - prior_sum + current_sum

    # Balance sheet: FQ-0 snapshot, fallback to FY0
    if quarterly:
        for field in BALANCE_SHEET_FIELDS:
            qv = getattr(quarterly[0], field, None)
            if qv is not None:
                data[field] = qv

    return RawFinancials(**data)


# Back-compat shim — some older test modules may reference this.
def compute_ltm(annual_fy0, quarterly_data, months_since_fy_end: int = 0):
    """DEPRECATED. Use compute_ltm_financials(RawFinancials, ...) instead."""
    K = max(0, min(4, months_since_fy_end // 3))
    if K == 0 or not quarterly_data:
        return dict(annual_fy0)
    result = dict(annual_fy0)
    sufficient = len(quarterly_data) >= K + 4
    for field in FLOW_FIELDS:
        if not sufficient or result.get(field) is None:
            continue
        cur = sum((quarterly_data[i].get(field) or 0) for i in range(K))
        prior = sum((quarterly_data[i + 4].get(field) or 0) for i in range(K))
        result[field] = result[field] - prior + cur
    for field in BALANCE_SHEET_FIELDS:
        if quarterly_data[0].get(field) is not None:
            result[field] = quarterly_data[0][field]
    return result
