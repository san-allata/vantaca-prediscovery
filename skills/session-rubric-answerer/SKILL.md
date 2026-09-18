---
name: session-rubric-answerer
description: "Process discovery session transcripts against the Associa Branch Readiness Master Rubric: extract answers to rubric questions, classify branch-to-TownSq capability backlogs (PC/AC/FB/NA), and deliver Assessment xlsx workbooks with full citations. Use this skill whenever the user asks to process a session, answer rubric questions, classify readiness gaps, or refresh an Assessment snapshot—even if they don't explicitly mention 'rubric' or 'classification'. Trigger phrases: 'Process session N', 'answer this session's questions', 'classify branch answers', 'give me an updated assessment', 'refresh the assessment'."
---

## Session Rubric Answerer — Full Instructions

You process branch discovery session transcripts against the Associa Branch Readiness Master Rubric. Your output is one or more downloadable Assessment xlsx workbooks (one per capability-group batch) containing branch answers, TownSq capability notes, classifications (PC / AC / FB / NA), and assessor notes.

**Before doing anything, read `references/session_processing_guide.md`.** It is the canonical operational guide for this skill and contains the complete step-by-step workflow, batching strategy, transcript fetch strategy, and all verified patterns from live runs. This SKILL.md is a summary — the guide is the source of truth.

---

## Reference Files & Resources

- `references/session_processing_guide.md` — **Read this first.** End-to-end workflow, batching strategy, transcript fetch approach, verified SQL patterns, known failure modes and fixes.
- `references/rubric_index.json` — Lightweight rubric index (representative rows). Use for scope resolution. Pass as `rubric_index` in inputData when calling v2 scripts.
- `scripts/resolve_session_scope_v2.py` — Resolves session mapping rows to rubric rows. Input: `{ "mapping_rows": [...], "rubric_index": [...] }`. Output: resolved rows or list of unresolved questions.
- `scripts/build_assessment_batch.py` — **Canonical production xlsx builder.** Handles ≤30-row batches, formats colors/freeze/wrap/column widths. Use via `execute_code` (Python), passing rows as `input` JSON parameter. Reads from `input.json`, writes `Assessment_Run<N>_<CapGroup>.xlsx`. **This is the ONLY script to use for new production builds.**
- `scripts/build_assessment_snapshot_v2.py` — **DEPRECATED.** Do not use for production. Causes payload overflow with 50+ rows. Kept only for backward compatibility with old automation.
- `scripts/build_assessment_snapshot.py` — **DEPRECATED.** Original script. Do not modify. Use `build_assessment_batch.py` instead.
- `assets/MasterRubricTemplateWithAssociaAnswers_FB.xlsx` — Master Rubric asset (read-only reference).

### Integrated Skills
- **`branch-assessor-skill`**: Used in Step 7 to classify each answer per the decision ladder (PC/AC/FB/NA). Provides Classification and Assessor Notes based on proximity to TownSq capability and dominant-blocker rule.
- **`rubric-answer-extractor-skill`**: Used in Step 6 to ground each answer in transcript evidence. Provides answer + Source line + BACKLOGS tracking.

Do not call these skills directly; they are invoked internally during Steps 6–7.

---

## Critical Note on Reference Guide Maintenance

**`references/session_processing_guide.md` is the canonical operational guide.** This SKILL.md is a summary only. If anything here conflicts with the guide, the guide wins.

**Keep in sync:** The guide should be updated whenever:
- A new SQL pattern is verified
- A failure mode is discovered and fixed
- Batching rules change
- Script versions change

Review and sync both documents during monthly maintenance cycles.

---

## Workflow Summary

**Read `references/session_processing_guide.md` for the full workflow.** The summary below is for quick orientation only.

### Step 1 — Wait for explicit user input
Do not proceed until the user provides ALL of:
- A session number (or range), AND
- Confirmation that the transcript and mapping CSV are in the attached data product(s)

If only one is provided, ask for the other before doing anything. Never call any script at startup or on context load.

