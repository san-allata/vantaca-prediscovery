---
name: session-rubric-answerer
description: Use this skill to run the complete end-to-end workflow that analyzes one or more sessions' meeting transcripts, answers each session's mapped Master Rubric questions using the Session Mapping file for context, classifies each answered row's Branch-to-TownSq capability gap, and builds a fresh, standalone Assessment workbook containing every existing rubric row plus the newly answered and classified rows. Trigger this whenever the user asks to process a session or several sessions, answer session questions, fill in the rubric, or produce or refresh an assessment snapshot from session transcripts, even if they do not use the words rubric or session explicitly. This is a conductor skill: it orchestrates rubric-answer-extractor-skill and branch-assessor-skill, and owns two scripts unique to this workflow, resolve_session_scope.py which matches Session Mapping questions to Master Rubric rows, and build_assessment_snapshot.py which renders the final standalone Assessment sheet as a downloadable xlsx file.
---

# Session Rubric Answerer

## Purpose
Process **one or more discovery sessions**: for each requested session, read its transcript, use the Session Mapping file to know which Master Rubric questions it covers, extract grounded answers from that session's transcript only, classify the resulting capability gap, and — once all requested sessions are processed — build **one fresh, standalone workbook containing a single sheet named "Assessment"** with every existing rubric row (unchanged where not touched) plus the newly answered/classified rows.

**There is no write-back and no in-place patch.** The Master Rubric data product file is read-only input. The deliverable is always a brand-new workbook, never a modified copy of the source file, and it contains only the Assessment-style rows — no Cover, Change Plan, Onboarding List, Product Backlog, Summary, or Renumber Map sheets.

## Use When
- "Process session N" / "process sessions N and M" / "process sessions 1 through 6"
- "Answer this session's rubric questions" / "fill in the missing answers from the session N transcript"
- "Give me an updated assessment sheet" / "refresh the assessment with the new session answers"

## Do Not Use When
- The user wants to classify/score already-answered rows without any new session to process — that's `branch-assessor-skill` alone.
- The user wants the original Master Rubric workbook modified or re-uploaded anywhere — this skill never writes back to any source system.
- No session number can be determined — ask the user to confirm before proceeding.

## Inputs
- **Master Rubric** — read-only, sourced by querying the `MasterRubricTemplateWithAssociaAnswers_FB.xlsx` file in the "vantaca files" data product via `getSpreadsheetInfo`/`executeQuery` against its `Assessment` sheet. This is a **file-only data product with no live sync** — treat it purely as a queryable source of existing rows, never as something to browse via SharePoint or write back to.
- **Session Mapping file** — the question-to-rubric-row mapping (e.g. `Sessions_1-6_Master_Rubric_Mapping.xlsx`, sheet `All Sessions Mapping`, columns `session`, `planned_question_id`, `planned_question`, `uid`, `qid`, `capability`, `dimension`, `priority`, `exact_master_rubric_question`). Look for it as a chat upload first; if not found in chat, search any data product(s) currently attached; if not found in either, ask the user.
- **Session transcript(s)** — one per session being processed, typically `.vtt` (strip cue-number/timestamp lines, keep speaker/text) or `.txt`. Same lookup order as the Session Mapping file: chat → attached data product(s) → ask.

## Workflow

### Step 1 — Load the existing Master Rubric rows once
Query the Master Rubric's `Assessment` sheet in full (header row 4, data from row 5). For every row capture: `dom_num, domain, cap_num, capability, dimension, priority, discovery_question (col G), branch_answer (col H), townsq_capability (col I), classification (col J), fb_priority (col K), assessor_notes (col L), qid (col P), uid (col Q)`, plus its row number. This is the baseline — every row not touched by the sessions being processed is carried into the final deliverable **unchanged**.

### Step 2 — Resolve each requested session's scope
1. Load the Session Mapping file (`getSpreadsheetInfo` then `executeQuery` for the full sheet — extract once, filter in memory, never many small targeted reads).
2. Filter its rows to the requested session number(s).
3. Run `scripts/resolve_session_scope.py` with the session's mapping rows and the full list of `{row, discovery_question}` pairs from Step 1, to match each `exact_master_rubric_question` to its Master Rubric row by normalized text.
4. **Any question that fails to resolve must be reported as unresolved — never guessed.**

