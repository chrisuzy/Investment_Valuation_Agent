#!/bin/bash

# --- 基础配置 ---
export ANTHROPIC_BASE_URL="http://10.110.133.66:5166"
export ANTHROPIC_AUTH_TOKEN="sk-1TjgCZbxrpu5dfr8woWNRA"
export ANTHROPIC_DEFAULT_SONNET_MODEL=claude-4-6-sonnet
export ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-4-5-haiku
export ANTHROPIC_DEFAULT_OPUS_MODEL="claude-4-7-opus[1m]"
export NODE_TLS_REJECT_UNAUTHORIZED=0
export ANTHROPIC_BETAS=context-1m-2025-08-07
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1
export ENABLE_TOOL_SEARCH=0

# --- Launch Claude Code in whatever directory the user is currently in ---
claude --dangerously-skip-permissions --resume 9ed8799d-8d98-42f5-a137-cb948326c585

# --resume 9ed8799d-8d98-42f5-a137-cb948326c585