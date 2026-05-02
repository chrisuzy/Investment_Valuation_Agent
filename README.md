<div align="center">

# 📊 Investment Valuation Agent

### Aswath Damodaran's *Ginzu* DCF model — finally open-source, auditable, and global.

**Every number traces to its source. Every methodology choice is a dropdown. Every valuation works for any public company on any exchange in any currency.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)
[![React 18](https://img.shields.io/badge/react-18-61DAFB.svg?logo=react&logoColor=white)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/typescript-%5E5.0-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/tests-83%20passing-brightgreen.svg)]()
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-ff69b4.svg)](CONTRIBUTING.md)

<br/>

[**Quickstart →**](#-quickstart) · [**Methodology docs →**](docs/Ginzu%20understanding/README.md) · [**Why this exists →**](#-why-this-exists) · [**Contributing →**](CONTRIBUTING.md)

<br/>

> ⭐ **If you've ever stared at a `#REF!` in a DCF model and wondered what it *actually* represents — star this repo. This project is for you.**

</div>

---

## 🤯 The problem

Every finance student learns Aswath Damodaran's DCF framework. Every investment analyst ends up in a 40-tab Excel workbook that nobody understands, not even its author 6 months later. The math is correct but the provenance is lost — **where did that β come from? Is the WACC in USD or HKD? What happens if we change the ERP approach? Why does Lenovo's D/E look wrong?**

Spreadsheets answer none of these questions. Their authors often can't either.

## 💡 What this does

**Reimplements Damodaran's *Ginzu* valuation workbook as a modern web application** where:

| Spreadsheet says | This app says |
|---|---|
| `1.62` | `β_L = β_u × [1 + (1−t) × D/E] = 1.325 × [1 + 0.835 × 0.304] = 1.62` *(hover tooltip)* |
| `5.52%` | `ERP = 0.45×4.33% (US) + 0.22×5.41% (China) + 0.18×6.51% (EMEA composite) + …` |
| `$2.37` | `VPS = $2.37 USD (≈ HK$18.49 at 7.78 HKD/USD, CIQ, 2025-06-30)` |
| `#REF!` | `⚠ Segment "Rest of World" needs your input — pick from 180 countries or 10 regions` |

Every number is traceable. Every methodology is a live dropdown. Switch the ERP approach from "country of incorporation" to "operating countries" — watch β, Ke, WACC, and VPS recompute in real time. Upload a financial data workbook, get a defensible DCF in seconds.

## ⚡ What makes this different

### 🔍 Full provenance on every cell
Hover any monetary or ratio cell in the app. Get the CIQ mnemonic, the Damodaran file + column, or the exact computational formula. No more "trust me, it's right."

### 🧭 Every Ginzu methodology choice, exposed
Damodaran's model has **4 approaches × 6 β variants × 4 ERP variants × 4 Kd variants** = 384 possible WACC paths. This app implements them all. Switch between them with a dropdown; the entire downstream valuation re-runs.

### 🌏 Works for any company, anywhere
- **180 countries** with their ERPs, CRPs, and tax rates loaded from Damodaran's live datasets
- **95 industries** — US and Global — with β_u, β_L, WACC, D/E, ROIC, and margin benchmarks
- **10 Damodaran regional aggregates** (North America, Western Europe, Asia, Africa, …) for operating-countries ERP blending
- **Automatic currency conversion** when the reporting currency differs from the listing currency (e.g., Lenovo reports USD but trades HKD — this matters for WACC)
- **Geographic revenue segments** auto-mapped: type "EMEA" in a segment, the resolver expands it to a weighted blend of Western Europe + Eastern Europe + Middle East + Africa

### 🛟 Graceful fallback — never a wall
Data missing? Industry not in Damodaran's classification? Exchange prefix unknown? FX rate unavailable? **The valuation still runs with safe defaults and surfaces every unresolved gap** through a single `UnresolvedFieldsPanel` at the top of every page. Pick from the dropdown, the valuation re-runs. No dead-ends.

### 📖 Methodology, documented in English
Every calculation module has a companion financial-reasoning doc in `docs/Ginzu understanding/` explaining *why* each step is structured the way it is. Not just code — a learning resource for anyone studying DCF seriously.

### ✅ 83 tests passing
Every M1–M6 arithmetic module tested against hand-calculated expected values, plus end-to-end integration tests for 4 representative companies (US tech mega-cap, China e-commerce ADR, US EV manufacturer, HK-listed hardware firm).

---

## 🎬 See it in action

Upload a populated data-fetch workbook for Lenovo (SEHK:992). Watch:

```
1. LTM rotation:      FY-0 + current YTD − prior YTD  →  latest 12-month base year
2. R&D capitalization: 10 years of historical R&D → research asset + amortization
3. Operating leases:   PV of commitments → debt + depreciation on lease asset
4. Cost of Capital:
     β_u (Computers/Peripherals, US Damodaran):       1.325
     β_L (relevered at D/E = 26.8%, tax = 16.5%):     1.621
     ERP (operating countries — China/AP/EMEA/Amer):  6.02%
     Ke (CAPM):                                       13.62%
     Kd (industry fallback, after-tax):               5.16%
     Weights (E/D):                                   78.9%/21.1%
     WACC:                                            11.99%
5. DCF projection:     10 years × (revenue path, margin path, reinvestment, FCFF)
6. Terminal + PV:      Gordon growth, failure overlay, cumulative discount factors
7. Equity bridge:      V_operating − debt − minority + cash + cross_holdings
8. Options dilution:   iterative Black-Scholes
9. Value per share:    $2.40 USD (≈ HK$18.67 at spot FX)
   Market price:       HK$11.83  (≈ $1.52 USD)
   Price/Value:        0.64x — undervalued on DCF
```

**Switch a single dropdown** (`ERP approach: country_of_incorporation → operating_countries`) and see β_L shift, WACC shift, VPS shift, all live. That's the point.

---

## 🚀 Quickstart

### Prerequisites

- **Python 3.12+**
- **Node.js 18+**
- **Damodaran's annual reference data** — free, downloadable from [his Stern page](https://pages.stern.nyu.edu/~adamodar/)
- **A data-fetch template** — you build it once following [`docs/DATA_FETCH_SCHEMA.md`](docs/DATA_FETCH_SCHEMA.md). Capital IQ plug-in, Bloomberg, FactSet, or manual input — anything that produces the documented schema.

### Three commands

```bash
# 1. Clone
git clone https://github.com/chrisuzy/Investment_Valuation_Agent.git
cd Investment_Valuation_Agent

# 2. Install
(cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt)
(cd frontend && npm install)

# 3. Run
(cd backend && source .venv/bin/activate && uvicorn api.main:app --port 8000) &
(cd frontend && npm run dev)
```

Open `http://localhost:5173/`. Upload a populated data workbook. Get a DCF.

---

## 🗺 The 9-module pipeline

<div align="center">

```
    ┌─────────────┐
    │ Data fetch  │  (your template, your data source)
    │ .xlsx       │
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │   M0 LTM    │  Trailing-12-month rotation
    └──────┬──────┘
           ▼
    ┌─────────────┐    ┌──────────────┐
    │ M1 Adjust   │───▶│ R&D as asset │
    │             │    │ Leases as debt│
    └──────┬──────┘    └──────────────┘
           ▼
    ┌─────────────┐    ┌──────────────┐
    │ M2 Cost of  │───▶│ 4 approaches │
    │  Capital    │    │ 6 β variants │
    │             │    │ 4 ERP variants│
    │             │    │ 4 Kd variants │
    └──────┬──────┘    └──────────────┘
           ▼
    ┌─────────────┐
    │ M3 FCFF     │  EBIT(1-t), reinvestment with lag, ROIC
    └──────┬──────┘
           ▼
    ┌─────────────┐    ┌──────────────┐
    │ M4 DCF      │───▶│ 10-yr path:  │
    │             │    │ rev × margin │
    │             │    │ S/C reinvest │
    │             │    │ WACC convrg  │
    └──────┬──────┘    │ NOL carry    │
           ▼           └──────────────┘
    ┌─────────────┐
    │ M5 Multiples│  P/E, P/B, EV/EBITDA intrinsic vs market
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │ M6 Terminal │  Gordon growth + cumulative PV + failure overlay
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │ M7 Bridge   │  V_op − debt − minority + cash + cross_holdings
    └──────┬──────┘
           ▼
    ┌─────────────┐    ┌──────────────┐
    │ M8 Options  │───▶│ Iterative    │
    │             │    │ dilution BSM │
    └──────┬──────┘    └──────────────┘
           ▼
    ┌─────────────┐
    │ M9 Per-Share│  Final VPS + market-price comparison
    └─────────────┘
```

</div>

Each module has a dedicated [methodology doc](docs/Ginzu%20understanding/README.md) and its own backend module + set of tests.

---

## 🎨 Screenshots

> 📸 *Screenshots and demo GIF coming soon.* For now, a tour of what you'll see:

- **Input Sheet** — every raw input with a tooltip showing its CIQ mnemonic or data-source origin
- **Cost of Capital** — methodology selectors in one panel; full WACC decomposition in another; industry-reference sidebar with Damodaran industry averages inline
- **Geographic Revenue Mix** — segment-by-segment revenue table with auto-mapped Damodaran ERPs; dropdown per row to override; live blended-ERP preview
- **Summary Sheet** — 10-year projection with year-by-year revenue, margin, FCFF, discount factor, PV
- **Valuation Output** — full equity bridge from V_operating to VPS with every addition/subtraction labeled

---

## 🧠 Why this exists

Damodaran's work is a public good — he literally publishes his spreadsheets, his lecture notes, and his valuation datasets for free on the NYU Stern website. He's been doing this for decades.

But the spreadsheets are opaque. A DCF hidden in Excel is a black box to everyone except its author. And for a global model — one that actually handles the fact that Lenovo reports in USD but trades in HKD, or that Alibaba reports in CNY but lists its ADR in USD — Excel is the wrong tool.

This project brings the *Ginzu* framework into a stack where:
- The math is testable (83 unit tests, and counting)
- The assumptions are interactive (methodology dropdowns that actually change outputs)
- The provenance is always one hover away (every cell explains itself)
- The data is substitutable (CIQ, Bloomberg, FactSet, your internal systems — if it produces the schema, it works)

Built as a tribute to an educator who gave away his life's work. Open-sourced to pay that forward.

---

## 📚 Deeper reading

- [**Damodaran on Valuation**](https://pages.stern.nyu.edu/~adamodar/) — the man, the myth, the spreadsheets
- [**Methodology docs**](docs/Ginzu%20understanding/README.md) — in-repo explanations of each calculation module
- [**Architecture docs**](docs/architecture/) — system-level design notes
- [**Data-fetch schema**](docs/DATA_FETCH_SCHEMA.md) — exact Excel workbook structure the backend expects
- [**Ginzu-vs-backend comparison tool**](docs/experiments/README.md) — verification harness that reconciles this engine's output against Damodaran's original Excel

---

## 🛣 Roadmap

- [ ] One-click cloud deployment (Fly.io / Railway / Render templates)
- [ ] Synthetic rating derivation from interest coverage, fully wired into Kd
- [ ] Scenario manager — "save this assumption set as 'Bull'"; compare against 'Base' / 'Bear'
- [ ] Monte Carlo on assumption distributions
- [ ] Historical-backtest mode — "what did my DCF say 3 years ago, and was I right?"
- [ ] More data-source adapters (Alpha Vantage, Yahoo Finance shim for casual use)
- [ ] Multi-business beta (EV-weighted β across segment industries)
- [ ] Sector-specific templates (banks, REITs, insurance have different bridge logic)

Want to help with any of these? [**Open an issue**](https://github.com/chrisuzy/Investment_Valuation_Agent/issues/new) or [**send a PR**](CONTRIBUTING.md). All contributions welcome.

---

## 🤝 Contributing

See [**CONTRIBUTING.md**](CONTRIBUTING.md). TL;DR: run the tests, keep PRs atomic, update the methodology docs when you change calculations.

Good first issues:
- Expand the `segment_aliases.json` with more broad-region composites
- Add currency-symbol rendering for more ISO codes (TRY, ILS, PHP, etc.)
- Translate any of the methodology docs to other languages

---

## 📜 License

**MIT** — see [LICENSE](LICENSE).

Use it, fork it, sell it. Just keep the copyright notice. Third-party datasets retain their own licenses; you're responsible for complying with those.

---

## 🙏 Acknowledgments

- **Aswath Damodaran** — whose *Ginzu* workbook, public datasets, and decades of teaching make this project possible. The methodology is his; the implementation is ours.
- **The FastAPI, Pydantic, React, and Vite teams** — for making the modern Python + TypeScript stack a joy to build on.
- **Every analyst who ever cursed an Excel DCF model** — this is for you.

---

<div align="center">

**If this saves you ten minutes on your next DCF — or teaches you something about why WACC is the way it is — please ⭐ the repo.**

*Built with spite against opaque spreadsheets, and love for the craft of valuation.*

</div>
