# API Design — FastAPI Backend

## Overview

The FastAPI backend serves as the bridge between the React frontend and the valuation engine. It handles data upload, session management, and exposes endpoints for running and interacting with valuations.

## Base URL

```
http://localhost:8000/api
```

---

## Endpoints

### Valuation Lifecycle

#### `POST /api/valuation/fetch`

Trigger a new valuation by fetching data for a ticker.

**Request:**
```json
{
  "ticker": "AAPL",
  "industry_override": null
}
```

**Response:**
```json
{
  "session_id": "uuid-1234",
  "status": "data_fetched",
  "data": {
    "raw_financials": [...],
    "adjustment_inputs": {...},
    "macro_inputs": {...},
    "industry_data": {...}
  },
  "warnings": ["CapIQ: field 'mv_debt' returned N/A, using book value"]
}
```

**Behavior:**
1. Launches CapIQ Excel automation for the ticker
2. Looks up Damodaran datasets by auto-mapped industry
3. Creates a session with fetched data
4. Returns data for frontend to display in the "Data Input" tab

---

#### `POST /api/valuation/{session_id}/run`

Run the full valuation pipeline (or from a specific module).

**Request:**
```json
{
  "from_module": null
}
```
- `from_module: null` → run M1 through M6
- `from_module: 2` → re-run from M2 onward (M2, M3, M4, M5, M6)

**Response:**
```json
{
  "session_id": "uuid-1234",
  "status": "completed",
  "results": {
    "module_1": { "adjusted_ebit": 134520.5, "adjusted_bv_equity": 89200.0, ... },
    "module_2": { "beta_l": 1.15, "wacc": 0.0892, ... },
    "module_3": { "fcff": 85430.0, "roic": 0.285, ... },
    "module_4": { "value_per_share_pre_options": 198.50, ... },
    "module_5": { "pe_ratio_intrinsic": 22.5, ... },
    "module_6": { "value_per_share": 195.20, ... }
  },
  "validation_warnings": []
}
```

---

#### `PATCH /api/valuation/{session_id}`

User edits a value (overrides an input or intermediate).

**Request:**
```json
{
  "overrides": [
    { "variable": "beta_u", "value": 1.35, "module": 2 },
    { "variable": "stable_growth_rate", "value": 0.03, "module": 4 }
  ]
}
```

**Response:** Same structure as `/run`, but only recomputes affected modules. Also returns `affected_modules: [2, 3, 4, 5, 6]` to tell the frontend which tabs have updated data.

---

#### `GET /api/valuation/{session_id}`

Retrieve current state of a valuation session.

**Response:** Full session state including all inputs, overrides, and module outputs.

---

### Damodaran Data Management

#### `POST /api/damodaran/upload`

Upload a Damodaran Excel dataset.

**Request:** `multipart/form-data`
- `file`: Excel file
- `dataset_type`: one of `erp`, `betas`, `tax_rates`, `cost_of_capital`

**Response:**
```json
{
  "dataset_type": "betas",
  "industries_loaded": 96,
  "last_updated": "2026-01-15"
}
```

---

#### `GET /api/damodaran/industries`

List all Damodaran industries currently loaded (for dropdown/mapping).

**Response:**
```json
{
  "industries": [
    { "name": "Software (System & Application)", "beta_u": 1.28, "d_e_ratio": 0.05 },
    { "name": "Computers/Peripherals", "beta_u": 1.15, "d_e_ratio": 0.12 },
    ...
  ]
}
```

---

#### `GET /api/damodaran/lookup?industry=Software&country=US`

Query specific industry/macro data.

---

### Capital IQ Fallback

#### `POST /api/capiq/upload`

Manual fallback: upload a filled CapIQ Excel export.

**Request:** `multipart/form-data` with the Excel file.

**Response:** Parsed `RawFinancials` + `AdjustmentInputs`, same format as the fetch endpoint.

---

## Session Management

### Session State Model

```python
class ValuationSession:
    session_id: str
    ticker: str
    created_at: datetime

    # Inputs (fetched or uploaded)
    raw_financials: list[RawFinancials]
    adjustment_inputs: AdjustmentInputs
    macro_inputs: MacroInputs
    industry_data: IndustryData

    # User overrides
    overrides: dict[str, Any]  # variable_name → user value

    # Module outputs (computed)
    module_outputs: dict[int, BaseModel]  # module_number → output model

    # Assumptions
    valuation_assumptions: ValuationAssumptions
```

### Storage

- **Phase 1:** In-memory dict `{session_id: ValuationSession}`. Sessions expire after 24 hours.
- **Phase 2 (future):** SQLite or PostgreSQL for persistent sessions, allowing users to save and revisit valuations.

### Incremental Recomputation

When an override arrives:
1. Determine which module the variable belongs to (via a reverse lookup table)
2. Apply the override to the session state
3. Re-run that module and all downstream modules
4. Update `module_outputs` in the session
5. Return the delta (which modules changed)

```
Variable ownership:
  M0 inputs: ticker, industry_override
  M1 inputs: raw financials, adjustment inputs, cost_of_debt_pretax
  M2 inputs: beta_u, risk_free_rate, equity_risk_premium, tax_rate_marginal
  M3 inputs: (no direct user inputs — derived from M1 + M2)
  M4 inputs: projection_years, stable_growth_rate, high_growth_rate_override
  M5 inputs: (derived from M1 + M2 + M3)
  M6 inputs: option_s, option_k, option_t, option_variance, option_y
```

---

## Error Handling

| Error | HTTP Status | Behavior |
|-------|-------------|----------|
| CapIQ automation timeout | 503 | Return partial data + `fallback_url` for manual upload |
| Damodaran data not loaded | 422 | Return `missing_datasets` list |
| Validation constraint violated | 422 | Return `{ constraint: "stable_growth_rate <= risk_free_rate", actual: ... }` |
| Session not found | 404 | Standard not found |
| Excel parse error | 400 | Return column-level error details |

## CORS

Frontend runs on `localhost:3000`, backend on `localhost:8000`. FastAPI CORS middleware configured for local development.
