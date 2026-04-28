# Opus 4.7 (1M Context) on Lenovo Gateway — Solution & Pitfalls

## The Problem

Claude Code cannot use Opus 4.7 (1M context) directly through the Lenovo gateway (`llm-prx-sy.hciii.lenovo.com:5167`). Two independent errors block it depending on which model name you use.

## Gateway Model List

The gateway uses **non-standard model IDs**. For Opus 4.7:

| Gateway has | Claude Code expects |
|---|---|
| `claude-4-7-opus` | `claude-opus-4-7` |

These are NOT interchangeable. Each triggers a different error.

## The Two Errors

### Error 1: Invalid Model Name

**When:** You select "Opus 4.7 (1M context)" from the `/model` picker.

**What happens:** Claude Code sends `model: "claude-opus-4-7"` to the gateway. The gateway doesn't have this model ID.

```
API Error: 400 {"error":{"message":"Invalid model name passed in model=claude-opus-4-7.
Call `/v1/models` to view available models for your key."}}
```

### Error 2: Thinking Type Rejected

**When:** You manually run `/model claude-4-7-opus` (the gateway's name).

**What happens:** The gateway accepts the model name, but Claude Code sends `thinking: {type: "enabled"}`. Opus 4.7 requires `thinking: {type: "adaptive"}`.

```
API Error: 400 "thinking.type.enabled" is not supported for this model.
Use "thinking.type.adaptive" and "output_config.effort" to control thinking behavior.
Received Model Group=claude-4-7-opus
```

### Additional Problem: 200k Context

Even if you bypass the above errors, using `claude-4-7-opus` (the gateway name) or `--model claude-opus-4-7` on the CLI only gives **200k context**. The 1M context is only available when selecting "Opus 4.7 (1M context)" from the `/model` **picker**, which sets internal Claude Code configuration beyond just the model ID.

## Root Cause

The Lenovo gateway uses reversed model naming (`claude-4-7-opus` instead of `claude-opus-4-7`). Claude Code:
1. Doesn't find `claude-opus-4-7` in the gateway's `/v1/models` response
2. Doesn't recognize `claude-4-7-opus` as Opus 4.7, so it sends the old `thinking: {type: "enabled"}` format instead of `{type: "adaptive"}`

## The Solution: Local Proxy

A Python proxy (`thinking_proxy.py`) sits between Claude Code and the gateway:

```
Claude Code (localhost:5168) --> Proxy --> Gateway (llm-prx-sy.hciii.lenovo.com:5167)
```

The proxy does three things:
1. **Injects `claude-opus-4-7` into `/v1/models` response** — so Claude Code sees the model it expects and enables 1M context
2. **Translates model name** in API calls: `claude-opus-4-7` -> `claude-4-7-opus`
3. **Translates thinking type**: `{type: "enabled"}` -> `{type: "adaptive"}` + adds `output_config.effort: "high"`

### How to Launch

```bash
cd ~/AD_CC_pilot
python thinking_proxy.py &

ANTHROPIC_BASE_URL=http://127.0.0.1:5168 \
ANTHROPIC_AUTH_TOKEN=sk-1TjgCZbxrpu5dfr8woWNRA \
NODE_TLS_REJECT_UNAUTHORIZED=0 \
ENABLE_TOOL_SEARCH=1 \
claude --dangerously-skip-permissions
```

Then inside Claude Code, use `/model` picker and select **"Opus 4.7 (1M context)"**.

**Important:** Do NOT use `--model claude-opus-4-7` on the CLI — that gives 200k. You must use the `/model` picker inside Claude Code to get 1M.

## Failed Attempts & Why They Failed

### Attempt 1: `--effort high` flag
**Tried:** Adding `--effort high` to `start_claude.sh`.
**Why it failed:** `--effort` sets `output_config.effort` but does NOT change `thinking.type` from `"enabled"` to `"adaptive"`. They are independent API parameters.

### Attempt 2: Changing model name in settings.json
**Tried:** Setting `"model": "claude-4-7-opus"` in `~/.claude/settings.json`.
**Why it failed:** Claude Code doesn't recognize `claude-4-7-opus` as Opus 4.7. It treats it as a generic model with 200k context and sends the wrong thinking format.

### Attempt 3: Using `--model claude-opus-4-7` on CLI
**Tried:** Launching with the standard Anthropic model ID.
**Why it failed:** Gives 200k context, not 1M. The 1M context variant requires selection through the `/model` picker which sets additional internal configuration.

### Attempt 4: Proxy without model injection in `/v1/models`
**Tried:** Proxy that only translated model names and thinking params in POST requests.
**Why it failed:** Claude Code queries `/v1/models` at startup. Without seeing `claude-opus-4-7` in that list, it couldn't properly recognize the model for 1M context. Had to inject the model into the GET `/v1/models` response.

### Attempt 5: Stale proxy process
**Tried:** Updated proxy code and re-ran tests.
**Why it failed:** The old proxy process (without MODEL_MAP) was still running on port 5168. New proxy couldn't bind or requests went to the old one. Fix: always `taskkill //F //IM python.exe` before starting the proxy.

## Key Files

| File | Purpose |
|---|---|
| `thinking_proxy.py` | The local proxy — must be running before Claude Code |
| `start_claude.sh` | Original launch script (does NOT use proxy yet) |
| `~/.claude/settings.json` | Claude Code settings (model field is for default model) |

## Environment

- Claude Code version: 2.1.114
- Gateway: `https://llm-prx-sy.hciii.lenovo.com:5167`
- Platform: Windows 11 Pro, Git Bash
- Date resolved: 2026-04-19
