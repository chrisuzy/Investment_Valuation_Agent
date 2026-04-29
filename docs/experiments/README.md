# Ginzu vs Backend — Comparison Experiment

See `docs/superpowers/specs/2026-04-29-ginzu-vs-backend-comparison-design.md` for the full design.

**Workflow:**

1. **Phase 1 (done):** Claude prepared `ginzu_inputs_<TICKER>.md` for each test company.
2. **Phase 2 (user, Windows):** Open `knowledge_base/Ginzu_NVIDIA.xlsx` on a Windows machine with Excel. For each ticker, Save-As `<TICKER>_ginzu.xlsx`, paste inputs per the package's Section A/B/C, let Excel recalc, fill in Section D with Ginzu's output values.
3. **Phase 3 (Claude, after user returns):** Claude runs `backend/tools/run_ginzu_comparison.py <TICKER>` which reads the filled-in Section D and produces `ginzu_comparison_<TICKER>.md`.

**Packages:**

- [`ginzu_inputs_MSFT.md`](./ginzu_inputs_MSFT.md)
- [`ginzu_inputs_BABA.md`](./ginzu_inputs_BABA.md)
- [`ginzu_inputs_TSLA.md`](./ginzu_inputs_TSLA.md)
- [`ginzu_inputs_LENOVO.md`](./ginzu_inputs_LENOVO.md)
