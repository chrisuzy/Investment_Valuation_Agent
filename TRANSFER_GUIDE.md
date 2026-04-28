# Transferring AD_CC_pilot to the Linux Server via SSH

**Target:** `chriszhang@10.110.133.66:/home/chriszhang/claude_code_projects/`
**Source:** `C:\Users\zhangyu29\AD_CC_pilot` (Windows)
**Goal:** Avoid VS Code drag-and-drop. Use only terminal commands.

---

## Preview: Which approach to pick

You have three options. Read them all, then pick:

| Option | When to use | Effort |
|---|---|---|
| **A. Single tarball via SCP** | Total size under ~500 MB, stable network | Simple |
| **B. Rsync (resumable)** | Large size or flaky connection | Best overall — recommended |
| **C. Split into parts** | Corporate firewall or transfer-size limit actually exists | More steps |

**My recommendation: Option B (rsync).** Resumable, efficient, single command. Works from Git Bash on Windows.

On the question of splitting: **SSH itself has no size limit.** The 200 MB limit is imposed only by some web upload tools (like claude.ai file uploads, corporate DLP tools, or certain network appliances). A direct SSH/SCP/rsync transfer to your own server has no artificial size cap. Unless your network admin has told you otherwise, **you do not need to split.**

If your network admin kills long SSH sessions, rsync with `--partial` resumes automatically. If rsync is also blocked, use Option C.

---

## Prerequisites

### On Windows

You need an SSH client. You already have one — Windows 10+ ships with OpenSSH (`ssh`, `scp`, `sftp`) built into PowerShell and cmd.

For rsync, you need Git Bash (ships with Git for Windows) OR WSL. Git Bash is simpler.

Check what you have:

```powershell
# In PowerShell — these should all work
ssh -V
scp
# rsync will NOT work in PowerShell; need Git Bash
```

```bash
# In Git Bash — rsync should work
rsync --version
```

If rsync is missing from Git Bash, install Git for Windows from https://git-scm.com/download/win (current versions bundle rsync).

### On the server

Ensure the target directory exists:

```bash
ssh chriszhang@10.110.133.66 "mkdir -p /home/chriszhang/claude_code_projects"
```

(Enter password when prompted. If SSH keys are set up, no password needed.)

---

## Option A — Single Tarball via SCP (simplest)

### Step 1. Create a compressed archive with exclusions

**Use Git Bash on Windows** (not PowerShell — its native `tar` has quirky exclude syntax):

```bash
cd /c/Users/zhangyu29

tar -czvf AD_CC_pilot.tar.gz \
  --exclude='AD_CC_pilot/frontend/node_modules' \
  --exclude='AD_CC_pilot/.venv' \
  --exclude='AD_CC_pilot/backend/.venv' \
  --exclude='AD_CC_pilot/.git' \
  --exclude='AD_CC_pilot/**/__pycache__' \
  --exclude='AD_CC_pilot/**/.pytest_cache' \
  --exclude='AD_CC_pilot/**/*.pyc' \
  --exclude='AD_CC_pilot/chat_history' \
  AD_CC_pilot/
```

**Why the exclusions:**
- `node_modules` (300-500 MB, rebuilt on server with `npm install`)
- `.venv` (100-200 MB, rebuilt on server with `pip install`)
- `.git` (history — skip unless you need it)
- `__pycache__`, `.pytest_cache`, `*.pyc` (Python bytecode, regenerated)
- `chat_history` (local session logs, not needed on server)

### Step 2. Check the resulting size

```bash
ls -lh AD_CC_pilot.tar.gz
```

Likely around 100-300 MB depending on how many Damodaran files are present.

### Step 3. Transfer via SCP

```bash
scp AD_CC_pilot.tar.gz chriszhang@10.110.133.66:/home/chriszhang/claude_code_projects/
```

Enter your password. Wait for the progress bar to finish. On an average connection, 200 MB takes 2-5 minutes.

### Step 4. Extract on the server

```bash
ssh chriszhang@10.110.133.66
cd /home/chriszhang/claude_code_projects
tar -xzvf AD_CC_pilot.tar.gz
cd AD_CC_pilot
ls -la
```

You should see the full project including `HANDOFF.md`, `docs/`, `backend/`, `frontend/`, `knowledge_base/`.

### Step 5. Optional — clean up the archive

