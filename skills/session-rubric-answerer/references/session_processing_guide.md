# Session Processing Guide
**Canonical operational guide for session-rubric-answerer**
Last updated: 2026-09-10 — codified from live Session 6 / CMA run

---

## 1. Overview

This guide documents the proven end-to-end pattern for processing any discovery session transcript against the Master Rubric. It was written after a live Session 6 run that encountered and resolved three distinct failure modes. Follow it exactly before improvising.

**Output:** One xlsx workbook per capability-group batch, each containing answered and classified rubric rows for the requested session. Multiple batch files are delivered as separate downloads and merged by the user (or a follow-up merge step).

---

## 2. Pre-flight Checklist

Before running anything, confirm:

- [ ] User has provided a session number (or range)
- [ ] Session Mapping CSV is accessible (chat upload or attached data product)
- [ ] Transcript file is accessible (chat upload or attached data product)
- [ ] `getSpreadsheetInfo` called on the mapping CSV to verify column names
- [ ] Rubric index loaded via `read_skill_resource`

Do NOT proceed if any item is unchecked.

---

## 3. Step-by-Step Workflow

### Step 1 — Query Session Mapping CSV

Always call `getSpreadsheetInfo` first to verify column names. Then query:

```sql
SELECT session, planned_question_id, uid, qid, capability, dimension, priority,
       exact_master_rubric_question
FROM data
WHERE session = <N>
LIMIT 100
```

**Known column names (Sessions_6_Master_Rubric_Mapping.csv as of 2026-09-10):**

| SQL name | Original name |
|---|---|
| `session` | Session |
| `planned_question_id` | Planned Question ID |
| `uid` | UID |
| `qid` | QID |
| `capability` | Capability |
| `dimension` | Dimension |
| `priority` | Priority |
| `exact_master_rubric_question` | Exact Master Rubric Question |

If column names differ (different session file), re-run `getSpreadsheetInfo` and adjust.

**Expected row count per session:** 80–110 rows typical. If result is 0, check the session number filter value — the column may store session as a number not a string.

### Step 2 — Load Rubric Index

```
read_skill_resource(skillId, "references/rubric_index.json")
```

Parse the returned JSON array. Pass as `rubric_index` in the resolve script input.

### Step 3 — Resolve Session Scope

Call `resolve_session_scope_v2.py`:

```json
{
  "mapping_rows": [ ...rows from Step 1... ],
  "rubric_index": [ ...parsed array from Step 2... ]
}
```

Expected output: `{ "resolved": [...], "unresolved": [...] }`. Report any unresolved rows before proceeding.

### Step 4 — Fetch Transcript Evidence (Batched by Topic)

**Do NOT attempt to load the full VTT transcript in one call.** The data product retrieval system returns chunked semantic search results. A single broad query returns ~40 chunks but misses topic-specific detail.

**Proven pattern: 3–4 targeted `get_information_from_dataProduct` calls, each covering one topic cluster.**

Example split for a Financial Operations session:
1. "management fee configuration, contract storage, fee types, rate changes, dual-sided accounting"
2. "board approval, self-billing controls, separation of duties, revenue recognition"
3. "supply charges, reimbursables, utility invoices, amenity rentals, security deposits"
4. "audit, CPA, tax filings, engagement letters, IRS, extensions"

Adjust topic clusters to match the session's capability areas. Hold all retrieved evidence in context — do NOT re-query per row.

### Step 5 — Split Rows into Capability-Group Batches

**Rule: ≤ 30 rows per batch.**

Group rows by capability name (not cap number — cap numbers can be stored inconsistently). Typical splits:

| Batch | Capabilities | Approx rows |
|---|---|---|
| Run 1 | Management Fee Administration (6.15) | 35–51 |
| Run 2 | Supply Charges (6.8) + Reimbursables/Fee Mgmt (6.9) + Systems (6.12.9) | 25–35 |
| Run 3 | Amenity Rentals & Security Deposits (6.12) + Audit/Tax/CPA (6.10) | 20–30 |

Adjust splits based on actual row counts returned. If a single capability group > 30 rows, split it alphabetically by dimension.

### Step 6 — Extract Branch Answers

For each row:
1. Search retrieved transcript evidence for the question topic
2. Write `branch_answer` in the format: `"{answer}\n\nSource: {file} [{timestamp}, {speaker}]"`
3. If partial: append `"\n\nGAPS: {what is missing}"`
4. If not found: `"Not Found — {brief reason}\n\nSource: {file} (full transcript reviewed; topic not addressed)\n\nGAPS: {topic} not discussed in this session"`
5. Mark `hitl: True` for all Not Found or Low confidence rows

