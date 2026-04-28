"""Extract Claude Code session JSONL files into readable markdown."""

import json
import os
import textwrap

BASE = r"C:\Users\zhangyu29\.claude\projects\C--Users-zhangyu29-AD-CC-pilot"
OUT_DIR = r"C:\Users\zhangyu29\AD_CC_pilot\chat_history"

SESSIONS = [
    ("048a94aa-36d1-475e-8e28-4b767b5046fa.jsonl", "session_1_brainstorm_and_backend.md", "Session 1 — Brainstorm, PRD & Backend Engine"),
    ("f4e73393-9bc4-45be-9464-415861dd71d9.jsonl", "session_2_frontend_and_api.md", "Session 2 — Frontend, API & Integration"),
]


def extract_messages(path):
    """Parse JSONL and yield (role, content, tool_info) tuples."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get("type")
            if msg_type not in ("user", "assistant"):
                continue

            msg = obj.get("message", {})
            role = msg.get("role", msg_type)
            content = msg.get("content", "")

            # Handle content that is a list of blocks
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            parts.append(block["text"])
                        elif block.get("type") == "tool_use":
                            tool_name = block.get("name", "unknown")
                            tool_input = block.get("input", {})
                            # Summarize tool calls
                            if tool_name == "Write":
                                fp = tool_input.get("file_path", "")
                                parts.append(f"[Tool: Write file `{fp}`]")
                            elif tool_name == "Edit":
                                fp = tool_input.get("file_path", "")
                                parts.append(f"[Tool: Edit file `{fp}`]")
                            elif tool_name == "Read":
                                fp = tool_input.get("file_path", "")
                                parts.append(f"[Tool: Read file `{fp}`]")
                            elif tool_name == "Bash":
                                cmd = tool_input.get("command", "")[:120]
                                parts.append(f"[Tool: Bash `{cmd}`]")
                            elif tool_name == "Glob":
                                pat = tool_input.get("pattern", "")
                                parts.append(f"[Tool: Glob `{pat}`]")
                            elif tool_name == "Grep":
                                pat = tool_input.get("pattern", "")
                                parts.append(f"[Tool: Grep `{pat}`]")
                            elif tool_name == "Agent":
                                desc = tool_input.get("description", "")
                                parts.append(f"[Tool: Agent — {desc}]")
                            else:
                                parts.append(f"[Tool: {tool_name}]")
                        elif block.get("type") == "tool_result":
                            # Skip tool results to keep it concise
                            pass
                    elif isinstance(block, str):
                        parts.append(block)
                content = "\n".join(parts)

            if not isinstance(content, str):
                continue

            # Skip very short or system-only messages
            clean = content.strip()
            if len(clean) < 10:
                continue
            if clean.startswith("<task-notification"):
                continue
            if clean.startswith("<system-reminder"):
                continue
            # Skip pure tool result messages (they start with system tags)
            if clean.startswith("<") and "system" in clean[:50].lower():
                continue

            yield (role.upper(), clean)


def write_markdown(messages, out_path, title):
    """Write messages to a markdown file."""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"*Extracted from Claude Code session logs*\n\n---\n\n")

        msg_num = 0
        for role, content in messages:
            msg_num += 1

            if role == "USER":
                f.write(f"## User (#{msg_num})\n\n")
            else:
                f.write(f"## Assistant (#{msg_num})\n\n")

            # Truncate extremely long messages (tool dumps, etc.)
            if len(content) > 5000:
                # Keep first 2000 and last 500 chars
                content = content[:2000] + "\n\n... [truncated] ...\n\n" + content[-500:]

            f.write(content)
            f.write("\n\n---\n\n")

        f.write(f"\n*End of {title} — {msg_num} messages total*\n")

    return msg_num


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for jsonl_file, md_file, title in SESSIONS:
        jsonl_path = os.path.join(BASE, jsonl_file)
        md_path = os.path.join(OUT_DIR, md_file)

        if not os.path.exists(jsonl_path):
            print(f"SKIP: {jsonl_file} not found")
            continue

        messages = list(extract_messages(jsonl_path))
        count = write_markdown(messages, md_path, title)
        size_kb = os.path.getsize(md_path) / 1024
        print(f"OK: {md_file} — {count} messages, {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