```bash
# On the server, after you confirm the extraction worked:
rm ../AD_CC_pilot.tar.gz

# On Windows, after you confirm the server has it:
rm /c/Users/zhangyu29/AD_CC_pilot.tar.gz
```

---

## Option B — Rsync (recommended for reliability)

Rsync only transfers what has changed and resumes interrupted transfers automatically. Best choice for a large, important project.

### Step 1. Run this single command in Git Bash

```bash
rsync -avzP \
  --exclude 'node_modules' \
  --exclude '.venv' \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude '*.pyc' \
  --exclude 'chat_history' \
  /c/Users/zhangyu29/AD_CC_pilot/ \
  chriszhang@10.110.133.66:/home/chriszhang/claude_code_projects/AD_CC_pilot/
```

Flags explained:
- `-a` archive mode (preserves timestamps, permissions, symlinks)
- `-v` verbose
- `-z` compress during transfer
- `-P` equivalent to `--partial --progress` (resumable + progress bar)

**Note the trailing slashes.** `AD_CC_pilot/` (with slash) tells rsync to transfer the folder's contents into the target folder. The target is also specified with `AD_CC_pilot/` to create the folder on the server side.

### Step 2. If the connection drops mid-transfer

Just re-run the same command. Rsync will resume from where it left off and skip files already transferred.

### Step 3. Verify on server

```bash
ssh chriszhang@10.110.133.66 "ls -la /home/chriszhang/claude_code_projects/AD_CC_pilot"
```

You should see `HANDOFF.md`, `docs/`, `backend/`, `frontend/`, `knowledge_base/`, `CLAUDE.md`, `PRD.md`, etc.

### Advantages over SCP
- Resumable (huge advantage on unstable connections)
- Idempotent (can re-run safely to sync only differences)
- No need to create a local tarball first

---

## Option C — Split Tarball (only if size limit exists)

Use this only if Option A or B fails due to a real size limit.

### Step 1. Create the tarball (same as Option A Step 1)

```bash
cd /c/Users/zhangyu29
tar -czvf AD_CC_pilot.tar.gz \
  --exclude='AD_CC_pilot/frontend/node_modules' \
  --exclude='AD_CC_pilot/.venv' \
  --exclude='AD_CC_pilot/backend/.venv' \
  --exclude='AD_CC_pilot/.git' \
  --exclude='AD_CC_pilot/**/__pycache__' \
  --exclude='AD_CC_pilot/**/.pytest_cache' \
  --exclude='AD_CC_pilot/**/*.pyc' \
  --exclude='AD_CC_pilot/chat_history' \
  AD_CC_pilot/
```

### Step 2. Split into 150 MB parts

```bash
split -b 150M AD_CC_pilot.tar.gz AD_CC_pilot.tar.gz.part.
```

This produces files like:
- `AD_CC_pilot.tar.gz.part.aa`
- `AD_CC_pilot.tar.gz.part.ab`
- `AD_CC_pilot.tar.gz.part.ac`
- ...etc.

Check them:
```bash
ls -lh AD_CC_pilot.tar.gz.part.*
```

### Step 3. Transfer each part via SCP

Option 3a — one command transfers all parts:
```bash
scp AD_CC_pilot.tar.gz.part.* chriszhang@10.110.133.66:/home/chriszhang/claude_code_projects/
```

Option 3b — transfer in a loop (lets you retry a specific part if one fails):
```bash
for part in AD_CC_pilot.tar.gz.part.*; do
  echo "Sending $part..."
  scp "$part" chriszhang@10.110.133.66:/home/chriszhang/claude_code_projects/
done
```

### Step 4. Reassemble on the server

```bash
ssh chriszhang@10.110.133.66

cd /home/chriszhang/claude_code_projects
cat AD_CC_pilot.tar.gz.part.* > AD_CC_pilot.tar.gz

# Verify size matches original
ls -lh AD_CC_pilot.tar.gz

# Extract
tar -xzvf AD_CC_pilot.tar.gz
cd AD_CC_pilot
ls -la
```

### Step 5. Clean up

```bash
# On server, after confirming extraction worked:
rm AD_CC_pilot.tar.gz.part.*
rm AD_CC_pilot.tar.gz

# On Windows, after confirming server has everything:
rm AD_CC_pilot.tar.gz*
```

### Optional — integrity check (paranoid mode)

If you want to be absolutely certain the split/recombine didn't corrupt anything, check the SHA-256 hash on both sides:

```bash
# On Windows (Git Bash) after creating the tarball:
sha256sum AD_CC_pilot.tar.gz

# On server after reassembly:
sha256sum AD_CC_pilot.tar.gz
```

Hashes should match exactly.

---

## After Transfer — Set Up on the Server

Once the folder is on the server:

```bash
ssh chriszhang@10.110.133.66
cd /home/chriszhang/claude_code_projects/AD_CC_pilot

# Read the handoff first
cat HANDOFF.md

# Set up backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn pydantic openpyxl pytest
# Or, if requirements.txt exists: pip install -r requirements.txt

# Run tests to verify baseline
pytest tests/engine/ -v
# Expect 65 passing

# Set up frontend
cd ../frontend
npm install
```

Start Claude Code in the project directory:

```bash
cd /home/chriszhang/claude_code_projects/AD_CC_pilot
claude   # or your configured launch command
```

The first thing Claude should do is read `HANDOFF.md`, then the four key docs listed there.

---

## Troubleshooting

### `Permission denied (publickey)` when running SSH
SSH keys aren't set up. Use password authentication:
```bash
ssh -o PreferredAuthentications=password chriszhang@10.110.133.66
```

If you want to stop typing the password, set up SSH keys:
```bash
# On Windows (Git Bash)
ssh-keygen -t ed25519    # accept defaults, optionally set passphrase
ssh-copy-id chriszhang@10.110.133.66
# Now SSH logs in without password
```

### `tar: Cannot stat: No such file or directory` on exclude patterns
You're running native Windows `tar` which has different glob semantics. Switch to Git Bash.

### `rsync: command not found`
You're in PowerShell. Run `rsync` in Git Bash instead.

### Transfer is unbearably slow
Try `-z` compression (already in rsync command). If still slow:
- Check if your corporate VPN/firewall is throttling SSH
- Try a different time of day
- Split into smaller parts and transfer overnight

### Server disk full
Check with `df -h /home/chriszhang`. If low on space, delete old projects or ask your sysadmin.

### File permissions wrong after extraction
```bash
# On server, fix permissions
chmod -R u+rwX /home/chriszhang/claude_code_projects/AD_CC_pilot
# Scripts need execute
chmod +x /home/chriszhang/claude_code_projects/AD_CC_pilot/start_claude.sh 2>/dev/null || true
```

---

## Quick Reference — Pick One of These

**If network is stable and folder is under ~500 MB:**
```bash
# Git Bash, one-time setup + transfer
cd /c/Users/zhangyu29
tar -czvf AD_CC_pilot.tar.gz --exclude='AD_CC_pilot/frontend/node_modules' --exclude='AD_CC_pilot/.venv' --exclude='AD_CC_pilot/**/__pycache__' --exclude='AD_CC_pilot/.git' AD_CC_pilot/
scp AD_CC_pilot.tar.gz chriszhang@10.110.133.66:/home/chriszhang/claude_code_projects/
ssh chriszhang@10.110.133.66 "cd /home/chriszhang/claude_code_projects && tar -xzvf AD_CC_pilot.tar.gz"
```

**If you want the best experience (recommended):**
```bash
# Git Bash, single resumable command
rsync -avzP --exclude 'node_modules' --exclude '.venv' --exclude '__pycache__' --exclude '.git' /c/Users/zhangyu29/AD_CC_pilot/ chriszhang@10.110.133.66:/home/chriszhang/claude_code_projects/AD_CC_pilot/
```

**If you must split:**
See Option C above.

---

## Summary Answers to Your Three Questions

1. **How to use terminal commands to upload from Windows to server**
   → Use `scp` or `rsync` from Git Bash. `rsync` is better because it is resumable.

2. **Whether you still need to split into packages under 200 MB**
   → No. SSH transfers have no inherent size limit. The 200 MB limit is a web-upload constraint (claude.ai file uploads, some corporate DLP tools) — it does not apply to SCP, SFTP, or rsync over SSH. Only split if your network admin has explicitly confirmed an SSH-level size restriction.

3. **Exact steps for sending multiple small packages**
   → See Option C. In short: `split -b 150M archive.tar.gz archive.tar.gz.part.` then `scp archive.tar.gz.part.* user@host:/target/` then on server `cat archive.tar.gz.part.* > archive.tar.gz && tar -xzvf archive.tar.gz`.
