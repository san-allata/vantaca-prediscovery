---
name: session-rubric-answerer
description: "Process discovery session transcripts against the Associa Branch Readiness Master Rubric: extract answers to rubric questions, classify branch-to-TownSq capability backlogs (PC/AC/FB/NA), and deliver Assessment xlsx workbooks with full citations. Use this skill whenever the user asks to process a session, answer rubric questions, classify readiness gaps, or refresh an Assessment snapshot—even if they don't explicitly mention 'rubric' or 'classification'. Trigger phrases: 'Process session N', 'answer this session's questions', 'classify branch answers', 'give me an updated assessment', 'refresh the assessment'."
---

## Session Rubric Answerer — Full Instructions

You process branch discovery session transcripts against the Associa Branch Readiness Master Rubric. Your output is one or more downloadable Assessment xlsx workbooks (one per capability-group batch) containing branch answers, TownSq capability notes, classifications (PC / AC / FB / NA), assessor notes, and proximity.

**Before doing anything, read `references/session_processing_guide.md`.** It is the canonical operational guide for this skill and contains the complete step-by-step workflow, batching strategy, transcript fetch strategy, and all verified patterns from live runs. This SKILL.md is a summary — the guide is the source of truth.

**Also load `references/greg_approved_classifications.md` at the start of every run.** This file contains Greg Hamm's confirmed classification rulings from SME review sessions. These override general heuristics for the topics they cover.

---

## Reference Files & Resources

- `references/session_processing_guide.md` — **Read this first.** End-to-end workflow, batching strategy, transcript fetch approach, verified SQL patterns, known failure modes and fixes.
- `references/greg_approved_classifications.md` — **Load at Step 2b.** Greg-confirmed classifications and domain rules (GR-1 through GR-7). Highest priority — overrides general decision ladder for covered topics.
- `references/rubric_index.json` — Lightweight rubric index (representative rows). Use for scope resolution. Pass as `rubric_index` in inputData when calling v2 scripts.
- `scripts/resolve_session_scope_v2.py` — Resolves session mapping rows to rubric rows. Input: `{ "mapping_rows": [...], "rubric_index": [...] }`. Output: resolved rows or list of unresolved questions. **Use via `run_skill_script` only.**
- `scripts/build_assessment_batch.py` — **Canonical production xlsx builder.**

  > ⛔ **TOOL: `execute_code` — NEVER `run_skill_script`.**
  > This script must be called via `execute_code` because only `execute_code` captures output files in `outputFiles` for delivery. `run_skill_script` writes to an isolated skill sandbox; those files are never accessible and cannot be delivered as downloads. Calling this script via `run_skill_script` will silently produce empty or broken download links every time.

- `scripts/build_assessment_snapshot_v2.py` — **DEPRECATED.** Do not use for production.
- `scripts/build_assessment_snapshot.py` — **DEPRECATED.** Do not use. Use `build_assessment_batch.py` instead.
- `assets/MasterRubricTemplateWithAssociaAnswers_FB.xlsx` — Master Rubric asset (read-only reference).

### Tool Usage — Which Script Uses Which Tool

| Script | Tool to use | Reason |
|---|---|---|
| `resolve_session_scope_v2.py` | `run_skill_script` | Reads/writes within skill sandbox only; no file delivery needed |
| `build_assessment_batch.py` | **`execute_code` ONLY** | Must write xlsx to code sandbox so `outputFiles` captures it for delivery |
| `build_assessment_batch.py` via `run_skill_script` | ⛔ **WRONG — do not use** | File lands in skill sandbox, never in `outputFiles`. Download link will be empty. |

**This distinction is critical.** `run_skill_script` and `execute_code` have completely isolated sandboxes. A file written by `run_skill_script` is never visible to `execute_code` and cannot be delivered as a download. **Any xlsx built via `run_skill_script` produces a link to nothing.**

### Integrated Skills
- **`branch-assessor-skill`**: Used in Step 7 to classify each answer per the decision ladder (PC/AC/FB/NA). Includes GR-1 through GR-7 Greg-Approved Domain Rules.
- **`rubric-answer-extractor-skill`**: Used in Step 6 to ground each answer in transcript evidence.

Do not call these skills directly; they are invoked internally during Steps 6–7.

---

## Critical Note on Reference Guide Maintenance

**`references/session_processing_guide.md` is the canonical operational guide.** This SKILL.md is a summary only. If anything here conflicts with the guide, the guide wins.

---

## Workflow Summary

**Read `references/session_processing_guide.md` for the full workflow.** The summary below is for quick orientation only.

### Step 1 — Wait for explicit user input
Do not proceed until the user provides ALL of:
- A session number (or range), AND
- Confirmation that the transcript and mapping CSV are in the attached data product(s)

Never call any script at startup or on context load.

### Step 2 — Query the Session Mapping CSV
Call `getSpreadsheetInfo` first to confirm column names. Then query:

```sql
SELECT session, planned_question_id, uid, qid, capability, dimension, priority,
       exact_master_rubric_question
FROM data
WHERE session = <N>
LIMIT 100
```

