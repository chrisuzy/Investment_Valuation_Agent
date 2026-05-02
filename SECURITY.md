# Security

## Supported versions

Only the latest `main` branch is actively maintained at this stage.

## Reporting a vulnerability

If you discover a security issue in this project — credentials leaking in
logs, a way to exfiltrate user data via a crafted upload, anything that
affects the confidentiality / integrity / availability of a user's valuation
data — please **do not open a public GitHub issue**.

Instead, open a private report via
[GitHub Security Advisories](https://github.com/chrisuzy/Investment_Valuation_Agent/security/advisories/new).

Include:

- A description of the issue and its potential impact
- Minimal reproduction steps
- The commit or version you tested against
- Any proof-of-concept code (if applicable)

You'll get an acknowledgment within 7 days. For confirmed issues, we'll
coordinate a fix and disclosure timeline with you before anything public.

## Scope

Things that are **in scope**:

- Backend API endpoints (FastAPI `routes.py`)
- Excel file parsing (`read_ciq_template.py`, `capiq_adapter.py`) — uploaded
  xlsx files come from user input; injection / XXE / zip-slip issues are
  meaningful
- Frontend XSS (any user-controlled field rendered without escaping)
- Session-store handling (`api/session_store.py`)
- Any dependency with a known CVE

Things that are **out of scope**:

- Incorrect financial outputs due to disagreement with Damodaran's stated
  methodology — file a regular bug report instead
- Performance issues
- Browser compatibility issues

## Dependency security

CI does not currently run automated vulnerability scans. Contributions to
add `pip-audit` and `npm audit` steps to `.github/workflows/` are welcome.
