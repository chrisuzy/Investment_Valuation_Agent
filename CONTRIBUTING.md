# Contributing

Contributions are welcome — bug reports, pull requests, and methodology
discussions all appreciated.

## Development setup

See the [README](README.md) Quickstart. You'll need Python 3.12+, Node 18+,
and a local copy of Damodaran's reference data.

## Pull requests

1. Fork the repo and create a feature branch off `main`.
2. Make atomic changes — one feature or fix per PR.
3. Run the test suite and make sure everything still passes:
   ```bash
   cd backend && source .venv/bin/activate && pytest tests/ -q
   ```
4. Run the frontend typecheck + build:
   ```bash
   cd frontend && npx tsc --noEmit && npx vite build
   ```
5. Push to your fork and open a PR against `main`. Describe what changed
   and why; reference an issue if one exists.

## Methodology changes

When modifying calculation logic (the backend `engine/` modules), please
also update the corresponding methodology doc under
`docs/Ginzu understanding/`. The goal is that methodology docs and code
stay in sync.

## Issues

Found a bug? Open an issue with:
- the ticker / dataset involved
- the observed output vs. expected output
- any error messages from the backend logs (`/tmp/backend.log` by default)
- what data source you used

Questions about Aswath Damodaran's methodology specifically are better
directed at his [Stern page](https://pages.stern.nyu.edu/~adamodar/) or
his Musings on Markets blog. This repo focuses on the *software
implementation* of his framework.
