"""
Local proxy: rewrites model names and thinking params for the Lenovo gateway.

  Claude Code -> localhost:5168 -> llm-prx-sy.hciii.lenovo.com:5167

Fixes two problems:
  1. Model name:  claude-opus-4-7 (CC standard) -> claude-4-7-opus (gateway)
  2. Thinking:    {type:"enabled"} -> {type:"adaptive"} + effort:high
"""

import json, ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError

UPSTREAM = "https://llm-prx-sy.hciii.lenovo.com:5167"

MODEL_MAP = {
    "claude-opus-4-7": "claude-4-7-opus",
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


class ProxyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = None

        if body:
            model = body.get("model", "")
            if model in MODEL_MAP:
                body["model"] = MODEL_MAP[model]
            if body.get("model", "").startswith("claude-4-7"):
                th = body.get("thinking")
                if isinstance(th, dict) and th.get("type") == "enabled":
                    body["thinking"] = {"type": "adaptive"}
                    body.setdefault("output_config", {})["effort"] = "high"
                    th.pop("budget_tokens", None)
            raw = json.dumps(body).encode()

        headers = {
            k: v for k, v in self.headers.items()
            if k.lower() not in ("host", "transfer-encoding")
        }
        headers["Content-Length"] = str(len(raw))

        req = Request(
            f"{UPSTREAM}{self.path}",
            data=raw,
            headers=headers,
            method="POST",
        )

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
        headers = {
            k: v for k, v in self.headers.items()
            if k.lower() not in ("host", "transfer-encoding")
        }
        req = Request(f"{UPSTREAM}{self.path}", headers=headers, method="GET")
        try:
            resp = urlopen(req, context=ctx)
            raw = resp.read()

            if "/v1/models" in self.path:
                try:
                    body = json.loads(raw)
                    ids = {m["id"] for m in body.get("data", [])}
                    for alias, real in MODEL_MAP.items():
                        if real in ids and alias not in ids:
                            body["data"].append({
                                "id": alias,
                                "object": "model",
                                "created": 1677610602,
                                "owned_by": "anthropic",
                            })
                    raw = json.dumps(body).encode()
                except (json.JSONDecodeError, KeyError):
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

    def log_message(self, fmt, *args):
        pass  # silent


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 5168), ProxyHandler)
    print("Thinking proxy listening on http://127.0.0.1:5168")
    server.serve_forever()
