# Session Processing Guide
**Canonical operational guide for session-rubric-answerer**
Last updated: 2026-09-25 — aligned with build_assessment_batch.py always-base64 output; corrected Step 8/9 to use run_skill_script stdout; fixed failure mode table; added Issue C (scope error halt) and Issue E (UEsD verification)

---

## 1. Overview

This guide documents the proven end-to-end pattern for processing any discovery session transcript against the Master Rubric. It was written after a live Session 6 run that encountered and resolved three distinct failure modes, then updated with classification corrections from four Greg Hamm SME review sessions. Follow it exactly before improvising.

**Output:** One xlsx workbook per capability-group batch (15 columns), named `Assessment_{Branch}_Session{N}_Run{M}.xlsx`. Every workbook must be delivered as a **clickable download link** in chat via `render_content`.

---

## 2. Pre-flight Checklist

Before running anything, confirm:

- [ ] User has provided a session number (or range)
- [ ] Session Mapping CSV is accessible (chat upload or attached data product)
- [ ] Transcript file is accessible (chat upload or attached data product)
- [ ] `getSpreadsheetInfo` called on the mapping CSV to verify column names
- [ ] Rubric index loaded via `read_skill_resource`
- [ ] `references/greg_approved_classifications.md` loaded via `read_skill_resource`
- [ ] Data product name(s) confirmed against naming convention (Section 2c)

Do NOT proceed if any item is unchecked.

---

## 2c. Data Product Naming Convention

All data products follow these naming patterns. Match exactly — do not guess or abbreviate.

| Type | Pattern | Example |
|---|---|---|
| Per-session transcript + mapping | `{Company} - {Branch} - Session {N}` | `Vantaca - CMA - Session 6` |
| Company-wide common data | `{Company} Data Product - Common` | `Vantaca Data Product - Common` |
| Company branch common data | `{Company} - {Branch} Common` | `Vantaca - CMA Common` |
| Master Rubric session data | `{Company} - Master Rubric - Session {N}` | `Vantaca - Master Rubric - Session 6` |

**If the data product name provided by the user does not match any pattern above, report the mismatch and ask for confirmation before proceeding. Do not query a data product whose name has not been confirmed.**

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

If column names differ, re-run `getSpreadsheetInfo` and adjust.

**Expected row count per session:** 80–110 rows typical. If result is 0, check the session number filter value.

### Step 2 — Load Rubric Index

```
read_skill_resource(skillId, "references/rubric_index.json")
```

Parse the returned JSON array. Pass as `rubric_index` in the resolve script input.

### Step 2b — Load Greg-Approved Classifications

```
read_skill_resource(skillId, "references/greg_approved_classifications.md")
```

Hold in context for the full run.

### Step 3 — Resolve Session Scope

Call `resolve_session_scope_v2.py` via `run_skill_script`:

```json
{
  "mapping_rows": [ ...rows from Step 1... ],
  "rubric_index": [ ...parsed array from Step 2... ]
}
```

Expected output: `{ "resolved": [...], "unresolved": [...] }`. Report any unresolved rows before proceeding.

**If the script errors for any reason, stop and report the exact error. Do not substitute manual scope resolution from mapping query context — the two are not equivalent.**

### Step 4 — Fetch Transcript Evidence (Batched by Topic)

**Do NOT load the full VTT in one call.** Use 3–4 targeted `get_information_from_dataProduct` calls per topic cluster.

Example split for a Financial Operations session:
1. "management fee configuration, contract storage, fee types, rate changes, dual-sided accounting"
2. "board approval, self-billing controls, separation of duties, revenue recognition"
3. "supply charges, reimbursables, utility invoices, amenity rentals, security deposits"
4. "audit, CPA, tax filings, engagement letters, IRS, extensions"

**Context scoping (GR-2):** Interpret all evidence through the lens of **HOA/community management**.

**System-of-record tagging (GR-3):** Tag each evidence piece: `[StrongRoom]`, `[VendorSmart]`, `[native Vantaca]`, `[Stripe]`, `[other]`. This tag must appear in the Source line.

### Step 5 — Split Rows into Capability-Group Batches

**Rule: ≤ 20 rows per batch.**

Group rows by capability name. Typical splits:

| Batch | Capabilities | Approx rows |
|---|---|---|
| Run 1 | Management Fee Administration (6.15) | 35–51 |
| Run 2 | Supply Charges (6.8) + Reimbursables (6.9) + Systems (6.12.9) | 25–35 |
| Run 3 | Amenity Rentals (6.12) + Audit/Tax/CPA (6.10) | 20–30 |

If a single capability group > 20 rows, split alphabetically by dimension.

