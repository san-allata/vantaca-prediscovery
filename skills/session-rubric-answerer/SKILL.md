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
- `scripts/resolve_session_scope_v2.py` — Resolves session mapping rows to rubric rows. Input: `{ "mapping_rows": [...], "rubric_index": [...] }`. Output: resolved rows or list of unresolved questions.
- `scripts/build_assessment_batch.py` — **Canonical production xlsx builder.** Handles ≤30-row batches, formats colors/freeze/wrap/column widths. Use via `execute_code` (Python), passing rows as `input` JSON parameter. Reads from `input.json`, writes `Assessment_<batch_name>.xlsx`. **This is the ONLY script to use for new production builds.**
- `scripts/build_assessment_snapshot_v2.py` — **DEPRECATED.** Do not use for production.
- `scripts/build_assessment_snapshot.py` — **DEPRECATED.** Do not use. Use `build_assessment_batch.py` instead.
- `assets/MasterRubricTemplateWithAssociaAnswers_FB.xlsx` — Master Rubric asset (read-only reference).

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
Call `resolve_session_scope_v2.py`. Confirm 100% resolved before proceeding.

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

### Step 8 — Build Assessment xlsx (BATCHED)

**Classification field contract — enforced by the script:**

```json
// Classified row:
{ "classification": "AC", "hitl": false, "proximity": "High (~75%)", ... }

// HITL row — transcript silent or unresolvable:
{ "classification": "", "hitl": true, "proximity": "", ... }
```

**`"classification": "HITL"` is INVALID and will be stripped to `""` by the script with amber fill.**

For each batch (≤ 30 rows), call `execute_code` passing rows as the `input` JSON parameter. Use `scripts/build_assessment_batch.py` ONLY.

**Never pass all rows in one call** — batch at ≤ 30 rows. Reduce to 20 if timeout occurs.

### Step 9 — Deliver files and Report

**Every generated xlsx MUST be delivered as a clickable download link.** Call `render_content` (displayType: `"download"`) for each batch file immediately after `execute_code` confirms it was written. Check `outputFiles` is non-empty before calling `render_content`.

```
render_content(
  displayType: "download",
  title: "Assessment_Run<N>_<CapGroup>.xlsx",
  content: <base64-encoded file bytes>,
  metadata: {
    filename: "Assessment_Run<N>_<CapGroup>.xlsx",
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
- Assessment_Run1_<CapGroup>.xlsx — [count] rows ↓ (download link above)
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
- **Never pass 50+ rows in a single `execute_code` call.** Batch at ≤ 30 rows.
- **Use ONLY `scripts/build_assessment_batch.py` for production builds.**
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
- **No download link** → `render_content` was not called. Call it immediately after `execute_code`.
- **`outputFiles` empty** → File not written. Check script path; retry.

### Script Execution Failures
- **Payload overflow / timeout** → Reduce batch to 20 rows; retry.
- **`outputFiles` empty after `execute_code`** → Do NOT claim a download link. Report and retry.

---

## Tool and Data Rules
- **Never mix sessions** — one session's rows, one session's transcript only.
- **No write-back ever** — source files are never modified.
- **Row count integrity** — delivered xlsx row count must equal mapping row count.
- **Always tag system of record** in every Source line and TOWNSQ note line.