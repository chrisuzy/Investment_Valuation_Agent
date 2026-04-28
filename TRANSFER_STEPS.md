# Step-by-Step Transfer Guide (Beginner-Friendly)

**Goal:** Copy your `AD_CC_pilot` folder from your Windows computer to the Linux server at `chriszhang@10.110.133.66`.

**You do not need to know Linux.** You open one window, paste three commands (one at a time), type your password, and wait.

> **NOTE:** We use `scp` here, not `rsync`. Many Git Bash installations do not include rsync, which causes `command not found` errors. `scp` is always built in and always works.

---

## What will happen

One command will copy your entire `AD_CC_pilot` folder — all your code, all your documents, all your data — to the server.

It will skip four things because they are large and automatically regenerated on the server:
- `node_modules` (frontend dependencies, rebuilt by `npm install`)
- `.venv` (Python virtual environment, rebuilt by `pip install`)
- `__pycache__` (Python compiled cache)
- `.git` (git history)

Everything else — all your Python files, TypeScript files, documents, Excel files, knowledge base — gets transferred.

The tool is called **rsync**. Think of it as a smart copy-paste that also compresses data during transfer and resumes if the connection drops.

---

## What you need before starting

### 1. Git Bash must be installed

You very likely already have it. To check:
- Click the Windows Start menu
- Type: `Git Bash`
- If it shows up, you have it. Click it.
- If it doesn't, download Git for Windows from https://git-scm.com/download/win and install with default options.

Git Bash is a black window that looks like a terminal. That's where you'll paste the command.

### 2. Know your server password

You will need to type the password for `chriszhang@10.110.133.66` when asked. When you type it, **nothing will appear on screen** — no dots, no stars, nothing. That is normal. Just type it and press Enter.

### 3. Make sure the server folder exists

You only need to do this once, before the very first transfer. Open Git Bash and run this single command:

```
ssh chriszhang@10.110.133.66 "mkdir -p /home/chriszhang/claude_code_projects"
```

It will ask for your password. Type it (invisible) and press Enter. You should see no error message. If you see something like "Connection refused" or "Host unreachable," stop — your server isn't accessible from this network, and you need to contact whoever set it up.

---

## THE COMMANDS (three one-liners, run one at a time)

Open Git Bash. Copy each command below exactly as it is (each is ONE continuous line). Paste into Git Bash (right-click inside the window, or press `Shift+Insert`). Press Enter. Wait for it to finish before moving to the next one.

### Command 1 — Pack your folder into a compressed archive

```
cd /c/Users/zhangyu29 && tar --exclude='AD_CC_pilot/frontend/node_modules' --exclude='AD_CC_pilot/.venv' --exclude='AD_CC_pilot/__pycache__' --exclude='AD_CC_pilot/backend/__pycache__' --exclude='AD_CC_pilot/backend/engine/__pycache__' --exclude='AD_CC_pilot/backend/tests/__pycache__' --exclude='AD_CC_pilot/.git' --exclude='AD_CC_pilot/.pytest_cache' --exclude='AD_CC_pilot/chat_history' -czvf AD_CC_pilot.tar.gz AD_CC_pilot/
```

