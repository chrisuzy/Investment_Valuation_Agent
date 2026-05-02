# Changelog

All notable changes to this project are documented here.
Format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
this project follows [semver](https://semver.org/) at `v1.0.0` onward.

## [Unreleased]

Initial public release — see [v0.1.0 (2026-05-02)](#010--2026-05-02).

## [0.1.0] — 2026-05-02

First public release.

### Added

**Calculation engine (backend)**
- Full 9-module DCF pipeline per Damodaran's *Ginzu* workbook (LTM rotation →
  R&D + lease adjustments → cost of capital → cash flow → DCF projection →
  multiples → terminal + PV → failure overlay → equity bridge → options →
  per-share intrinsic value).
- Cost-of-Capital module with 4 approaches × 6 β variants × 4 ERP variants ×
  4 Kd variants = 384 WACC paths, plus bond-pricing MV of debt, preferred
  stock, convertible decomposition.
- Trailing-12-month rotation using Damodaran's exact formula
  (`LTM = FY0 − Prior_YTD + Current_YTD`).
- Iterative Black-Scholes-Merton for dilution-adjusted employee options.
- 10-year DCF with revenue × margin compounding, Sales-to-Capital
  reinvestment (0/1/2/3-year lag), NOL carryforward, terminal ROIC override,
  stable-period WACC override, cumulative discount-factor math for non-flat
  WACC paths.
- Failure-probability overlay applied before equity bridge.
- Industry-specific R&D amortization defaults (pharma/biotech/aerospace:
  10y; online retail / internet: 3y; all others: 5y).

**Data layer**
- `DamodaranStore` — loads 180 country-risk premiums, 95 US industries +
  95 Global industries, regional aggregates, rating-spread tables, synthetic
  rating tables.
- Country alias table (22 variants) handles formal-vs-short names
  ("United States" / "United States of America", "Hong Kong" variants, etc.).
- Industry mapper with 48k+ company classifications from Damodaran's
  `indname.xlsx` plus an extensible `supplemental_companies.json` for firms
  Damodaran's classification misses (Alibaba, PDD, Sea Ltd, etc.).

**Currency handling**
- Automatic FX derivation via dual-currency data fetch (`stock_price` vs
  `stock_price_reporting` from CIQ's `REPORTED` currency scope).
- `mv_equity` standardized to reporting currency so WACC math is
  currency-consistent with debt. Fixes the D/E mis-computation that would
  otherwise affect non-US-listed / non-US-reporting firms (Lenovo, BABA).
- `CurrencyBanner` and `DualCurrency` frontend components show both
  currencies with the FX rate + date.

**Geographic segments**
- Top-10 revenue-segment fetch from data source.
- 4-layer resolver: exact country → alias → composite expansion
  (`EMEA`, `APAC`, `Americas`, `Greater China`, `Nordics`, `DACH`, `ASEAN`,
  etc.) → unresolved (flagged to user).
- `GeographicSegmentsPanel` — frontend dropdown with 180 countries + 10
  regions (ERP shown inline in each option). Live blended-ERP preview.
- Auto-filtering of zero-revenue / corporate / unallocated segment labels.

**Graceful fallback**
- `UnresolvedFieldsPanel` surfaces every missing / unresolved input
  (industry, country, exchange currency, tax rate, FX, shares, etc.).
- No valuation ever blocks; the pipeline always runs with safe placeholders
  and the UI prompts for user override.

**Frontend (React + Vite + TypeScript + Tailwind)**
- 15 pages mirroring Ginzu's worksheet layout.
- Tooltips on every monetary/ratio cell showing provenance.
- Methodology dropdowns wired end-to-end to backend.
- Session-based PATCH-and-recompute flow.

**Documentation**
- Per-module methodology documents in plain financial-reasoning English
  under `docs/Ginzu understanding/`.
- Full data-fetch schema reference in `docs/DATA_FETCH_SCHEMA.md`.
- Architecture notes in `docs/architecture/`.
- Ginzu-vs-backend comparison harness with tooling for reconciliation
  against Damodaran's own published spreadsheets.

**Verification**
- 83 pytest unit + integration tests covering every M1–M6 module.
- NVDA valuation reconciled against Damodaran's Ginzu workbook: WACC
  matches to 4 decimal places; value per share within 5.3% (residual
  attributable to Ginzu's NVDA-specific 3-business-story split).

### Known limitations

- Multi-business β (EV-weighted across segment industries) is schema-
  supported but the front-end segment editor is not yet wired.
- No live cloud deployment templates.
- Screenshot gallery + demo GIFs not yet captured (see `docs/screenshots/`
  drop-in guide).
- pywin32-dependent Excel COM automation is Windows-only; Linux/macOS
  users must populate the data-fetch template manually.

[Unreleased]: https://github.com/chrisuzy/Investment_Valuation_Agent/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/chrisuzy/Investment_Valuation_Agent/releases/tag/v0.1.0