If the result set is empty, stop and report: "No mapping rows found for session N."

### Step 2b — Load Greg-Approved Classifications
Call `read_skill_resource` with `resourcePath: "references/greg_approved_classifications.md"` and hold in context.

### Step 3 — Load rubric index
Call `read_skill_resource` with `resourcePath: "references/rubric_index.json"` and parse as JSON.

### Step 4 — Resolve session scope
Call `resolve_session_scope_v2.py` via **`run_skill_script`**. Confirm 100% resolved before proceeding.

### Step 5 — Fetch transcript evidence (batched by topic)
Make **2–4 targeted** `get_information_from_dataProduct` calls, each covering a distinct topic cluster. Tag system of record (`[native Vantaca]`, `[StrongRoom]`, `[VendorSmart]`, `[Stripe]`, `[other]`) on every evidence piece. Scope all evidence to **HOA/community management** context (GR-2).

### Step 6 — Extract branch answers
For each row, ground the answer in transcript evidence. Cite speaker + timestamp + system tag in every Source line.

**HITL threshold:** When transcript is silent AND capability references an integration rather than native Vantaca — leave `classification` as `""` and set `hitl: true`. Write `[HITL: integration applicability unconfirmed — transcript silent]` in `assessor_notes`.

### Step 7 — Classify each row

Decision ladder (walk in order, stop at first match):
0. Greg-Approved Domain Rule applies? → Use it, record GR-N in notes
1. Either side unreadable / Not Found? → `classification: ""`, `hitl: true`, write `[HITL: <reason>]` in notes
2. Branch explicitly doesn't do this? → `"NA"`
3. Capability covered by StrongRoom, VendorSmart, or Stripe? → `"AC"`, record `[GR-1]`
4. TownSq native cannot produce the outcome today? → `"FB"`
5. Capability in flight / not yet live? → `"FB"`
6. Only system setup needed; branch steps survive? → `"AC"`
7. Branch steps/roles/approvals must change? → `"PC"`
8. Base = AC but automated exception surfacing also required? → `"AC"`, add `[GR-4: ...]` in notes
9. Still torn? → `classification: ""`, `hitl: true`, write `[HITL: <reason>]` in notes

**`classification` field MUST be one of: `"PC"`, `"AC"`, `"FB"`, `"NA"`, or `""` (empty string).**
**NEVER set `classification` to `"HITL"` or any other string.** The script will reject it.

For HITL rows: set `"classification": ""` AND `"hitl": true`. The script applies amber fill automatically. The cell value will be blank — no text is written into it.

### Step 8 — Build Assessment xlsx (BATCHED via execute_code — NOT run_skill_script)

> ⛔ **TOOL REQUIRED: `execute_code` — using `run_skill_script` here will silently break all file delivery.**
> Files written by `run_skill_script` are trapped in the skill sandbox and never appear in `outputFiles`.
> Every xlsx built via `run_skill_script` produces an empty or broken download link.
> This is the most common failure mode in this skill. Always use `execute_code` for this step.

> ⚠️ **`build_assessment_batch.py` MUST be called via `execute_code`, not `run_skill_script`.**
> Files written by `run_skill_script` live in the skill sandbox and cannot be captured in `outputFiles` or delivered as downloads. Any xlsx built via `run_skill_script` produces a link to nothing — the file binary is not accessible.

**The xlsx MUST be built inside `execute_code`.** The `execute_code` sandbox writes the file and captures it in `outputFiles`. The file is then delivered directly from `outputFiles` — no cross-sandbox read is needed or possible.

**If `build_assessment_batch.py` fails for any reason — STOP.** Do not write inline Python to replicate the script. Instead:
1. Report exactly what failed and why
2. Describe what change to `build_assessment_batch.py` is needed to fix it
3. Halt and wait for the user to update the script

**Classification field contract — enforced by the script:**

```json
// Classified row:
{ "classification": "AC", "hitl": false, "proximity": "High (~75%)", ... }

// HITL row — transcript silent or unresolvable:
{ "classification": "", "hitl": true, "proximity": "", ... }
```

**`"classification": "HITL"` is INVALID and will be stripped to `""` by the script with amber fill.**

Input JSON structure per batch:
```json
{
  "branch": "CMA",
  "session": 6,
  "run": 1,
  "rows": [ ... ]
}
```

For each batch (≤ 20 rows), call `execute_code` passing rows as the `input` JSON parameter. Use `scripts/build_assessment_batch.py` ONLY.

**Never pass all rows in one call** — batch at ≤ 20 rows. Reduce to 15 if timeout occurs.

### Step 9 — Deliver files and Report

**Every generated xlsx MUST be delivered as a clickable download link.** Call `render_content` (displayType: `"download"`) for each batch file immediately after `execute_code` confirms it was written. Check `outputFiles` is non-empty before calling `render_content`.

```
render_content(
  displayType: "download",
  title: "Assessment_{Branch}_Session{N}_Run{M}.xlsx",
  content: <base64-encoded file bytes from outputFiles>,
  metadata: {
    filename: "Assessment_{Branch}_Session{N}_Run{M}.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  }
)
```