Filenames scroll by as they are packed. Takes 1-3 minutes. When the `$` prompt returns, a file called `AD_CC_pilot.tar.gz` now exists at `C:\Users\zhangyu29\`.

### Command 2 — Upload the archive to the server

```
scp /c/Users/zhangyu29/AD_CC_pilot.tar.gz chriszhang@10.110.133.66:/home/chriszhang/claude_code_projects/
```

Enter your password (invisible). A progress bar shows the transfer. Typically 3-10 minutes on a normal connection.

### Command 3 — Extract the archive on the server

```
ssh chriszhang@10.110.133.66 "cd /home/chriszhang/claude_code_projects && tar -xzvf AD_CC_pilot.tar.gz && echo DONE && ls AD_CC_pilot"
```

Enter your password. Filenames scroll as the server extracts. When you see `DONE` followed by a list that includes `HANDOFF.md`, `docs`, `backend`, `frontend`, `knowledge_base` — the transfer is complete.

### Optional Command 4 — Clean up the archive file

Once you have confirmed the project is on the server, you can delete the tarball from both sides to save disk space:

```
ssh chriszhang@10.110.133.66 "rm /home/chriszhang/claude_code_projects/AD_CC_pilot.tar.gz"
```

```
rm /c/Users/zhangyu29/AD_CC_pilot.tar.gz
```

---

## What happens after you press Enter

1. **Password prompt.** Git Bash will show:
   ```
   chriszhang@10.110.133.66's password:
   ```
   Type your server password (you will not see anything as you type — that's normal). Press Enter.

2. **The transfer starts.** You will see lines flying by like:
   ```
   sending incremental file list
   AD_CC_pilot/
   AD_CC_pilot/CLAUDE.md
             13,450 100%  ...
   AD_CC_pilot/PRD.md
             18,928 100%  ...
   AD_CC_pilot/backend/
   AD_CC_pilot/backend/engine/data_dictionary.py
              8,432 100%  ...
   ...
   ```
   Each file is listed with its size and a percentage. Large files take longer; tiny files flash by. You will see a progress bar for each.

3. **The total time.** On a typical network, 150-300 MB takes about 3-10 minutes. Most of the time will be spent on Damodaran Excel files in `knowledge_base/`.

4. **It finishes.** When done, you see something like:
   ```
   sent 247,123,456 bytes  received 12,345 bytes  650,000 bytes/sec
   total size is 246,998,123  speedup is 0.99
   ```
   The Git Bash prompt (`$`) returns. The transfer is complete.

5. **If the connection drops mid-transfer.** Just run the exact same command again. Rsync will pick up where it left off — it will not re-transfer files it already sent. This is the main reason we use rsync instead of simpler tools.

---

## How to check it worked

After the transfer completes, run this single command to list the files on the server:

```
ssh chriszhang@10.110.133.66 "ls -la /home/chriszhang/claude_code_projects/AD_CC_pilot"
```

You will be asked for your password again. After entering it, you should see a list that includes:
- `HANDOFF.md`
- `TRANSFER_STEPS.md`
- `CLAUDE.md`
- `PRD.md`
- `backend` (folder)
- `frontend` (folder)
- `docs` (folder)
- `knowledge_base` (folder)

If you see those, the transfer worked.

---

## What to do after the transfer

The folder is on the server. Now you need to log in to the server and set things up:

### Step A. Log in

Single command in Git Bash:

```
ssh chriszhang@10.110.133.66
```

Type your password. Once logged in, your prompt will change to something like `chriszhang@server:~$`. You are now on the Linux server.

### Step B. Go to the project folder

```
cd /home/chriszhang/claude_code_projects/AD_CC_pilot
```

### Step C. Confirm the handoff document is there

```
cat HANDOFF.md
```

This prints the document. Tells the new Claude Code session exactly where to pick up.

### Step D. Start Claude Code

Whatever command you normally use to start Claude Code on this server. If you have a `start_claude.sh` script, it's:

```
./start_claude.sh
```

When Claude Code starts, the first thing to tell it is:

> Read `HANDOFF.md`, then read the four documents it points to under `docs/`. Then continue from Phase 1 of the project plan.

---

## If something goes wrong

### "command not found: rsync"
You are in PowerShell or cmd, not Git Bash. Close the window and open Git Bash instead. Look for the program called "Git Bash" in your Start menu.

### "Permission denied (publickey)"
The server expects an SSH key, not a password. You need to either:
- Tell your sysadmin to enable password login, or
- Set up an SSH key (ask me — I'll guide you separately)

### "Connection refused" or "No route to host"
The server isn't reachable from your current network. Common causes:
- VPN not connected (if the server requires VPN)
- Wrong IP address
- Server is down

### "No space left on device"
The server's disk is full. Run `ssh chriszhang@10.110.133.66 "df -h"` to check disk space, or ask your sysadmin.

### Password is rejected
Make sure you are typing the server password for `chriszhang`, not your Windows password. If you've forgotten it, contact whoever set up the server for you.

### Transfer is very slow
If you are on VPN or a slow corporate network, this is normal. Let it run. It will finish eventually. Rsync will resume if interrupted.

### You want to cancel
Press `Ctrl+C` in Git Bash. The transfer stops. When you re-run the command later, it picks up from where it was cancelled.

---

## Short version (once you have done it once)

For future transfers, you only need these two lines in Git Bash:

```
rsync -avzP --exclude='node_modules' --exclude='.venv' --exclude='__pycache__' --exclude='.git' --exclude='.pytest_cache' --exclude='chat_history' /c/Users/zhangyu29/AD_CC_pilot/ chriszhang@10.110.133.66:/home/chriszhang/claude_code_projects/AD_CC_pilot/
```

```
ssh chriszhang@10.110.133.66
```

Copy, paste, password, wait. Done.

---

## Reference card — the commands used in this guide

| Purpose | Command |
|---|---|
| Create server folder (once) | `ssh chriszhang@10.110.133.66 "mkdir -p /home/chriszhang/claude_code_projects"` |
| Transfer your project folder | `rsync -avzP --exclude='node_modules' --exclude='.venv' --exclude='__pycache__' --exclude='.git' --exclude='.pytest_cache' --exclude='chat_history' /c/Users/zhangyu29/AD_CC_pilot/ chriszhang@10.110.133.66:/home/chriszhang/claude_code_projects/AD_CC_pilot/` |
| Verify it arrived | `ssh chriszhang@10.110.133.66 "ls -la /home/chriszhang/claude_code_projects/AD_CC_pilot"` |
| Log in to server | `ssh chriszhang@10.110.133.66` |
| Go to project folder (on server) | `cd /home/chriszhang/claude_code_projects/AD_CC_pilot` |
| Read handoff (on server) | `cat HANDOFF.md` |

Each command fits on one line. Copy it in its entirety.