### Step 6 — Extract Branch Answers

For each row:
1. Check `references/greg_approved_classifications.md` — if topic matches a Greg ruling, use it as authoritative context
2. Search retrieved transcript evidence
3. Scope to community management context (GR-2)
4. Tag system of record in Source line (GR-3)
5. Write `branch_answer`: `"{answer}\n\nSource: {file} [{timestamp}, {speaker}] [system: {system-of-record}]"`
6. If partial: append `"\n\nGAPS: {what is missing}"`
7. If not found: `"Not Found — {brief reason}\n\nSource: {file} (full transcript reviewed; topic not addressed)\n\nGAPS: {topic} not discussed in this session"`

**HITL threshold:** When transcript is silent AND capability references a third-party integration (not native Vantaca), set `"classification": ""` and `"hitl": true`. Write `[HITL: integration applicability unconfirmed — transcript silent]` in `assessor_notes`.

### Step 7 — Classify Each Row

Check `references/greg_approved_classifications.md` first. Then apply the decision ladder:

0. Greg-Approved Domain Rule applies? → Use it, record GR-N in notes
1. Either side unreadable / Not Found? → `"classification": ""`, `"hitl": true`, write `[HITL: <reason>]` in notes
2. Branch explicitly doesn't do this? → `"NA"`
3. Capability covered by StrongRoom, VendorSmart, or Stripe? → `"AC"`, record `[GR-1]`
4. TownSq native cannot produce the outcome today? → `"FB"`
5. Capability in flight / not yet live? → `"FB"`; name dependency and date
6. Only system setup needed; branch steps survive? → `"AC"`
7. Branch steps/roles/approvals must change? → `"PC"`
8. Base = AC but automated exception surfacing required? → `"AC"`, add `[GR-4: exception automation FB gap — <description>]` in notes
9. Still torn? → `"classification": ""`, `"hitl": true`, write `[HITL: <reason>]` in notes

---

## ⚠️ Classification Field Contract (MANDATORY)

The `classification` field in every row JSON **must be one of:**

| Value | Meaning |
|---|---|
| `"PC"` | Process Change |
| `"AC"` | Adoption / Config |
| `"FB"` | Feature Backlog |
| `"NA"` | Not Applicable |
| `""` | Human review needed (HITL) |

**`"HITL"` is NOT a valid value for the `classification` field.** It will be stripped by the script.

For rows requiring human review:
- Set `"classification": ""` (empty string)
- Set `"hitl": true`
- Write `[HITL: <reason>]` in `assessor_notes`
- Leave `"proximity": ""`

The build script applies amber fill to the Classification cell automatically for HITL rows. **The cell value will be blank — no text is written into it.**

---

### Step 8 — Build Assessment xlsx (BATCHED via run_skill_script)

Call `build_assessment_batch.py` via **`run_skill_script`**. The script always outputs the xlsx as base64 to stdout — no extra flag or parameter is needed.

#### Why `run_skill_script`, not `execute_code`

The script file lives in the skill sandbox. `execute_code` runs in a completely isolated code sandbox that cannot access skill sandbox files — calling the script from `execute_code` will always produce a `FileNotFoundError`. `run_skill_script` executes directly in the skill sandbox and prints the base64-encoded xlsx to stdout, which is then captured and passed to `render_content`.

#### Canonical build pattern (per batch)

```
result = run_skill_script(
  skillId: <this skill's ID>,
  scriptPath: "scripts/build_assessment_batch.py",
  inputData: {
    "branch": "CMA",
    "session": 6,
    "run": 1,
    "rows": [ ... ]
  }
)
```

**Input JSON fields:**

| Field | Type | Description |
|---|---|---|
| `branch` | string | Branch name, e.g. `"CMA"` |
| `session` | number | Session number, e.g. `6` |
| `run` | number | Batch/run number within session, e.g. `1` |
| `rows` | array | Row data objects (≤ 20 rows) |

**Verification before delivery — check all three:**
1. `result.exitCode == 0`
2. `result.stdout` is non-empty
3. `result.stdout` starts with `UEsD` (xlsx base64 magic bytes)

If any check fails, do NOT call `render_content`. Report what failed and stop.

**If the script fails for any reason — STOP.** Do not write inline Python to replicate the script logic. The column schema in this guide is reference documentation, not a licence to rebuild the script inline. Report the exact blocker and wait for the user to resolve it.

**If `run_skill_script` times out:** reduce batch size from 20 to 15 rows and retry.

#### Column schema (15 columns, fixed order)