### Step 2 — Query the Session Mapping CSV
Call `getSpreadsheetInfo` first to confirm column names. Then use `executeQuery` with the exact pattern from the guide. Do NOT use `SELECT *` with a WHERE clause that filters on a column name you haven't verified.

```sql
SELECT session, planned_question_id, uid, qid, capability, dimension, priority,
       exact_master_rubric_question
FROM data
WHERE session = <N>
LIMIT 100
```

If the result set is empty, stop and report: "No mapping rows found for session N."

### Step 3 — Load rubric index
Call `read_skill_resource` with `resourcePath: "references/rubric_index.json"` and parse the result as JSON.

### Step 4 — Resolve session scope
Call `resolve_session_scope_v2.py` with mapping rows + rubric index via `run_skill_script`. Confirm 100% of rows resolved before proceeding. If any rows are unresolved, report them and stop.

### Step 5 — Fetch transcript evidence (batched by topic)
Do NOT attempt to load the full VTT in one `get_information_from_dataProduct` call — the retrieval system returns chunked results. Instead make **2–4 targeted calls**, each covering a distinct topic cluster (e.g. "management fees + contract storage", "supply charges + reimbursables", "amenity rentals + deposits", "audit + tax + CPA"). Hold all retrieved evidence in context. If no transcript is found, stop and report: "Transcript not provided or not found."

### Step 6 — Extract branch answers
For each resolved row, locate the branch's answer in the retrieved transcript evidence. Use the evidence-grounding discipline from `rubric-answer-extractor-skill`:
- **Answer:** [text extracted from transcript]
- **Source:** [filename, speaker, timestamp]
- **GAPS:** [any partial answer notes]
- **Not Found:** [when transcript is silent on this topic]

Cite speaker and timestamp for every answer. Never use column I (TownSq Capability) as evidence for the branch answer.

### Step 7 — Classify each row
Apply the `branch-assessor-skill` decision ladder:
- **PC** (Process Change) — TownSq supports this; branch must change how they work
- **AC** (Adoption/Config) — TownSq supports this after configuration/setup
- **FB** (Feature Backlog) — TownSq cannot support this today
- **NA** (Not Applicable) — Not applicable to this branch
- **HITL** (Human In The Loop) — Flag amber when answer is "Not Found" OR confidence is Low

Never infer a classification from Branch Answer alone; always apply the decision ladder.

### Step 8 — Build Assessment xlsx (BATCHED)
**This is the critical step where previous attempts failed. Follow the batching rules exactly.**

See `references/session_processing_guide.md` → "Batched Build Strategy" for full detail. Summary:
- Split rows into capability-group batches of ≤ 30 rows each
- For each batch: call `execute_code` (Python) passing the rows as the `input` JSON parameter
- Use `scripts/build_assessment_batch.py` ONLY — it handles all formatting (colors, freeze, wrap, column widths)
- Deliver each batch file as a download via `render_content`
- **Never pass all 100 rows in a single `execute_code` call** — this causes payload overflow / timeout
- **If `execute_code` times out:** reduce batch size from 30 to 20 rows and retry

### Step 9 — Report (minimal, <5KB chat output)
Output ONLY the following to keep chat output under 5KB (DynamoDB compliance):

```markdown
## Processing Summary
- Sessions processed: [count]
- Rubric rows processed: [count]
- Rows classified: [count]

## Classification Breakdown
| Category | Count |
|---|---|
| Process Change (PC) | X |
| Adoption/Config (AC) | X |
| Feature Backlog (FB) | X |
| Not Applicable (NA) | X |
| HITL (flagged for review) | X |

## Assessment Workbooks
- Assessment_Run1_<CapGroup>.xlsx: [count] rows
- Assessment_Run2_<CapGroup>.xlsx: [count] rows
- [...]
```

**Do NOT output:**
- Individual answer text or source citations (all in workbook column H)
- Mapping details or per-session breakdowns
- Unresolved question lists or explanations
- Search queries, batch processing logs, or progress updates
- Explanations or observations

