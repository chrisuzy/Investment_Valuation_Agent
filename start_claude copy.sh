#!/bin/bash

# =============================================================================
# Claude Code Launcher for Lenovo Gateway
# =============================================================================
#
# WHAT THIS DOES:
#   Launches Claude Code with a local proxy that fixes two incompatibilities
#   between Claude Code and the Lenovo LLM gateway, enabling Opus 4.7 with
#   1M context and adaptive thinking.
#
# WHY IT'S NEEDED:
#   The Lenovo gateway (llm-prx-sy.hciii.lenovo.com:5167) uses non-standard
#   model IDs. For Opus 4.7:
#     - Gateway name:     claude-4-7-opus
#     - Claude Code name: claude-opus-4-7
#   This mismatch causes two errors:
#
#   Error 1 — "Invalid model name" (model=claude-opus-4-7)
#     When you select "Opus 4.7 (1M context)" from /model picker, Claude Code
#     sends "claude-opus-4-7" which the gateway doesn't recognize.
#
#   Error 2 — "thinking.type.enabled is not supported"
#     When you manually use /model claude-4-7-opus (gateway name), Claude Code
#     doesn't recognize it as Opus 4.7, so it sends the old thinking format
#     {type: "enabled"} instead of the required {type: "adaptive"}.
#
# HOW THE PROXY FIXES IT:
#   A tiny Python HTTP server runs on localhost:5168 between Claude Code and
#   the gateway. It does three things:
#
#   1. MODEL LIST INJECTION (GET /v1/models)
#      Adds "claude-opus-4-7" to the gateway's model list response so Claude
#      Code sees the model it expects and enables 1M context support.
#
#   2. MODEL NAME TRANSLATION (POST /v1/messages)
#      Rewrites "claude-opus-4-7" -> "claude-4-7-opus" in API requests so
#      the gateway accepts the model name.
#
#   3. THINKING TYPE TRANSLATION (POST /v1/messages)
#      Rewrites thinking: {type: "enabled"} -> {type: "adaptive"} and adds
#      output_config: {effort: "high"} so Opus 4.7 accepts the request.
#
# USAGE:
#   cd /path/to/any/project
#   bash /path/to/start_claude.sh
#
#   Then inside Claude Code, run /model and select "Opus 4.7 (1M context)".
#
#   IMPORTANT: Do NOT use --model claude-opus-4-7 on the CLI. That gives 200k
#   context only. You must use the /model picker inside Claude Code to get 1M.
#
# REQUIREMENTS:
#   - Python 3 (for the proxy)
#   - Claude Code (npm install -g @anthropic-ai/claude-code)
#   - Network access to llm-prx-sy.hciii.lenovo.com:5167
#
# PORTABILITY:
#   This is a single self-contained file. The proxy is embedded inline as
#   Python code. Copy this file to any machine and it works — no external
#   scripts or config files needed.
#
# RESOLVED: 2026-04-19
# CLAUDE CODE VERSION: 2.1.114
# FULL DETAILS: See opus47_gateway_fix.md for all failed attempts and pitfalls.
# =============================================================================

# --- Gateway Config ---
export ANTHROPIC_AUTH_TOKEN="sk-1TjgCZbxrpu5dfr8woWNRA"
export ENABLE_TOOL_SEARCH=1

# Disable SSL verification — the Lenovo gateway uses a corporate certificate
# that Node.js doesn't trust by default.
export NODE_TLS_REJECT_UNAUTHORIZED=0

# --- Start proxy if not already running on port 5168 ---
# Check if anything is already listening on port 5168. If so, assume the proxy
# is already running from a previous launch and skip starting a new one.
if ! netstat -ano 2>/dev/null | grep -q "127.0.0.1:5168.*LISTEN"; then
    python -c '
import json, ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# The real Lenovo gateway that this proxy forwards requests to.
UPSTREAM = "https://llm-prx-sy.hciii.lenovo.com:5167"

# Model name mapping: Claude Code standard name -> Lenovo gateway name.
# Add more entries here if other models have the same naming mismatch.
MODEL_MAP = {"claude-opus-4-7": "claude-4-7-opus"}

# Disable SSL verification for the upstream connection (same reason as
# NODE_TLS_REJECT_UNAUTHORIZED=0 above — corporate certificate).
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            body = json.loads(raw)
        except Exception:
            body = None
        if body:
            # --- Fix 1: Translate model name ---
            m = body.get("model", "")
            if m in MODEL_MAP:
                body["model"] = MODEL_MAP[m]

            # --- Fix 2: Translate thinking type for Opus 4.7 ---
            # Claude Code sends {type: "enabled"} but Opus 4.7 requires
            # {type: "adaptive"} with output_config.effort.
            if body.get("model", "").startswith("claude-4-7"):
                th = body.get("thinking")
                if isinstance(th, dict) and th.get("type") == "enabled":
                    body["thinking"] = {"type": "adaptive"}
                    body.setdefault("output_config", {})["effort"] = "high"

            raw = json.dumps(body).encode()

        # Forward to upstream gateway
        hdrs = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "transfer-encoding")}
        hdrs["Content-Length"] = str(len(raw))
        req = Request(f"{UPSTREAM}{self.path}", data=raw, headers=hdrs, method="POST")
        try:
            resp = urlopen(req, context=ctx)
            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() not in ("transfer-encoding",):
                    self.send_header(k, v)
            self.end_headers()
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except HTTPError as e:
            self.send_response(e.code)
            for k, v in e.headers.items():
                if k.lower() not in ("transfer-encoding",):
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(e.read())

    def do_GET(self):
        hdrs = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "transfer-encoding")}
        req = Request(f"{UPSTREAM}{self.path}", headers=hdrs, method="GET")
        try:
            resp = urlopen(req, context=ctx)
            raw = resp.read()

            # --- Fix 3: Inject claude-opus-4-7 into models list ---
            # Claude Code queries /v1/models at startup. If it does not see
            # "claude-opus-4-7" in the list, it cannot enable 1M context.
            # We inject it as an alias for the real "claude-4-7-opus" model.
            if "/v1/models" in self.path:
                try:
                    body = json.loads(raw)
                    ids = {m["id"] for m in body.get("data", [])}
                    for alias, real in MODEL_MAP.items():
                        if real in ids and alias not in ids:
                            body["data"].append({"id": alias, "object": "model", "created": 1677610602, "owned_by": "anthropic"})
                    raw = json.dumps(body).encode()
                except Exception:
                    pass

            self.send_response(resp.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())

    # Suppress request logging to keep the terminal clean.
    def log_message(self, *a):
        pass

HTTPServer(("127.0.0.1", 5168), H).serve_forever()
' &
    sleep 1
fi

# --- Point Claude Code at the local proxy instead of the gateway directly ---
export ANTHROPIC_BASE_URL="http://127.0.0.1:5168"

# --- Launch Claude Code in whatever directory the user is currently in ---
claude --dangerously-skip-permissions claude --resume 6798d6d3-7e06-4cda-986d-185abb25d321

# claude --resume 6798d6d3-7e06-4cda-986d-185abb25d321