| # | Column | Valid values |
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
| 13 | Classification | `PC`, `AC`, `FB`, `NA`, or **blank**. Never `HITL`. Amber fill = HITL. |
| 14 | Assessor Notes | `[HITL: ...]`, `[RECOMMENDATION: ...]`, `[GR-N: ...]` as applicable. |
| 15 | Proximity | `Exact match`, `High (~75%)`, `Moderate (~50%)`, `Low (~25%)`, `No match`, or blank. |

#### Classification color map (column 13)

| Code | Fill | Font |
|---|---|---|
| AC | #70AD47 (green) | White bold |
| FB | #FF0000 (red) | White bold |
| PC | #4472C4 (blue) | White bold |
| NA | #FFD966 (yellow) | Black bold |
| blank/HITL | #FFC000 (amber) | — cell is **blank** (no text); amber fill is the only indicator |

#### Proximity color map (column 15)

| Value | Fill | Font |
|---|---|---|
| Exact match | #70AD47 (green) | White bold |
| High (~75%) | #A9D18E (light green) | Black bold |
| Moderate (~50%) | #FFD966 (yellow) | Black bold |
| Low (~25%) | #F4B942 (orange) | Black bold |
| No match | #FF0000 (red) | White bold |
| blank | #FFC000 (amber) | — |

#### Other formatting constants

- Header fill: #1F4E79 (dark blue), white bold font, size 11
- Freeze panes: A2 | Wrap text: all cells | Vertical align: top
- Row height: 80pt (data), 30pt (header)
- Column widths: [10, 10, 8, 14, 18, 8, 22, 28, 9, 45, 55, 45, 14, 60, 18]
- Sheet name: `Assessment`

#### Output file naming

```
Assessment_{Branch}_Session{N}_Run{M}.xlsx
```
Examples: `Assessment_CMA_Session6_Run1.xlsx`, `Assessment_CMA_Session6_Run2.xlsx`

### Step 9 — Deliver Files and Report

**Mandatory for every batch. Never skip. Deliver immediately after each run_skill_script call — do not queue.**

After verifying `result.stdout` starts with `UEsD`, deliver via `render_content`:

```
render_content(
  displayType: "download",
  title: "Assessment_{Branch}_Session{N}_Run{M}.xlsx",
  content: result.stdout,
  metadata: {
    filename: "Assessment_{Branch}_Session{N}_Run{M}.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  }
)
```

After all batches delivered, output summary report (< 5KB — DynamoDB item size compliance):

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
| Pending HITL review (blank) | X |

## Assessment Workbooks
- Assessment_{Branch}_Session{N}_Run1.xlsx — [count] rows ↓ (download link above)
- Assessment_{Branch}_Session{N}_Run2.xlsx — [count] rows ↓ (download link above)
- [...]
```

Do NOT output individual answers, mapping details, search queries, or batch logs.

---

## 4. Row Data Structure

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
  "branch_answer": "All billing is handled in Vantaca...\n\nSource: CMA_Session6.vtt [00:05:01, Kim Dunbar] [system: native Vantaca]",
  "townsq_capability": "After config — Management fee billing contracts configured in TownSq...",
  "classification": "AC",
  "assessor_notes": "BRANCH: ... TOWNSQ: [native Vantaca] ... DELTA: ... WHY AC: ... Confidence: ...",
  "proximity": "High (~75%)",
  "hitl": false
}
```

**`classification`**: `"PC"` / `"AC"` / `"FB"` / `"NA"` / `""`. **Never `"HITL"`.**
**`proximity`**: `"Exact match"` / `"High (~75%)"` / `"Moderate (~50%)"` / `"Low (~25%)"` / `"No match"` / `""` (blank for HITL).
**`hitl`**: `true` for blank-classification rows. Script applies amber fill; cell value stays blank.

---

## 5. Known Failure Modes & Fixes

