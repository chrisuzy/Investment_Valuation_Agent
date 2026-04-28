# Lenovo Gateway Model Configuration

## Gateway
- URL: `https://llm-prx-sy.hciii.lenovo.com:5167`
- Auth: `ANTHROPIC_AUTH_TOKEN` (not API_KEY)
- Model list endpoint: `/models` (OpenAI-compatible format)

## Available Claude Models on Gateway
| Model ID | Notes |
|---|---|
| `claude-4-7-opus` | Latest, supports adaptive thinking |
| `claude-4-6-opus` | Also listed as `claude-opus-4-6` |
| `claude-4-6-sonnet` | Also listed as `claude-sonnet-4-6` |
| `claude-4-5-opus` | |
| `claude-4-5-sonnet` | |
| `claude-4-5-haiku` | |
| `claude-4-sonnet` | |
| `claude-3-7-sonnet` | |
| `claude-3-5-sonnet` / `claude-3-5-sonnet-2` | |

## Thinking Mode for 4.7
- Does NOT support `"thinking": {"type": "enabled"}` — returns error
- MUST use `"thinking": {"type": "adaptive"}` with `"output_config": {"effort": "high|max"}`
- `effort: "high"` — works, thinking block returned
- `effort: "max"` — works, thinking block returned with signature
- `budget_tokens` NOT allowed with adaptive type

## Claude Code CLI Flags (Verified)
- `--model claude-4-7-opus` — sets model
- `--effort high` — sets thinking effort (low, medium, high, xhigh, max)

## 1M Context Window
- `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS="1"` in current start script — likely blocks extended context
- The `anthropic-beta: extended-context-2025-04-14` header was accepted by gateway without error
- Remove the DISABLE_BETAS env var to enable

## Recommended start_claude.sh
```bash
#!/bin/bash
export ANTHROPIC_BASE_URL="https://llm-prx-sy.hciii.lenovo.com:5167"
export ANTHROPIC_AUTH_TOKEN="sk-1TjgCZbxrpu5dfr8woWNRA"
export NODE_TLS_REJECT_UNAUTHORIZED=0
export ENABLE_TOOL_SEARCH=1
# REMOVED: CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS (blocks extended context/1M)
claude --model claude-4-7-opus --effort high --dangerously-skip-permissions
```
