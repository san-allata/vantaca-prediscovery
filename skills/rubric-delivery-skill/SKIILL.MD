---
name: rubric-delivery-skill
description: Use this skill to build and deliver Assessment xlsx workbooks from classified rubric rows. Accepts a classified_rows JSON payload (merged answered_rows + classified_rows, keyed by UID), runs the pre-build metadata validation gate, batches rows (≤ 20), calls execute_code with the xlsx builder, and delivers each batch as a download via render_content. Use this skill after session-rubric-answerer (answering) and branch-assessor-skills (classification) have both completed their passes.
---

# Rubric Delivery Skill

## Purpose

Build and deliver Assessment xlsx workbooks from a fully classified row payload. This skill owns **only** the merge, validation, build, and delivery steps. It does not answer questions, classify rows, or fetch transcript evidence.

## Input

A merged JSON payload — `answered_rows` (from `session-rubric-answerer`) joined with classification output (from `branch-assessor-skills`) — keyed by UID. Every row must carry all 13 output fields before this skill runs.

## Workflow

### Step 1 — Receive and validate the merged payload

Accept the merged rows. Verify the merge was done by UID key (never by position):

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

If any check fails: correct from source or set `classification: ""` + `hitl: true` with `[HITL: metadata validation failed — field missing or invalid]`. Never build with invalid metadata.

### Step 3 — Batch rows by capability group (≤ 20 rows per batch)

Group rows by `capability` name. If a single capability group exceeds 20 rows, split by `dimension` alphabetically. Assign `run` numbers sequentially (1, 2, 3 …).

### Step 4 — Load xlsx builder

```
read_skill_resource(skillId, "references/xlsx_builder.py")
```

Store the returned content verbatim. **Do not rewrite or paraphrase it.**

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
- Non-empty → use `outputFiles[0].blobKey` as `content` in `render_content`
- Empty → **STOP**. Do not attempt a base64 fallback. Report and retry.

### Step 6 — Deliver each batch immediately

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

### Step 7 — Report

```markdown
## Delivery Summary
- Branch: {branch} / Session: {N} / Total rows: {count} / Batches: {M}

## Classification Breakdown
| Code | Count |
|---|---|
| AC | X | PC | X | FB | X | NA | X | HITL (blank) | X |

## Files Delivered
- Assessment_{Branch}_Session{N}_Run1.xlsx — {count} rows
```

---

## Output Column Schema (13 columns, fixed order)

| # | Column | Field key |
|---|---|---|
| 1 | UID | `uid` |
| 2 | QID | `qid` |
| 3 | Session | `session` |
| 4 | Planned Question ID | `planned_question_id` |
| 5 | Capability | `capability` |
| 6 | Dimension | `dimension` |
| 7 | Priority | `priority` |
| 8 | Discovery Question | `discovery_question` |
| 9 | Branch Answer | `branch_answer` |
| 10 | TownSq Capability | `townsq_capability` |
| 11 | Classification | `classification` |
| 12 | Assessor Notes | `assessor_notes` |
| 13 | Proximity | `proximity` |

**Never add columns beyond 13.**

---

## Row Dict Schema

```json
{
  "uid": "Q0285",
  "qid": "6.8.1",
  "session": 6,
  "planned_question_id": "S6-Q12",
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
**`hitl`**: `true` for blank-classification rows — builder applies amber fill, cell stays blank.

---

## Hard Rules

- **Always use execute_code + outputFiles[0].blobKey** — never run_skill_script for xlsx delivery.
- **Always read references/xlsx_builder.py before building** — embed verbatim, never rewrite.
- **Never add columns** — 13-column schema is fixed.
- **Merge by UID key only** — never by row index or position.
- **Deliver immediately after each batch** — do not queue.
- **If outputFiles is empty** — STOP. Report and retry.
- **classification must be "PC", "AC", "FB", "NA", or ""** — never "HITL".
- **Chat output must stay < 5KB.**