After all files delivered, output minimal summary report (< 5KB):

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
| Pending HITL review (blank classification) | X |

## Assessment Workbooks
- Assessment_{Branch}_Session{N}_Run1.xlsx — [count] rows ↓ (download link above)
- Assessment_{Branch}_Session{N}_Run2.xlsx — [count] rows ↓ (download link above)
- [...]
```

---

## Workbook Column Schema (15 columns)

| # | Column | Notes |
|---|---|---|
| 1 | UID | |
| 2 | QID | |
| 3 | Session | |
| 4 | Planned Question ID | |
| 5 | Domain | |
| 6 | Cap # | |
| 7 | Capability | |
| 8 | Dimension | |
| 9 | Priority | |
| 10 | Discovery Question | |
| 11 | Branch Answer | |
| 12 | TownSq Capability | |
| 13 | Classification | `"PC"`, `"AC"`, `"FB"`, `"NA"`, or `""`. **Never `"HITL"`**. HITL rows: `""` + amber fill (applied by script). |
| 14 | Assessor Notes | Contains `[HITL: <reason>]` for blank rows, `[RECOMMENDATION: ...]`, `[GR-N: ...]` as applicable. |
| 15 | Proximity | `"Exact match"`, `"High (~75%)"`, `"Moderate (~50%)"`, `"Low (~25%)"`, `"No match"`, or `""`. Blank for HITL rows. |

---

## Hard Fast-Fail Rules

- **Never call any script at startup or before the user provides data.**
- **⛔ NEVER call `build_assessment_batch.py` via `run_skill_script`.** This is the single most common failure mode. `run_skill_script` writes to an isolated skill sandbox. The file is never captured. The download link will be empty. There is no recovery except rebuilding via `execute_code`. Always use `execute_code` for Step 8.
- **Never pass 50+ rows in a single `execute_code` call.** Batch at ≤ 20 rows.
- **Use ONLY `scripts/build_assessment_batch.py` for production builds.**
- **Never write inline Python to build xlsx files.** If the script fails, halt and report — do not replicate script logic inline.
- **Never skip `getSpreadsheetInfo` before querying a spreadsheet.**
- **Chat output must be < 5KB.** DynamoDB item size limit compliance (400KB max).
- **`classification` field must be `"PC"`, `"AC"`, `"FB"`, `"NA"`, or `""`. Never `"HITL"`.**
- **HITL rows: pass `"classification": ""` and `"hitl": true`.** The script handles amber fill. The cell value will be blank.
- **Always deliver every generated xlsx as a `render_content` download link.**
- **Never classify integration-covered items as FB without explicit SME confirmation.** (GR-1)
- **Never use "non-negotiable" in any assessor note.** (GR-6)
- If mapping rows are empty → report and stop.
- If transcript is empty → report and stop.
- If `execute_code` times out → reduce batch size and retry.

---

## Troubleshooting

### Classification Issues
- **"HITL appearing in Classification column"** → You set `"classification": "HITL"`. Change to `"classification": ""` + `"hitl": true`. The script will apply amber fill; the cell value stays blank.
- **"Too many FBs"** → Check GR-1 (StrongRoom/VendorSmart/Stripe = AC).
- **Business vs. community mismatch** → Check GR-2.
- **StrongRoom/Vantaca conflation** → Check GR-3.

### Delivery Failures
- **No download link / link points to nothing** → `build_assessment_batch.py` was called via `run_skill_script` instead of `execute_code`. The file landed in the skill sandbox and is not capturable. Rebuild the batch using `execute_code` with the same row data.
- **I already built some batches via `run_skill_script` — how do I recover?** → The row data is still in context. Rebuild each affected batch using `execute_code` with the same rows. You do not need to re-run Steps 1–7. Pass the same `branch`, `session`, `run`, and `rows` values to `execute_code` as the `input` parameter and run `build_assessment_batch.py`.
- **`outputFiles` empty after `execute_code`** → File not written to disk. Check script path; retry.
- **Chat stopped mid-run after `run_skill_script` builds** → Same root cause: `run_skill_script` was used for xlsx builds. Start a new chat, reprocess the remaining batches using `execute_code` only.

### Script Execution Failures
- **FileNotFoundError after run_skill_script** → You tried to read a skill-sandbox file from the code sandbox. Build xlsx inside `execute_code` only — never use `run_skill_script` for production builds.
- **Payload overflow / timeout** → Reduce batch to 15 rows; retry.
- **Script fails for any reason** → STOP. Report what failed and what fix is needed. Do not write inline Python.

---

## Tool and Data Rules
- **Never mix sessions** — one session's rows, one session's transcript only.
- **No write-back ever** — source files are never modified.
- **Row count integrity** — delivered xlsx row count must equal mapping row count.
- **Always tag system of record** in every Source line and TOWNSQ note line.
- **Data product names must match the naming convention in Section 2c of the processing guide exactly.** If the name provided by the user does not match, report the mismatch and ask for confirmation before proceeding.