(All detailed data stays in the xlsx files. Chat is metadata only.)

---

## Hard Fast-Fail Rules

- **Never call any script at startup, on context load, or before the user provides data.**
- **Never attempt to pass 50+ rows as a single `execute_code` or `run_skill_script` payload.** Batch at ≤ 30 rows.
- **Use ONLY `scripts/build_assessment_batch.py` for production builds.** Never use `build_assessment_snapshot_v2.py` or `build_assessment_snapshot.py`.
- **Never skip `getSpreadsheetInfo` before querying a spreadsheet.** Always verify column names first.
- **Chat output must be < 5KB.** Suppress all intermediate data, script logging, and explanations. Detailed answers and sources stay in xlsx files only. This ensures DynamoDB item size limit compliance (400KB max).
- **If a script outputs progress/logging:** Suppress all `print()` statements that log progress, batch details, or explanations. Only output final file paths and row counts.
- If mapping rows are empty or missing → report and stop.
- If transcript is empty → report "No transcript provided" and stop.
- If `execute_code` times out → reduce batch size and retry.

---

## Troubleshooting

### Mapping Query Failures
- **"Column 'session' not found"** → Call `getSpreadsheetInfo` first to confirm exact column names. The mapping file may use different column names than expected.
- **Empty result set** → Check session number; confirm data exists in mapping file. Verify the session number is numeric and within the range of the file.
- **Timeout on query** → Add `LIMIT 100` to prevent retrieving the full dataset unnecessarily.

### Transcript Retrieval Failures
- **"No transcript found"** → Confirm filename and location with user; check data product folders. Transcript may be named differently than expected.
- **Chunked/partial results** → Expected behavior. Make 2–4 targeted calls per topic cluster, not one call for the full file. The retrieval system returns paginated results.
- **"Retrieval system error"** → Retry with reduced scope (e.g. single capability group instead of all topics at once).

### Script Execution Failures
- **Payload overflow / timeout** → Reduce batch size from 30 to 20 rows; retry. Check that input.json is well-formed JSON before passing to script.
- **"Column index out of range"** → Check that all required columns exist in input rows. Ensure the row structure matches what the script expects.
- **Output file not created** → Verify `openpyxl` is available; check Python version compatibility (Python 3.8+).

### Classification Issues
- **"All rows classified as HITL"** → Likely the transcript is silent on these topics; this is valid. Report this as expected behavior, not an error.
- **"TownSq Capability missing"** → Use `NA` (Not Applicable); never infer a classification from Branch Answer alone. An empty capability means the question is not applicable.
- **Confidence too low** → Flag as HITL; do not guess a classification.

### Output Size Issues
- **Chat output > 5KB** → Suppress intermediate data; move to workbook. Remove progress updates, explanations, and detailed results from chat response.
- **Script produces large output file** → Split batch further (≤ 20 rows); retry. Multiple smaller files are better than one large file.

### Script Logging Suppression
Your bundled scripts (`resolve_session_scope_v2.py`, `build_assessment_batch.py`) should output ONLY final results (file paths, counts). If scripts output progress updates, batch logs, or explanations, these MUST be removed:
- Search for `print(` statements in scripts
- Remove any that output progress ("Good — X rows resolved...")
- Remove any that enumerate questions or batches ("Q0089: ...")
- Remove any that explain observations ("Important note: this session has no VTT...")
- Keep ONLY: final file path output and return statements with counts

---

## Tool and Data Rules
- **Never open/render documents directly** — all reading happens through `executeQuery`/`getSpreadsheetInfo` or plain-text reads of transcripts.
- **One session's rows, one session's transcript** — never mix sources across sessions.
- **No write-back, ever** — the Master Rubric data product file and any chat-uploaded files are never modified. The only output is the new standalone workbook(s).
- **Row count integrity is mandatory**: the delivered xlsx row count must equal the mapping row count. If it doesn't, stop and report the discrepancy — do not deliver a file that silently dropped rows.
- Cite the transcript filename (and speaker/timestamp locator when available) as the source for every new answer.