| Failure | Cause | Fix |
|---|---|---|
| Response cut off mid-run | Payload too large | Batch at ≤ 20 rows |
| `run_skill_script` timeout | Oversized payload | Reduce to 15 rows; retry |
| `getSpreadsheetInfo` column not found | Column names vary by file | Always call getSpreadsheetInfo before querying |
| Transcript evidence missing | Single broad VTT query | Use 3–4 targeted topic-cluster queries |
| 0 rows from mapping CSV | Session stored as number, queried as string | Check sample values in getSpreadsheetInfo output |
| `resolve_session_scope_v2.py` errors | Row key mismatch or rubric index issue | Stop and report exact error. Do not bypass with manual scope resolution. |
| "HITL" appearing in Classification cell | `classification` set to `"HITL"` in row data | Set `"classification": ""` + `"hitl": true`. Never use `"HITL"` as a classification value. |
| `result.stdout` empty after `run_skill_script` | Script errored silently | Check `result.stderr` and `result.exitCode`. Report and stop. |
| `result.stdout` does not start with `UEsD` | Script did not output valid base64 | Check `result.exitCode` and `result.stderr`. Report and stop. Do not call render_content. |
| render_content produces empty download | stdout was not valid base64 | Verify stdout starts with `UEsD` before delivering. |
| FileNotFoundError when using execute_code | Script lives in skill sandbox, not code sandbox | Use `run_skill_script` only for `build_assessment_batch.py`. |
| Persona writes inline Python to build xlsx | Script failure with no halt instruction | STOP, report what failed, describe the fix needed, wait for user to update the script. |
| Over-generation of FB | FB bias applied before checking integrations | Check GR-1 first |
| Wrong context (business vs. community) | AI evaluating business-client features | Scope to HOA community management (GR-2) |
| StrongRoom/Vantaca conflation | Treating StrongRoom as native Vantaca | Tag system of record in Source lines (GR-3) |
| Proximity missing | Old 14-column schema | 15 columns required; proximity is col 15 |
| File not delivered as download link | `render_content` skipped | Call `render_content` after every successful batch |
| Wrong data product queried | Name guessed rather than matched to convention | Confirm data product name against Section 2c before querying |

---

## 6. Transcript Evidence Quality Rules

- **Cite speaker and timestamp** for every answer (e.g., `[00:05:01–00:05:14, Kim Dunbar]`)
- **Tag system of record** in every Source line: `[system: native Vantaca / StrongRoom / VendorSmart / Stripe / other]`
- **Scope to community management context** — note any business-client context mismatch
- **Do not use TownSq capability column as branch evidence**
- **Synthesize only explicit statements** — no inference
- **Not Found is valid** — use it when transcript is genuinely silent
- **GAPS line required** when some sub-parts of a multi-part question are unanswered

---

## 7. Classification Quick Reference

| Code | Field value | When |
|---|---|---|
| AC | `"AC"` | TownSq supports it after config; OR supported integration covers it |
| PC | `"PC"` | TownSq supports it; branch steps/roles/approvals must change |
| FB | `"FB"` | TownSq cannot produce the outcome AND no integration covers it |
| NA | `"NA"` | Branch positively does not do this |
| HITL | `""` + `hitl: true` | Not Found, low confidence, or torn — write `[HITL: <reason>]` in notes |

---

## 8. Assessor Note Format

```
BRANCH: <clause from branch answer>
TOWNSQ: <clause from TownSq capability; name system — native Vantaca / StrongRoom / VendorSmart / integration>
DELTA: <which facets differ>
WHY <CODE>: <one sentence>
[Also requires: <secondary config or FB automation layer, if any>]
[GR-N: <Greg-Approved Rule applied>]
[HITL: <reason — only on blank-classification rows>]
[RECOMMENDATION: <improvement or upsell note — if applicable>]
Confidence: <High | Medium | Low> (<what is solid; what is not>)
```

Proximity is written in **col 15**, not inside Assessor Notes. Do not use "non-negotiable" (GR-6).

---

## 9. Greg-Approved Classifications Reference

See `references/greg_approved_classifications.md`. Load at Step 2b.

Key rules: GR-1 (integration = AC), GR-2 (community context), GR-3 (systems distinct), GR-4 (exception automation = FB on AC), GR-5 (portal retirement = FB), GR-6 (no non-negotiable), GR-7 (14 confirmed topics).

---

## 10. Session 6 / CMA Reference Run (2026-09-10)

| Batch | Capabilities | Rows | AC | FB | PC | NA | Blank(HITL) |
|---|---|---|---|---|---|---|---|
| Run 1 | Management Fee Admin (6.15) | 39 | 14 | 18 | 3 | 4 | 7 |
| Run 2 | Systems (6.12.9) + Supply (6.8) + Reimbursables (6.9) | 32 | 18 | 8 | 3 | 3 | 14 |
| Run 3 | Amenity Rentals (6.12) + Audit/Tax/CPA (6.10) | 29 | TBD | TBD | TBD | TBD | TBD |

Total Session 6 mapped rows: 100. Transcript: `CMA _ Financial Operations Discovery - Session 6.vtt`.
Data product: `Vantaca - CMA - Session 6` (matches pattern `{Company} - {Branch} - Session {N}`).
Mapping CSV: `Sessions_6_Master_Rubric_Mapping.csv`.

Known pain points captured in Run 2:
- Payment misapplication (assessment vs. reservation) — Will Stanley, 00:55:43
- Role-based JE restriction gap — Melanie Adams, 01:18:44
