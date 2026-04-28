import json, os

def extract(path):
    msgs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line.strip())
            t = obj.get("type")
            if t not in ("user", "assistant"):
                continue
            msg = obj.get("message", {})
            role = msg.get("role", "")
            content = msg.get("content", "")
            if isinstance(content, list):
                texts = []
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        texts.append(c["text"])
                content = "\n".join(texts)
            if not isinstance(content, str) or len(content) < 15:
                continue
            if content.strip().startswith("<task-notification"):
                continue
            msgs.append((role.upper(), content))
    return msgs

base = r"C:\Users\zhangyu29\.claude\projects\C--Users-zhangyu29-AD-CC-pilot"
for fname, label in [
    ("048a94aa-36d1-475e-8e28-4b767b5046fa.jsonl", "SESSION 1"),
    ("f4e73393-9bc4-45be-9464-415861dd71d9.jsonl", "SESSION 2"),
]:
    path = os.path.join(base, fname)
    print(f"=== {label} ===")
    for role, text in extract(path):
        clean = text[:500].replace("\n", "\n  ")
        print(f"[{role}]:\n  {clean}")
        print("---")
    print()