### Step 3 — Extract grounded answers (session-scoped only)
For each resolved row, extract a grounded answer strictly from that session's own transcript, following `rubric-answer-extractor-skill`'s evidence discipline: answer + `Source:` line, `GAPS:` line for partial answers, `Not Found` when unsupported, `CONFLICT:` when contradictory. Never use column I (TownSq Capability) as evidence. Never pull from any other session's transcript.

### Step 4 — Classify (once, across all sessions processed this run)
Hand the union of all newly-answered rows to `branch-assessor-skill` to produce Classification + Assessor Notes per its decision ladder, proximity verdict, and dominant-blocker rule. This step only decides values in memory — there is no workbook to write J/L into in place.

### Step 5 — Build the standalone Assessment workbook
Merge Step 1's baseline rows with Step 3/4's new answers/classifications (new values override baseline for touched rows; everything else passes through unchanged). Call `scripts/build_assessment_snapshot.py` with the full merged row set to render a fresh `.xlsx` containing exactly one sheet, named `Assessment`, with columns: Dom #, Domain, Cap #, Capability, Dimension, Priority, Discovery Question, Branch Answer, TownSq Capability, Classification, FB Priority, Assessor Notes, QID, UID.

### Step 6 — Deliver and report
The script's output file is the deliverable — render it via `render_content` as a download. Report: sessions processed, mapped questions per session, resolved/unresolved counts, answer outcomes (Answered/Partial/Not Found/Conflict), classification counts, and total rows in the delivered sheet (must equal the Master Rubric's total row count — nothing dropped).

## Tool and Data Rules
- **Never open/render documents directly** — all reading happens through `executeQuery`/`getSpreadsheetInfo` or plain-text reads of transcripts.
- **One session's rows, one session's transcript** — never mix sources across sessions.
- **No write-back, ever** — the Master Rubric data product file and any chat-uploaded files are never modified. The only output is the new standalone workbook.
- **Row count integrity is mandatory**: the delivered `Assessment` sheet's row count must equal the source Master Rubric's data row count. If it doesn't, stop and report the discrepancy — do not deliver a file that silently dropped rows.
- Cite the transcript filename (and speaker/timestamp locator when available) as the source for every new answer.

## Output Format
```markdown
## Session(s) N — Assessment Snapshot Report
- Sessions processed: [...]
- Master Rubric source: vantaca files / MasterRubricTemplateWithAssociaAnswers_FB.xlsx (query only, read-only)
- Session Mapping file: <filename> (source: chat | data product)
- Transcript(s): <filename(s)> (source: chat | data product)

### Scope
- Mapped questions per session: [...] | Resolved: X of Y (list unresolved)

### Outcomes
- Answered: N | Partial (GAPS): N | Not Found: N | Conflicts: N
- Classified this run: N rows (by code: PC/AC/FB/NA counts)

### Delivery
- Total rows in delivered Assessment sheet: N (must match Master Rubric baseline row count: N)
- Download: provided in this chat

### Flags
- HITL rows, blocked rows, unresolved mappings
```

## Validation Checklist
- [ ] Every mapped question resolved to a specific Master Rubric row, or explicitly reported as unresolved.
- [ ] Every new answer follows the exact required format (answer + Source, optional GAPS), grounded only in that session's transcript.
- [ ] Classification followed `branch-assessor-skill`'s decision ladder — never inferred from column I alone.
- [ ] Delivered sheet's row count equals the Master Rubric baseline row count exactly.
- [ ] No write-back was attempted or claimed anywhere.

## Troubleshooting
- If the Session Mapping file's schema doesn't match the expected column names, report the actual schema found and ask before guessing a mapping.
- If an `exact_master_rubric_question` doesn't match any Master Rubric row (even after normalization), report it as unresolved — do not fuzzy-guess a row.
- If both `.txt` and `.vtt`/`.docx` transcripts exist and disagree, default to `.txt` but flag the discrepancy.
- If the delivered row count doesn't match the baseline, stop and report — do not deliver a truncated file.