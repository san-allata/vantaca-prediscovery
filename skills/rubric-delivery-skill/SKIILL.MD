---
name: rubric-delivery-skill
description: Use this skill to build and deliver Assessment xlsx workbooks from classified rubric rows. Accepts a classified_rows JSON payload (merged answered_rows + classified_rows, keyed by UID), runs the pre-build metadata validation gate, batches rows (≤ 20), calls execute_code with the xlsx builder, and delivers each batch as a download via render_content. Use this skill after session-rubric-answerer (answering) and branch-assessor-skills (classification) have both completed their passes.
---

# Rubric Delivery Skill

## Purpose

Build and deliver Assessment xlsx workbooks from a fully classified row payload. This skill owns **only** the merge, validation, build, and delivery steps. It does not answer questions, classify rows, or fetch transcript evidence.

## Input

A merged JSON payload — `answered_rows` (from `session-rubric-answerer`) joined with classification output (from `branch-assessor-skills`) — keyed by UID. Every row must carry all 15 output fields before this skill runs.

## Workflow

### Step 1 — Receive and validate the merged payload

Accept the merged rows. For each row, verify the merge was done by UID key (never by position):

```python
assert row['uid'] == classified_row['uid'], f"UID mismatch: {row['uid']} vs {classified_row['uid']}"
```

Any unmatched UID → set `classification: ""`, `hitl: true`, write `[HITL: UID mismatch on merge — verify row binding]` in `assessor_notes`.

### Step 2 — Run the pre-build metadata validation gate

Before every batch, confirm per-row:
- `uid` — present and non-empty
- `dimension` — present and non-empty
- `discovery_question` — present and non-empty
- `townsq_capability` — present and non-empty
- `branch_answer` — present and non-empty (or `hitl: true` if Not Found)
- `classification` — one of `"PC"`, `"AC"`, `"FB"`, `"NA"`, `""` — never `"HITL"`

If any check fails: correct from source or set `classification: ""` + `hitl: true` with `[HITL: metadata validation failed — field missing or invalid]` in `assessor_notes`. Never build with invalid metadata.

### Step 3 — Batch rows by capability group (≤ 20 rows per batch)

Group rows by `capability` name. If a single capability group exceeds 20 rows, split by `dimension` alphabetically.

Assign `run` numbers sequentially (1, 2, 3 …).

### Step 4 — Load xlsx builder

```
read_skill_resource(skillId, "references/xlsx_builder.py")
```

Store the returned content string verbatim. **Do not rewrite or paraphrase it.** Embed it exactly as-is in every `execute_code` call.

### Step 5 — Build each batch via execute_code

```python
# execute_code — code parameter:
<full content of references/xlsx_builder.py>

with open("input.json") as f:
    build(json.load(f))

# execute_code — input parameter:
{
  "branch": "<branch name>",
  "session": <session number>,
  "run": <run number>,
  "rows": [ ...up to 20 row dicts... ]
}
```

After `execute_code` returns, check `outputFiles`:
- If `outputFiles` is non-empty → use `outputFiles[0].blobKey` as `content` in `render_content`
- If `outputFiles` is empty → **STOP**. Do not attempt a base64 fallback. Report the failure and retry.

### Step 6 — Deliver each batch immediately

Deliver via `render_content` immediately after each successful `execute_code` call. Do not queue batches.

```
render_content(
  displayType: "download",
  title: "Assessment_{Branch}_Session{N}_Run{M}.xlsx",
  content: <outputFiles[0].blobKey>,
  metadata: {
    filename: "Assessment_{Branch}_Session{N}_Run{M}.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  }
)
```

File naming: `Assessment_{Branch}_Session{N}_Run{M}.xlsx`
Examples: `Assessment_CMA_Session6_Run1.xlsx`, `Assessment_CMA_Session6_Run2.xlsx`

### Step 7 — Report

After all batches are delivered, output a minimal summary (< 5KB):

