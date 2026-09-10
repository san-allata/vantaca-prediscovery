---
name: session-rubric-answerer
description: Use this skill to run the complete end-to-end workflow that analyzes one or more sessions' meeting transcripts, answers each session's mapped Master Rubric questions using the Session Mapping file for context, classifies each answered row's Branch-to-TownSq capability gap, and builds a fresh, stamped Assessment snapshot. Use when a user wants to process discovery session transcripts against the readiness rubric, even if they don't explicitly mention 'rubric' or 'classification'.
---

# Session Rubric Answerer — Skill Instructions

You process branch discovery session transcripts against the Associa Branch Readiness Master Rubric. Your output is one or more downloadable Assessment xlsx workbooks (one per capability-group batch) containing branch answers, TownSq capability notes, classifications (PC / AC / FB / NA), and assessor notes.

**Before doing anything, read `references/session_processing_guide.md`.** It is the canonical operational guide for this skill and contains the complete step-by-step workflow, batching strategy, transcript fetch strategy, and all verified patterns from live runs. This SKILL.md is a summary — the guide is the source of truth.

---

## Reference Files

- `references/session_processing_guide.md` — **Read this first.** End-to-end workflow, batching strategy, transcript fetch approach, verified SQL patterns, known failure modes and fixes.
- `references/rubric_index.json` — Lightweight rubric index (representative rows). Use for scope resolution. Pass as `rubric_index` in inputData when calling v2 scripts.
- `scripts/resolve_session_scope_v2.py` — Resolves session mapping rows to rubric rows. Input: `{ "mapping_rows": [...], "rubric_index": [...] }`.
- `scripts/build_assessment_batch.py` — **Canonical xlsx builder.** Reads `input.json` containing `{ "rows": [...] }` and writes `Assessment_RunN_<CapGroup>.xlsx`. Use this via `execute_code` (pass rows as `input` JSON parameter). Do NOT use `build_assessment_snapshot_v2.py` for production builds — it cannot handle 50+ rows without payload overflow.
- `scripts/build_assessment_snapshot.py` — Original script. Do not modify.
- `scripts/build_assessment_snapshot_v2.py` — v2 test copy. Only use for small (<15 row) test payloads.
- `assets/MasterRubricTemplateWithAssociaAnswers_FB.xlsx` — Master Rubric asset (read-only reference).

---

## Workflow Summary

**Read `references/session_processing_guide.md` for the full workflow.** The summary below is for quick orientation only.

### Step 1 — Wait for explicit user input
Do not proceed until the user provides ALL of:
- A session number (or range), AND
- Confirmation that the transcript and mapping CSV are in the attached data product(s)

If only one is provided, ask for the other before doing anything.

### Step 2 — Query the Session Mapping CSV
Use `executeQuery` with the exact pattern from the guide. Do NOT use `SELECT *` with a WHERE clause that filters on a column name you haven't verified — always call `getSpreadsheetInfo` first to confirm column names.

```sql
SELECT session, planned_question_id, uid, qid, capability, dimension, priority,
       exact_master_rubric_question
FROM data
WHERE session = <N>
LIMIT 100
```

### Step 3 — Load rubric index
Call `read_skill_resource` with `resourcePath: "references/rubric_index.json"` and parse the result as JSON.

### Step 4 — Resolve session scope
Call `resolve_session_scope_v2.py` with mapping rows + rubric index. Confirm 100% of rows resolved before proceeding.

### Step 5 — Fetch transcript evidence (batched by topic)
Do NOT attempt to load the full VTT in one `get_information_from_dataProduct` call — the retrieval system returns chunked results. Instead make **2–4 targeted calls**, each covering a distinct topic cluster (e.g. "management fees + contract storage", "supply charges + reimbursables", "amenity rentals + deposits", "audit + tax + CPA"). Hold all retrieved evidence in context.

### Step 6 — Extract branch answers
For each resolved row, locate the branch's answer in the retrieved transcript evidence. Cite speaker and timestamp. Use `Not Found` with a source note when the transcript is silent on a topic.

### Step 7 — Classify each row
Apply the branch-assessor decision ladder (see `branch-assessor-skill`):
- **PC** — TownSq supports this; branch must change how they work
- **AC** — TownSq supports this after configuration/setup
- **FB** — TownSq cannot support this today
- **NA** — Not applicable to this branch
- **HITL** — Flag amber when answer is Not Found or confidence is Low

### Step 8 — Build Assessment xlsx (BATCHED)
**This is the critical step where previous attempts failed. Follow the batching rules exactly.**

See `references/session_processing_guide.md` → "Batched Build Strategy" for full detail. Summary:
- Split rows into capability-group batches of ≤ 30 rows each
- For each batch: call `execute_code` (Python) passing the rows as the `input` JSON parameter
- The script reads from `input.json` and writes the xlsx using `openpyxl`
- Use `scripts/build_assessment_batch.py` — it handles all formatting (colors, freeze, wrap, column widths)
- Deliver each batch file as a download via `render_content`
- Never pass all 100 rows in a single `execute_code` call — this causes payload overflow / timeout

### Step 9 — Report
Summarise per batch and overall: total rows answered, classification breakdown (PC/AC/FB/NA), HITL count, unresolved questions.

---

## Hard Fast-Fail Rules

- **Never call any script at startup, on context load, or before the user provides data.**
- **Never attempt to pass 50+ rows as a single execute_code or run_skill_script payload.** Batch at ≤ 30 rows.
- **Never call `build_assessment_snapshot_v2.py` for production builds.** Use `build_assessment_batch.py` via `execute_code`.
- **Never skip `getSpreadsheetInfo` before querying a spreadsheet.**
- If mapping rows are empty or missing → report and stop.
- If transcript is empty → report "No transcript provided" and stop.
- If `execute_code` times out → reduce batch size and retry.