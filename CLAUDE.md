# CLAUDE.md — Lessons, Philosophy, and Operational Guidance

This is a living document. Update it after every session with new lessons learned.

---

## CRITICAL RULES — Non-Negotiable

### Rule 1: Never Stop Without Explanation
If you cannot continue, you MUST immediately tell the user why. Silence is unacceptable. The user should never have to wait minutes wondering if you are stuck. If a tool call fails, if you hit a context limit, if you are unsure — say so immediately in the same response.

### Rule 2: Never Announce Work Without Doing It
"Let me do X" followed by stopping is worse than doing nothing. If you say you will do something, the very next thing must be the tool call that does it. No announcements without action in the same response.

**Specific pattern to avoid:** After receiving large tool output, DO NOT write a summary paragraph as the last thing in the response. Either end with a tool call, or put the summary BEFORE the tool call. A response that ends with text and no tool call is a finished turn — there is no "continuing."

### Rule 3: Execute, Don't Over-Plan
Planning is only useful if it leads to immediate execution. Do not:
- Create task lists for simple work
- Read 6 files before writing 1 line of code
- Produce analysis paragraphs between each action
- Ask "is this the right understanding?" when you already know the answer

If the plan is clear, start writing code immediately.

### Rule 4: Break Every Task Into Baby Steps
Never attempt a large task in one shot. Always decompose into the smallest possible sub-steps and execute them one at a time. This is the **#1 principle** for preventing context window exhaustion.

- A "baby step" = one file edit, one new file, or one small logical change.
- Never write a full file rewrite (500+ lines) in a single tool call. Split it into sections.
- If a task has 5 parts, do part 1, verify, then part 2, etc. — never all 5 at once.
- Large tool outputs consume context fast. Prefer targeted reads/edits over full file rewrites.
- When in doubt, make the step smaller, not bigger.

**Why this matters:** Attempting too much at once causes context window overflow, which leads to compaction, which leads to lost state, which leads to the "unexplained stop" pattern. Small steps prevent all of this.

### Rule 5: Every Response MUST End With a Tool Call
If the work is not done, your response MUST contain a tool call. A response that ends with only text and no tool call is a **completed turn** — there is no implicit "I'll continue next." This means:
- If you just finished writing File A and File B is next, the **same response** must include the tool call for File B.
- If you are mid-task and producing text, append a tool call at the end.
- The ONLY acceptable response without a tool call is one that says "I'm done" or explicitly asks the user a question.
- Violating this rule is what causes the "unexplained stop" pattern. It is the #1 source of user frustration.

### Rule 6: The Stalling Fix = Baby Steps + Immediate Tool Call
The stalling pattern happens when a step is too big. When the step is tiny, there's always a clear next tool call. The fix is NOT about limiting text — it's about ensuring every response has a concrete, small, tool-call-sized action.

**Before writing ANY text, ask:** "What is my ONE baby-step tool call this response?" Make that call. Text is decoration around the tool call, not the other way around.

**If you find yourself writing analysis without a tool call queued, you skipped a baby step.** Go back to the task list, find the next tiny step, and call the tool.

### Rule 7: NEVER "Do the Remaining N Things in One Go"
When there are multiple similar tasks (e.g., write 11 sheet exporters), NEVER attempt to write them all at once. This ALWAYS causes stalling — the response gets too large, context fills up, and the tool call never happens.

**Instead:**
1. Create a numbered task list with ONE item per mini-step
2. Execute ONE task per response
3. Check it off when done
4. Move to the next

Even if the tasks are "similar" or "simple", do them ONE AT A TIME. The cost of being slow is far less than the cost of stalling and having to redo everything.

**Anti-pattern:** "Let me write all 11 remaining sheets in one go" → ALWAYS fails
**Correct pattern:** "Sheet 3: Cost of Capital" → write it → test → "Sheet 4: R&D Converter" → write it → test → ...

### Rule 8: Excel Export = Calculator with Formulas, NEVER Static Values
When the user asks for an Excel spreadsheet "calculator", EVERY computed cell MUST contain an Excel formula (e.g., `=B12/B11`, `=SUM(D5:D10)`), NOT a pre-computed Python value. Only raw input cells (CIQ data, Damodaran references, user assumptions) should be static values. Computed/gray cells must always be formulas so changing any input recalculates the entire workbook.