```markdown
## Delivery Summary
- Branch: {branch}
- Session: {N}
- Total rows delivered: {count}
- Batches: {M}

## Classification Breakdown
| Code | Count |
|---|---|
| AC | X |
| PC | X |
| FB | X |
| NA | X |
| HITL (blank) | X |

## Files Delivered
- Assessment_{Branch}_Session{N}_Run1.xlsx — {count} rows
- Assessment_{Branch}_Session{N}_Run2.xlsx — {count} rows
```

Do NOT output individual row data, answers, or classification details in chat.

---

## Output Column Schema (15 columns, fixed order)

The xlsx builder writes exactly these 15 columns. Do not add, remove, or reorder columns.

| # | Column | Field key | Source |
|---|---|---|---|
| 1 | UID | `uid` | Read-only — CSV verbatim |
| 2 | QID | `qid` | Read-only — CSV verbatim |
| 3 | Session | `session` | Read-only — CSV verbatim |
| 4 | Planned Question ID | `planned_question_id` | Read-only — CSV verbatim |
| 5 | Domain | `domain` | Matched from rubric_index |
| 6 | Cap # | `cap_num` | Matched from rubric_index |
| 7 | Capability | `capability` | Read-only — CSV verbatim |
| 8 | Dimension | `dimension` | Read-only — CSV verbatim |
| 9 | Priority | `priority` | Read-only — CSV verbatim |
| 10 | Discovery Question | `discovery_question` | Read-only — CSV verbatim |
| 11 | Branch Answer | `branch_answer` | AI-written by session-rubric-answerer |
| 12 | TownSq Capability | `townsq_capability` | Read-only — CSV verbatim |
| 13 | Classification | `classification` | AI-written by branch-assessor-skills |
| 14 | Assessor Notes | `assessor_notes` | AI-written by branch-assessor-skills |
| 15 | Proximity | `proximity` | AI-written by branch-assessor-skills |

**Never add columns beyond 15.** The builder's column list is fixed.

---

## Row Dict Schema (passed in `rows` array)

```json
{
  "uid": "Q0285",
  "qid": "6.8.1",
  "session": 6,
  "planned_question_id": "S6-Q12",
  "domain": "Financial Operations",
  "cap_num": "6.8",
  "capability": "Supply Charges",
  "dimension": "Ancillary billing visibility",
  "priority": "P1",
  "discovery_question": "How do you view ancillary billings...",
  "branch_answer": "We maintain a fee schedule...\n\nSource: ...",
  "townsq_capability": "Ancillary charges are managed as Reimbursable Items...",
  "classification": "AC",
  "assessor_notes": "BRANCH: ...\nTOWNSQ: ...\nDELTA: ...\nWHY AC: ...\nConfidence: High",
  "proximity": "High (~75%)",
  "hitl": false
}
```

**`classification`**: `"PC"` / `"AC"` / `"FB"` / `"NA"` / `""`. **Never `"HITL"`.**
**`proximity`**: `"Exact match"` / `"High (~75%)"` / `"Moderate (~50%)"` / `"Low (~25%)"` / `"No match"` / `""` (blank for HITL rows).
**`hitl`**: `true` for blank-classification rows. Builder applies amber fill; cell value stays blank.

---

## Hard Rules

- **Never call run_skill_script for xlsx delivery** — outputFiles will always be empty from the skill sandbox.
- **Always use execute_code + outputFiles[0].blobKey** for xlsx delivery.
- **Always read references/xlsx_builder.py before building** — embed verbatim, do not rewrite.
- **Never add columns to output** — the 15-column schema is fixed.
- **Merge by UID key only** — never by row index or position.
- **Deliver immediately after each batch** — do not queue.
- **If outputFiles is empty after execute_code** — STOP. Report and retry. Never fall back to base64 from stdout.
- **classification must be "PC", "AC", "FB", "NA", or ""** — never "HITL".
- **Chat output must stay < 5KB** — all row data goes in xlsx files.