### Step 7 — Classify Each Row

Apply the branch-assessor decision ladder in order:
1. Either side unreadable / Not Found? → HITL (flag amber, no code)
2. Branch explicitly doesn't do this? → NA
3. TownSq cannot produce the outcome today? → FB
4. Capability in flight / not yet live? → FB
5. Only system setup needed; branch steps survive? → AC
6. Branch steps/roles/approvals must change? → PC
7. Still torn? → HITL

**FB-bias-under-uncertainty:** When transcript is silent AND TownSq capability statement is "Not supported" or "Partial", default to FB. A false FB is caught in backlog grooming. A false AC/PC hides a build need.

### Step 8 — Build Assessment xlsx (BATCHED via execute_code)

**This is where previous single-payload attempts failed. The fix is mandatory.**

#### Why batching is required

| Attempt | Failure mode |
|---|---|
| `run_skill_script` with full 100-row inputData | Payload too large — response cut off |
| `execute_code` with inline Python string literals for 100 rows | Script body too large — sandbox timeout |
| `execute_code` with `input` JSON param for 100 rows | JSON input too large to marshal inline |
| `execute_code` with ≤ 30 rows as `input` JSON | ✅ **Works reliably** |

#### Canonical build pattern (per batch)

```python
# In execute_code, pass rows as the `input` parameter (≤ 30 rows)
# The sandbox writes input to input.json automatically
# Script reads input.json and writes xlsx

import json, openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

# Load rows from input.json (passed via execute_code `input` parameter)
with open('input.json') as f:
    data = json.load(f)
rows = data['rows']
batch_name = data.get('batch_name', 'Batch')

# ... (see build_assessment_batch.py for full implementation)
```

#### Column schema (14 columns, fixed order)

| # | Column |
|---|---|
| 1 | UID |
| 2 | QID |
| 3 | Session |
| 4 | Planned Question ID |
| 5 | Domain |
| 6 | Cap # |
| 7 | Capability |
| 8 | Dimension |
| 9 | Priority |
| 10 | Discovery Question |
| 11 | Branch Answer |
| 12 | TownSq Capability |
| 13 | Classification |
| 14 | Assessor Notes |

#### Classification color map

| Code | Fill color | Font |
|---|---|---|
| AC | #70AD47 (green) | White bold |
| FB | #FF0000 (red) | White bold |
| PC | #4472C4 (blue) | White bold |
| NA | #FFD966 (yellow) | Black bold |
| HITL | #FFC000 (amber) | Black bold |

#### Formatting constants

- Header fill: #1F4E79 (dark blue), white bold font, size 11
- Freeze panes: A2
- Wrap text: all cells
- Vertical align: top (data rows)
- Row height: 80pt (data rows), 30pt (header)
- Column widths: [10, 10, 8, 14, 18, 8, 22, 28, 9, 45, 55, 45, 14, 60]
- Sheet name: `Assessment`

#### Output file naming

```
Assessment_Run<N>_<CapabilityGroup>.xlsx
```
Examples: `Assessment_Run1_MgmtFee.xlsx`, `Assessment_Run2_Supply_Reimbursables.xlsx`, `Assessment_Run3_Amenity_Audit.xlsx`

### Step 9 — Deliver and Report

For each batch:
1. Deliver xlsx via `render_content` (displayType: download)
2. Report: rows written, classification breakdown (AC/FB/PC/NA counts), HITL count, any unresolved

Final summary across all batches:
- Total rows: N
- AC: N | FB: N | PC: N | NA: N | HITL: N
- Unresolved mappings: list UIDs

---

## 4. Row Data Structure

Each row passed to the xlsx builder must include these fields:

```json
{
  "uid": "Q0468",
  "qid": "6.15.1",
  "session": 6,
  "planned_question_id": "S6-Q3",
  "domain": "Financial Operations",
  "cap_num": "6.15",
  "capability": "Management Fee Administration",
  "dimension": "Fee schedule configuration per association",
  "priority": "P0",
  "discovery_question": "How is the monthly management fee configured...",
  "branch_answer": "All billing is handled in Vantaca...\n\nSource: CMA _ Financial Operations Discovery - Session 6.vtt [00:05:01, Kim Dunbar]",
  "townsq_capability": "After config — Management fee billing contracts configured in TownSq...",
  "classification": "AC",
  "assessor_notes": "BRANCH: ... TOWNSQ: ... DELTA: ... WHY AC: ... Proximity: ... Confidence: ...",
  "hitl": false
}
```