**This requires:**
- Fixed cell positions (not dynamic `row += 1`) so formulas can reference specific cells
- A cell-position map returned by each sheet writer so cross-sheet formulas work (e.g., `='Input Sheet'!B15`)
- Excel formula syntax (e.g., `=B5*(1-B20)` not `=ebit*(1-tax)`)

**Anti-pattern:** Writing `_cell(ws, row, 2, fin0.ebit / fin0.revenues)` — this bakes in the answer
**Correct pattern:** Writing `_cell(ws, row, 2, "=C13/C12")` — this is a live formula

---

## Lessons Learned (Updated 2026-03-19)

### Lesson 1: The Stalling Pattern
**What happened:** Multiple times in Session 3, Claude said "let me do it" or "let me build that now" and then the response ended without any code being written. This happened 3+ times in a row, wasting 10+ minutes of the user's time.

**Root causes identified:**
1. Response boundaries after tool results — after a tool returns, Claude sometimes emits text but no follow-up tool call
2. Over-preparation — reading too many files before writing any code
3. Verbose analysis between actions — spending tokens on text instead of tool calls
4. COM automation timeouts — 90-second commands with 30-second poll timeouts caused cascading retries that looked like stalling

**How to prevent:**
- Always include the next tool call in the same response as the previous tool's result
- If a bash command will take >60 seconds, use `run_in_background` with appropriate timeout
- Minimize text between tool calls — prefer parallel tool calls over sequential analysis
- If you feel yourself writing a summary paragraph, stop and make a tool call instead

### Lesson 2: Don't Create Tasks for Simple Work
**What happened:** Claude created 3 TaskCreate entries for a plan that could have been executed directly with 3 Write tool calls.

**Rule:** Only use TaskCreate for genuinely complex multi-step work with dependencies. For a 3-file plan where you know exactly what to write, just write the files.

### Lesson 3: Batch Independent Work
**What happened:** Claude made sequential tool calls that could have been parallel, adding unnecessary round-trips.

**Rule:** If two file reads, two file writes, or two bash commands are independent, make them in the same response as parallel tool calls. This is faster and reduces the chance of stopping between them.

### Lesson 4: COM Automation Needs Special Handling
**What happened:** Excel COM automation via pywin32 takes 90-120 seconds. Using 30-second poll timeouts caused repeated timeouts and retries.

**Rules for COM work:**
- Set `timeout: 300000` (5 minutes) for any bash command involving Excel COM
- Use `run_in_background: true` for long COM operations
- Consider whether COM is even needed — often a pure openpyxl solution (generating Excel file with formula text) is simpler and doesn't require Excel to be open

### Lesson 5: Context Window Management
**What happened:** Long sessions with many file reads and verbose analysis filled the context window, leading to compaction and loss of important details.

