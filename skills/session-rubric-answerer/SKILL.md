# Session Rubric Answerer

## Purpose
Process **exactly one discovery session at a time**: read that session's transcript, use that session's Analyst Workbook mapping to know which Master Rubric questions it covers and what context/must-capture notes apply, extract grounded answers from the transcript only, and patch only the resolved Branch Answer cells into the original Master Rubric workbook — leaving every other sheet, row, formula, and format untouched.

This skill is a **conductor**: it does not reimplement extraction/patching logic that already exists in other skills. It defines the sequence, the session-scoping rule, and bundles the one genuinely new piece of logic — cross-referencing the per-session Analyst Workbook against the Master Rubric to resolve exact target rows (`scripts/resolve_session_scope.py`).

## Use When
- "Process session N for [Client]" / "answer session N's questions" / "fill in the master rubric using session N's transcript"
- A session folder in SharePoint has been identified and the user wants its questions answered and the master rubric updated
- Re-running a session after a corrected transcript or updated Analyst Workbook arrives (only the affected session's rows should be touched)

## Do Not Use When
- The user wants to classify/score already-filled branch answers (PC/AC/FB) — that's `Branch Assessor Skill`, not this one.
- The user wants a JSON-only workflow with no Excel involved — use `json-question-answer-patcher` directly.
- The user wants to process multiple sessions in one pass without isolating file scope per session — clarify first; this skill's core rule is one-session-at-a-time isolation (see Boundaries).
- No session number can be determined from the transcript file/folder — ask the user to confirm the session number before proceeding.

## Inputs
- Required:
  - **Client/branch folder identity** in SharePoint (via the Extraction Data Product's root folder)
  - **Session number** N — must be explicit or unambiguously derivable from the session folder name (e.g., "Session 3") or transcript filename
  - **Session N Analyst Workbook** (`Session_{N}_Analyst_Workbook*.xlsx`) with sheets `Live Interview Tracker` and `Rubric Mapping`
  - **Session N transcript** — plain `.txt` if present, otherwise the Word transcript file (routed through `docx-transcript-extractor`)
  - **Master Rubric workbook** (`MasterRubricTemplateWithAssociaAnswers.xlsx` or equivalent), the client's ORIGINAL file — must be preserved
- Optional: existing answers policy — overwrite vs. fill-empty-only (default per branch instructions: **new answers always replace existing ones** for the target session's resolved rows only)
- Assumptions if unstated:
  - If both a `.txt` and a `.docx` transcript exist for the session, prefer the `.txt` and never invoke the docx extractor.
  - If the session number isn't explicit, infer only from unambiguous folder/file naming (`Session 3`, `Session_3_...`); if ambiguous, ask.

## Workflow

### Step 0 — Locate files in SharePoint (never open documents directly)
1. Use the Office 365 extension to browse the client's root folder (as identified via the Extraction Data Product) → `Session N` subfolder.
2. Identify: the transcript file (`.txt` preferred, else `.docx`), the `Session_{N}_Analyst_Workbook*.xlsx`, and the Master Rubric workbook (typically at the client root, one level up from `Session N`).
3. Download bytes via the Office 365 extension (`download-onedrive-file-content` or equivalent) into the working session — never render/open the document for manual reading.

### Step 1 — Ensure a plain-text transcript exists
1. If a `.txt` transcript was found, use it as-is.
2. If only a `.docx` transcript exists, invoke **docx-transcript-extractor** (`run_skill_script` → `scripts/extract_docx_text.py`) with the downloaded bytes to produce `transcript.txt` / `transcript_segments.json`. Never read the `.docx` directly.

### Step 2 — Extract the session's mapping rows
1. Load `Session_{N}_Analyst_Workbook*.xlsx` with `getSpreadsheetInfo` / `executeQuery` (per **excel-qa-processor** conventions: `SELECT * FROM data LIMIT 10000`, no `WHERE`/`rowid`, detect real column names).
2. Sheet `Live Interview Tracker`: filter rows whose `ID` starts with `S{N}-` to build a `{planned_question_id → {planned_question, must_capture}}` map, scoped to session N only.
3. Sheet `Rubric Mapping`: take every row (one or more per `Planned Question ID`), each carrying an `Exact Rubric Question` string — this is the full list of Master Rubric questions this session is responsible for.

### Step 3 — Resolve target rows in the Master Rubric
1. Load the Master Rubric `Assessment` sheet (header row 4, data from row 5; columns per `rubric-answer-extractor-integrated`'s layout reference — G = Discovery Question, H = Branch Answer).
2. Run `scripts/resolve_session_scope.py` (this skill) to match each `Exact Rubric Question` from Step 2 against Assessment column G by normalized text, producing one resolved record per mapped question: `{planned_question_id, planned_question, must_capture, exact_rubric_question, master_rubric_row}`.
3. **Any question that fails to resolve to a row must be reported as an unresolved mapping — never guessed or skipped silently.** Do not proceed to patch an unresolved row.
4. This resolved list is the **complete and exclusive scope** for this run: only these rows may be touched in Step 5.

### Step 4 — Extract grounded answers (session-scoped only)
1. Hand off to **rubric-answer-extractor-integrated** with:
   - Corpus = ONLY this session's transcript (plain text from Step 1) — never any other session's transcript or any other source document
   - Context per question = that question's `planned_question` and `must_capture` notes from Step 3 (use these to focus the search, not as evidence themselves)
   - Question list = exactly the resolved `exact_rubric_question` values from Step 3
2. Follow that skill's full grounding discipline: strict evidence-only answers, exact answer-plus-Source (and optional GAPS) format, `Not Found` when unsupported, `CONFLICT:` when contradictory, no use of column I (TownSq Capability) as evidence, mandatory self-audit pass.
3. One or more mapped questions can share a single Analyst Workbook row's context — when a `Planned Question ID` maps to multiple `Exact Rubric Question`s, answer each Master Rubric question separately but let the shared `planned_question` / `must_capture` context inform all of them.

### Step 5 — Patch the Master Rubric in place (only resolved rows, only column H)
1. Hand off the final `{master_rubric_row, branch_answer}` pairs to **json-rubric-tools-skill**'s `patch_xlsx_inplace.py`, targeting the Master Rubric's ORIGINAL file and column H only.
2. Confirm via the script's `sheets_preserved` output that every original sheet, formula, style, and macro is intact and unchanged.
3. Confirm the row set patched exactly matches Step 3's resolved scope — no more, no fewer.
4. Do not touch columns I/J/K/L/M/N/O or any other sheet (Cover, Change Plan, Onboarding List, Product Backlog, Summary, Renumber Map).

### Step 6 — Deliver and report
1. Upload/save the patched Master Rubric workbook back to its SharePoint location via the Office 365 extension (or provide as a download if the user is working locally).
2. Report: session number processed, total mapped questions, rows patched, `Not Found` count, partial/GAPS count, conflicts, and any unresolved mappings requiring follow-up.

## Output Format
Deliver a run report:
```markdown
## Session N — Rubric Update Report
- Client/Branch:
- Transcript source: <filename> (txt | docx-extracted)
- Analyst Workbook: <filename>
- Master Rubric: <filename> (patched in place)

### Scope
- Planned questions (session N): X
- Mapped Master Rubric questions: Y
- Resolved rows: Y of Y (list any unresolved)

### Answer Outcomes
| Master Rubric Row | Question | Outcome | Notes |
|---|---|---|---|
| ... | ... | Answered / Partial / Not Found / Conflict | ... |

### Delivery
- sheets_preserved: [...]
- Rows patched: [row list]
- File delivered to: <path or download>
```
Plus the patched workbook itself (in-place delivery, never a rebuild).

## Tool and Data Rules
- **Never open/render documents directly** — all reading happens through `executeQuery`/`getSpreadsheetInfo` (Excel), `docx-transcript-extractor` (Word), or plain-text file reads. No manual "reading" of binary files.
- **One session, one run**: never pull transcript, mapping, or answer content from any session other than the one requested. If the Master Rubric already contains answers for other sessions, do not touch those rows.
- **In-place patch only**: the Master Rubric must never be rebuilt from JSON as a deliverable (that drops other sheets). Always use `patch_xlsx_inplace.py` on the original file.
- **Column H only**: never write to columns I/J/K/L or any calculated column (M/N/O), and never alter any other sheet.
- Cite the transcript filename (and speaker/timestamp locator when available) as the source for every answer.
- If existing answers are present in target rows, overwrite them (per branch policy: new answers replace old), but state this in the report.
- Confirm file locations and session number with the user before writing if any ambiguity exists in SharePoint folder structure.

## Examples
### Example Request
"Process Session 3 for Heritage Property — use the transcript to answer this session's rubric questions and update the master rubric."

### Expected Behavior
1. Browse SharePoint: `Heritage Property/Session 3/` for transcript + `Session_3_Analyst_Workbook*.xlsx`; `Heritage Property/MasterRubricTemplateWithAssociaAnswers.xlsx` at root.
2. Confirm transcript format (txt preferred); extract from docx if needed.
3. Pull only `S3-*` rows from the Analyst Workbook.
4. Resolve those mapped questions to exact Master Rubric rows.
5. Extract grounded answers strictly from the Session 3 transcript.
6. Patch only those resolved rows' column H in the original Master Rubric file.
7. Deliver the report plus patched file.

## Validation Checklist
- [ ] Only Session N's transcript, mapping rows, and target rubric rows were used — no cross-session contamination.
- [ ] Every mapped question resolved to a specific Master Rubric row, or was explicitly reported as unresolved.
- [ ] Every answer follows the exact required format (answer_corpus plus Source line, plus optional GAPS line), no CONFIDENCE line embedded.
- [ ] Original Master Rubric file preserved — all sheets, formulas, formatting, macros intact (sheets_preserved confirmed).
- [ ] Only column H was modified, only on the resolved row set.
- [ ] No document was opened/read directly — all access went through skills/tools.
- [ ] Report delivered with per-row outcomes and any gaps/conflicts/unresolved items surfaced.

## Troubleshooting
- If the Analyst Workbook's `ID` format doesn't match `S{n}-Q{n}`, ask the user to confirm the session-number column/format rather than guessing.
- If an `Exact Rubric Question` doesn't match any Assessment column G text (even after normalization), report it as unresolved — do not fuzzy-guess a row.
- If both `.txt` and `.docx` transcripts exist and disagree in length/content, default to `.txt` but flag the discrepancy to the user.
- If the Master Rubric file can't be found at the expected client root, ask the user for its exact SharePoint path rather than searching broadly.
- If `patch_xlsx_inplace.py` reports any sheet missing from `sheets_preserved`, stop and report the failure — do not deliver a partially-preserved file.