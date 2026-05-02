# Ginzu DCF Engine

A faithful, open-source implementation of Aswath Damodaran's *Ginzu*
discounted-cash-flow valuation workbook as a full-stack web application.

Covers every module Ginzu does — LTM rotation, R&D capitalization,
operating-lease conversion, full cost-of-capital with 4 approaches / 6 β
variants / 4 ERP variants / 4 Kd variants, 10-year DCF projection, terminal
value, failure overlay, iterative Black-Scholes options dilution, equity
bridge, per-share intrinsic value. Ships with a React frontend that
mirrors Ginzu's worksheet layout and exposes every methodology choice
as a dropdown.

---

## Why

Damodaran's spreadsheet is the gold standard for intrinsic valuation but
it's a black-box Excel file. This project reimplements it as auditable
code so every number traces to a formula, every assumption is an explicit
user choice, and every intermediate value is inspectable via hover
tooltips that show "this came from CIQ mnemonic X" or "this was computed
as β × (1 + (1−t)·D/E) = …".

Built alongside Damodaran's methodology documents, modeled for a
professional analyst workflow where the analyst wants:

- to see the **provenance of every number** (source, formula, which
  Damodaran dataset it came from);
- to **override any methodology choice** (β source, ERP approach, Kd
  approach, reinvestment lag, failure probability) and watch the
  downstream effect live;