**Rules:**
- Don't re-read files you've already read unless content has changed
- Don't produce multi-paragraph analysis when a table or bullet list suffices
- Save important findings to memory files early (don't wait until end of session)
- When context is getting large, prioritize code output over explanation

### Lesson 6: When the User Says Stop, Actually Stop
**What happened:** User said "stop everything" but Claude continued executing background tasks or immediately jumped back into execution without proper diagnosis.

**Rule:** When told to stop:
1. Cancel any running background tasks
2. Delete/close any open task items
3. Acknowledge the stop
4. Wait for instruction — do NOT immediately start working again
5. If asked to diagnose, diagnose WITHOUT also trying to fix

### Lesson 7: Always Restart Backend After Code Changes
**What happened:** Multiple times, code changes were made but the running uvicorn server still served old code. The user got the same error repeatedly.

**Rule:** After ANY backend Python change, ALWAYS kill the old process and restart. Verify with a curl test that the new code is active. `--reload` flag is unreliable for model/schema changes.

### Lesson 8: Never Hard-Code Fiscal Years or Regions
**What happened:** Fiscal years were computed as `datetime.now().year - offset` which was wrong for non-calendar fiscal year companies (e.g., Lenovo March FY end). Region was defaulted to "US" for all companies.

**Rule:** Always derive fiscal years from CIQ period dates. Always derive region from the company's country.

### Lesson 9: User Corrects CIQ Mnemonics — Use Theirs
**What happened:** Used IQ_TOTAL_TAX but the correct mnemonic is IQ_INC_TAX. Used IQ_EFFECTIVE_TAX_RATE but correct is IQ_EFFECT_TAX_RATE with /100.

**Rule:** Before generating a new CIQ template, check the user's corrected template file for the actual mnemonics. The user has direct access to the CIQ plugin and knows which IDs work.

### Lesson 10: Retrieve Latest Context Before Acting
**What happened:** After session resume, acted on stale context without reading current file state. Made changes that conflicted with user's recent work.

**Rule:** On session resume, always read the key files (InputSheet.tsx, TrailingTwelveMonth.tsx, routes.py, capiq_formula_map.py) before making any changes.

---

## Interaction Philosophy

### Do
- Start writing code within the first 1-2 tool calls of receiving a task
- Use parallel tool calls aggressively
- Give progress updates within code-producing responses (not standalone text-only responses)
- If stuck, immediately say "I'm stuck because X" — never go silent
- Save important context to memory files proactively during work (not just at end)

### Don't
- Don't announce what you're about to do without also doing it
- Don't read more than 2-3 files before starting to write code
- Don't create task lists for tasks with fewer than 5 clear steps
- Don't produce standalone analysis messages — combine analysis with action
- Don't retry the same failing approach more than once without telling the user
- Don't produce reflection/apology text when you could be producing code

### Communication Style
- User communicates in English, PRD is in Chinese
- User values speed and execution over thoroughness of explanation
- User gets frustrated by:
  - Unexplained pauses/stops
  - Announcements without follow-through
  - Repeated failures without diagnosis
  - Over-planning
- User appreciates:
  - Working code on first attempt
  - Honest immediate communication about problems
  - Quick fixes without excessive discussion

---

## Project-Specific Notes

### Almarai (SASE:2280) is the Test Company
All ground truth data is for Almarai, a Saudi food company. The ticker format for CIQ is "SASE:2280".

### Ground Truth Excel Structure
File: `knowledge_base/groud_truth/ground_truth.xlsx` (note: "groud_truth" is a typo in the folder name, do not rename)
- Sheet name is "Input sheet" (not "Input")
- 17 sheets total matching Damodaran's fcffsimpleginzu.xlsx
- Values are in Saudi Riyals (SAR)
- Monetary values in millions

### CIQ Formula Syntax
```
=CIQ("TICKER","MNEMONIC","PERIOD")
```
- Period: "IQ_FY-0" (most recent FY), "IQ_FY-1" (prior FY), "IQ_FQ-0" (most recent quarter)
- Market items: no period argument
- Template fetches 8 quarters (FQ-0..FQ-7) for Damodaran LTM method

### CIQ Mnemonics — User-Corrected (DO NOT CHANGE)
- Tax expense: `IQ_INC_TAX` (NOT IQ_TOTAL_TAX — user corrected this)
- Effective tax rate: `IQ_EFFECT_TAX_RATE` with /100 and period "IQ_FY"
- R&D: `IQ_RD_EXP` primary, `IQ_RD_EXP_FN` as fallback when primary returns zero
- All others verified working — see MEMORY.md for full table

### Damodaran LTM Calculation (Confirmed with User)
NOT a simple sum of 4 quarters. Damodaran's method:
```
n = quarters_since_10k (0-3)
LTM = FY0 + sum(FQ-0..FQ-(n-1)) - sum(FQ-4..FQ-(4+n-1))
```
Old quarters (subtracted) are the SAME calendar quarters from prior year, replaced by new data.

### Industry Name Matching
Only 1 mismatch out of 95: "Retail (Online)" from indname.xlsx → maps to "Retail (General)" in Damodaran.
Alias table + fuzzy prefix matching in `DamodaranStore.lookup_industry()`.

### Companies Missing from indname.xlsx
Damodaran's indname.xlsx has ~48K companies but is NOT comprehensive. Notable gaps:
- Some ADRs (BIDU, TSM ADR listing)
- Some dual-listed tickers (SEHK:9988 for Alibaba HK)
- User manually added Alibaba (NYSE:BABA) to indname.xlsx
- `industry_override` parameter available for tickers not in the file