The `hitl` field is optional (defaults to false). Set to `true` for Not Found or Low confidence rows — the builder will use amber fill on the Classification cell.

---

## 5. Known Failure Modes & Fixes

| Failure | Cause | Fix |
|---|---|---|
| Response cut off mid-run | Payload too large for single tool call | Batch at ≤ 30 rows per execute_code call |
| `execute_code` timeout | Inline Python string literals for 100 rows too large | Pass rows as `input` JSON parameter, not inline strings |
| `run_skill_script` payload overflow | 100-row JSON too large for inputData | Use execute_code + build_assessment_batch.py instead |
| `getSpreadsheetInfo` column not found | Column names vary by file | Always call getSpreadsheetInfo before querying; use exact column names returned |
| Transcript evidence missing for a topic | Single broad VTT query misses detail | Use 3–4 targeted topic-cluster queries |
| 0 rows returned from mapping CSV query | Session column stored as number, queried as string (or vice versa) | Check sample values in getSpreadsheetInfo output; adjust filter value type |
| build_assessment_snapshot_v2.py hangs | Designed for small payloads only | Use build_assessment_batch.py via execute_code for production |

---

## 6. Transcript Evidence Quality Rules

- **Cite speaker and timestamp for every answer** (e.g., `[00:05:01–00:05:14, Kim Dunbar]`)
- **Do not use TownSq capability column as branch evidence** — column H must reflect branch's current process
- **Synthesize only explicit statements** — no inference beyond what is said
- **Speculation is evidence of the statement, not the fact:** `"Per Kim Dunbar: 'I think we do X'"` ≠ `"Branch does X"`
- **Not Found is valid** — use it when transcript is genuinely silent; do not guess
- **GAPS line required** when some sub-parts of a multi-part question are unanswered

---

## 7. Classification Quick Reference

| Code | When |
|---|---|
| AC | TownSq supports it after config; branch steps/roles survive |
| PC | TownSq supports it; branch steps/roles/approvals must change |
| FB | TownSq cannot produce the required outcome today |
| NA | Branch positively does not do this / does not apply |
| HITL | Branch answer Not Found or Low confidence — escalate for human review |

**Dominant-blocker rule:** When a row needs both AC and PC, assign PC (the change that blocks go-live) and note `Also requires: <config>` in assessor notes.

**FB-bias-under-uncertainty:** When transcript is silent AND TownSq capability is "Not supported" or "Partial", default FB. A false FB is fixed in backlog grooming; a false AC/PC hides a build need until UAT.

**NA requires positive evidence:** If H simply does not mention the topic, that is Not Found / HITL, not NA. Require a positive statement that the branch does not do this.

---

## 8. Assessor Note Format

Every classified row must have assessor notes in this format:

```
BRANCH: <clause from branch answer that drives the code>
TOWNSQ: <clause from TownSq capability that drives the code>
DELTA: <which facets differ — outcome / mechanism / actors / timing / controls / exceptions / evidence>
WHY <CODE>: <one sentence>
[Also requires: <secondary config or process change, if any>]
Proximity: <Exact match | High (~75%) | Moderate (~50%) | Low (~25%) | No match>
Confidence: <High | Medium | Low> (<what is solid; what is not>)
```

---

## 9. Session 6 / CMA Reference Run (2026-09-10)

The first full live run of this skill was Session 6 for CMA. Key stats:

| Batch | Capabilities | Rows | AC | FB | PC | NA | HITL |
|---|---|---|---|---|---|---|---|
| Run 1 | Management Fee Admin (6.15) | 39 | 14 | 18 | 3 | 4 | 7 |
| Run 2 | Systems (6.12.9) + Supply (6.8) + Reimbursables (6.9) | 32 | 18 | 8 | 3 | 3 | 14 |
| Run 3 | Amenity Rentals (6.12) + Audit/Tax/CPA (6.10) | 29 | TBD | TBD | TBD | TBD | TBD |

Total Session 6 mapped rows: 100. Transcript: `CMA _ Financial Operations Discovery - Session 6.vtt`.
Data product: `Vantaca - CMA - Session 6`.
Mapping CSV: `Sessions_6_Master_Rubric_Mapping.csv`.

Known pain points captured in Run 2:
- Payment misapplication (assessment vs. reservation) — Will Stanley, 00:55:43
- Role-based JE restriction gap — Melanie Adams, 01:18:44