- to run a DCF **on any publicly traded firm globally** — the engine
  handles 180+ countries, 10 Damodaran region aggregates, FX conversion
  between listing and reporting currencies, and graceful fallback when
  auto-resolution fails (e.g. an unmapped exchange or a ticker not in
  Damodaran's industry classification file).

---

## Architecture

```
┌──────────────────────┐      ┌──────────────────────┐
│  Frontend (React +   │◄────►│  Backend (FastAPI +   │
│  Vite + Tailwind)     │ HTTP │  Pydantic v2)         │
│                        │      │                        │
│  Input Sheet           │      │  M1  Adjustments       │
│  Summary Sheet         │      │  M2  Cost of Capital   │
│  Cost of Capital       │      │  M3  Cashflow & Growth │
│  Valuation Output      │      │  M4  DCF Projection    │
│  TTM / Relative /      │      │  M5  Multiples         │
│  Options / Failure /   │      │  M6  Options & Final   │
│  Segments / …          │      │                        │
└──────────────────────┘      └──────────────────────┘
                                      │
                              ┌───────┴───────┐
                              │ Damodaran     │
                              │ reference     │
                              │ data (local)  │
                              └───────────────┘
```

**Backend:** Python 3.12, FastAPI, Pydantic v2, openpyxl, xlrd, uvicorn.
**Frontend:** React 18, Vite 8, TypeScript, TailwindCSS, React Router,
Axios.

Every per-module calculation is documented in plain financial-reasoning
language under `docs/Ginzu understanding/` — read
[module_04_cost_of_capital.md](docs/Ginzu%20understanding/module_04_cost_of_capital.md)
for a representative sample.

---

## Quickstart

### Prerequisites

- Python 3.12+
- Node.js 18+ (for the frontend)
- Git

### 1. Clone

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```

### 2. Install backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Install frontend

```bash
cd ../frontend
npm install
```

### 4. Supply reference data

See [Data sources](#data-sources) below. At minimum you need:

- **Damodaran country/industry datasets** — download the `.xls` files
  from [pages.stern.nyu.edu/~adamodar/](https://pages.stern.nyu.edu/~adamodar/)
  and drop them under `knowledge_base/damodaran/`. The engine expects
  files like `betas.xls`, `betaGlobal.xls`, `ctryprem.xlsx`,
  `countrytaxrates.xls`, `wacc.xls`, `margin.xls`.

- **Damodaran industry classification** (`indname.xlsx`) — download
  from the same page, save to `knowledge_base/industry_lookup/indname.xlsx`.

- **Your own data-fetch template** (see below).

### 5. Run the stack

```bash
# Terminal A — backend on :8000
cd backend && source .venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal B — frontend dev server
cd frontend
npm run dev
```

Open `http://localhost:5173/` in a browser. Upload a populated data-fetch
workbook, get a full DCF valuation in seconds.

### 6. Verify

```bash
cd backend && source .venv/bin/activate
pytest tests/ -q
# Expected: 83 passed, 4 skipped
```

---

## Data sources

This project does **not** ship with any third-party data. You have three
options for supplying the per-company financial data needed to run a
valuation:

### Option 1 — Capital IQ Excel plug-in (recommended for professional users)

If you have access to S&P Capital IQ (via a Bloomberg-like terminal
subscription at a bank / investment firm / university), build a fetch
template in Excel using the plug-in's `=CIQ(...)` formulas. The schema
the backend expects is documented in
[`docs/DATA_FETCH_SCHEMA.md`](docs/DATA_FETCH_SCHEMA.md) — every field
name, period, and currency convention.

We do not redistribute a prebuilt Capital IQ template out of respect for
S&P's terms of service. You build your own following the schema.

The backend's template generator (`backend/tools/generate_ciq_template.py`)
can emit a template skeleton for you given the schema — but the
`=CIQ(...)` formulas only resolve if you have the plug-in installed.

### Option 2 — Any equivalent data source with the same schema

The backend reads an Excel workbook with a `_RowMap` sheet + a `CIQ_Data`
sheet. Any data source you can get into that format works. Providers that
commonly work:

- Bloomberg (via BQL or BDP formulas)
- Refinitiv / LSEG Workspace
- FactSet
- Your firm's internal data warehouse with an Excel export

Schema doc: [`docs/DATA_FETCH_SCHEMA.md`](docs/DATA_FETCH_SCHEMA.md).

### Option 3 — Contact the author

Open an issue on this repo describing the company you're trying to
value and the data source constraints you have. The maintainer may be
able to point you at a suitable resource or share access to a
pre-populated workbook for common test tickers (for educational /
non-commercial use).

**In all cases:** the project assumes you own or have licensed access to
the underlying financial data. Capital IQ / Bloomberg / FactSet
subscriptions are typical at investment firms and universities.

### Damodaran reference data

The engine also needs Damodaran's public datasets (country risk premiums,
industry betas, industry WACCs, etc.). Professor Damodaran publishes these
freely on his Stern page and they update annually. We do **not** bundle
them — download fresh from
[pages.stern.nyu.edu/~adamodar/](https://pages.stern.nyu.edu/~adamodar/)
under "Updated Data" and drop them into `knowledge_base/damodaran/`.

The backend uses 2026 vintage data as the default. When Damodaran updates
in early 2027, re-download and restart the backend.

---

## Features

### Full methodology selectors

Every Ginzu methodology choice exposed as a frontend dropdown:

| Selector | Options |
|---|---|
| **Cost of Capital approach** | Detailed (CAPM build-up) · Direct input · Industry average · Regional decile |
| **β approach** | Single-business US · Single-business Global · Multi-business US (EV-weighted) · Multi-business Global · Direct levered · Direct unlevered |
| **ERP approach** | Country of incorporation · Operating countries (rev-weighted) · Operating regions · Direct |
| **Kd approach** | Industry fallback · Direct · Synthetic rating (coverage→rating→spread) · Actual rating → spread |
| **Failure overlay** | Probability of failure, distress proceeds pct, tie-to (B/V) |
| **Terminal** | Stable-period WACC override, stable ROIC override, perpetuity growth override |
| **Reinvestment lag** | 0, 1, 2, or 3 years |
| **Tax convergence, NOL carryforward, trapped-cash treatment** | editable overrides |

### Currency handling

Every valuation has two currency contexts: **reporting currency** (from
financial statements) and **listing currency** (where the stock trades).
When they differ (e.g. Lenovo: USD reports, HKD listing; Alibaba: CNY
reports, USD ADR), the engine:

- derives the FX rate from the data source by fetching price in both
  currencies;
- performs all WACC / bridge math in reporting currency to keep it
  consistent with debt;
- shows both currencies in the UI with a `DualCurrency` component and
  a top-of-page `CurrencyBanner` displaying the FX rate + date;
- gracefully falls back when FX isn't available and flags the gap to
  the user.

### Graceful fallback — unresolved fields

When the data source can't auto-resolve a field (industry not in
Damodaran's classification, country unknown, exchange-prefix unmapped,
tax rate `#N/A`, FX unavailable), the valuation still runs with a
documented placeholder and surfaces the gap via an
`UnresolvedFieldsPanel` at the top of every page. The analyst picks
from a dropdown (95 industries, 180 countries, 55 ISO currencies) or
types a custom value; the valuation re-runs.

### Geographic revenue segments

Fetch the top 10 geographic revenue segments from your data source;
the auto-resolver maps them to Damodaran's 180 countries and 10 regional
aggregates through a 4-layer cascade (exact country → curated alias →
composite expansion with seeded weights → weak default / unresolved).
Composites like `EMEA`, `APAC`, `Americas`, `Greater China`, `Nordics`,
`DACH`, `ASEAN`, `LATAM`, `MENA` are pre-defined. Users override via
dropdown when the auto-suggestion doesn't fit. The blended ERP feeds
directly into the `operating_countries` ERP methodology.

### Tooltips on every number

Every monetary / percentage / ratio cell on every page has a hover
tooltip showing its provenance: the data-source formula, the Damodaran
file+column it came from, or the inline math that produced it (e.g.
`β_L = β_u × [1 + (1-t) × D/E] = 1.325 × [1 + (1−16.50%) × 0.304] = 1.62`).

### Comprehensive test suite

83 backend tests cover the arithmetic for each M1–M6 module against
hand-calculated expected values plus live integration tests for 4
representative companies (software mega-cap, Chinese e-commerce ADR,
auto manufacturer, HK-listed hardware firm).

---

## Project layout

```
<repo>/
├── backend/
│   ├── api/                       FastAPI routes, session store
│   ├── engine/                    M1–M6 calculation modules + orchestrator
│   │   ├── data_dictionary.py     All Pydantic input/output schemas
│   │   ├── ltm_calculator.py      LTM rotation (Ginzu formula)
│   │   ├── module_1_adjustments.py  R&D + lease capitalization
│   │   ├── module_2_risk.py       Cost of capital (4×6×4×4 dispatch)
│   │   ├── module_3_cashflow.py   FCFF, ROIC, reinvestment
│   │   ├── module_4_dcf.py        10-year projection + terminal
│   │   ├── module_5_multiples.py  P/E, P/B, EV/EBITDA comparisons
│   │   ├── module_6_options.py    Iterative dilution-adjusted BSM
│   │   ├── segment_resolver.py    Geographic-segment → Damodaran mapper
│   │   └── orchestrator.py        Glue code
│   ├── data_sources/              Damodaran store + data-fetch parser
│   ├── tools/                     Template generator, readers
│   └── tests/                     pytest suite
│
├── frontend/
│   └── src/
│       ├── pages/                 Input Sheet, Summary, CoC, DCF, …
│       ├── components/            SpreadsheetGrid, CurrencyBanner,
│       │                          UnresolvedFieldsPanel, GeographicSegmentsPanel
│       ├── lib/                   currency, sources tooltips
│       └── types/                 TypeScript models mirroring Pydantic
│
├── docs/
│   ├── Ginzu understanding/       Financial-reasoning docs per module
│   ├── architecture/              System-level design notes
│   ├── experiments/               Ginzu-vs-backend comparison tooling
│   └── DATA_FETCH_SCHEMA.md       Template field-by-field reference
│
└── knowledge_base/                Reference data (user-supplied, see above)
    ├── damodaran/                 → download from Damodaran's Stern page
    ├── industry_lookup/           → indname.xlsx + supplemental_companies.json
    ├── ciq_fetches/               → your data-fetch templates (gitignored)
    └── segment_aliases.json       Ships with the repo — geographic-segment aliases
```

---

## Methodology documentation

The `docs/Ginzu understanding/` folder contains a plain-English
financial-reasoning document for each calculation module:

- [`README.md`](docs/Ginzu%20understanding/README.md) — index
- [`module_01_ltm.md`](docs/Ginzu%20understanding/module_01_ltm.md) — LTM rotation
- [`module_02_rd_capitalization.md`](docs/Ginzu%20understanding/module_02_rd_capitalization.md) — R&D capitalization
- [`module_03_operating_leases.md`](docs/Ginzu%20understanding/module_03_operating_leases.md) — lease capitalization
- [`module_04_cost_of_capital.md`](docs/Ginzu%20understanding/module_04_cost_of_capital.md) — WACC
- [`module_05_dcf_projection.md`](docs/Ginzu%20understanding/module_05_dcf_projection.md) — DCF projection
- [`module_06_terminal_and_pv.md`](docs/Ginzu%20understanding/module_06_terminal_and_pv.md) — terminal value, PV
- [`module_07_failure_and_bridge.md`](docs/Ginzu%20understanding/module_07_failure_and_bridge.md) — failure overlay, equity bridge
- [`module_08_options.md`](docs/Ginzu%20understanding/module_08_options.md) — options dilution
- [`module_09_per_share.md`](docs/Ginzu%20understanding/module_09_per_share.md) — per-share intrinsic value

Written to serve as a learning resource for analysts who want to
understand *why* each step of a DCF is structured the way it is.

---

## Contributing

Contributions welcome. Open a PR against `main`. Please:

1. Keep changes atomic — one feature or fix per PR.
2. Run `pytest tests/ -q` before pushing; all 83 tests must pass.
3. Run `npx tsc --noEmit` and `npx vite build` in `frontend/` before
   pushing.
4. Follow the existing module boundary: new calculation logic goes in
   `backend/engine/`, not `backend/api/`.
5. Reference the methodology docs when adding features — if you're
   introducing a new methodology variant, add to the appropriate module
   doc.

---

## License

MIT — see [LICENSE](LICENSE).

The software and methodology docs are MIT-licensed. Third-party datasets
(Damodaran's classification files, any data from Capital IQ / Bloomberg /
FactSet) retain their original licenses; users are responsible for
complying with those terms.

---

## Acknowledgments

- **Aswath Damodaran** (NYU Stern) — whose *Ginzu* workbook and open
  datasets are the methodological foundation of this project. His
  published spreadsheets and lecture notes are the reference implementation
  this code reproduces.
- **S&P Capital IQ / Bloomberg / FactSet / Refinitiv** — any of these
  provides the point-in-time financial data the engine consumes. This
  project is data-source-agnostic; the documented schema is what
  matters.
