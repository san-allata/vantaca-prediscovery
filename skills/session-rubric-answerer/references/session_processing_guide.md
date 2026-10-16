# Session Processing Guide

> ⛔ HARD RULE — READ BEFORE ANY OTHER STEP
> `xlsx_builder.py` is the ONLY production xlsx builder.
> Call it via `execute_code` — NEVER via `run_skill_script`.
> `run_skill_script` and `execute_code` are isolated sandboxes.
> Files written by `run_skill_script` are NEVER captured in `outputFiles`
> and CANNOT be delivered as downloads. Any xlsx built via `run_skill_script`
> produces a link to nothing. If you are about to call `run_skill_script`
> with the builder script — STOP and switch to `execute_code`.

**Canonical operational guide for session-rubric-answerer**
Last updated: 2026-10-16 — removed domain/cap_num fields and rubric_index dependency; removed resolve_session_scope_v2.py step.

---

## 1. Overview

This guide documents the proven end-to-end pattern for processing any discovery session transcript against the Master Rubric. It was written after a live Session 6 run that encountered and resolved three distinct failure modes, then updated with classification corrections from four Greg Hamm SME review sessions. Follow it exactly before improvising.

**Output:** One xlsx workbook per capability-group batch (13 columns), named `Assessment_{Branch}_Session{N}_Run{M}.xlsx`. Deliver every workbook as a **clickable download link** in chat via `render_content`.

---

## 2. Pre-flight Checklist

Confirm all items before running anything:

- [ ] User has provided a session number (or range)
- [ ] Session Mapping CSV is accessible (chat upload or attached data product)
- [ ] Transcript file is accessible (chat upload or attached data product)
- [ ] `references/greg_approved_classifications.md` loaded via `read_skill_resource`
- [ ] Data product name(s) confirmed against naming convention (Section 2c)

Do NOT proceed if any item is unchecked.

---

## 2c. Data Product Naming Convention

Match data product names exactly. Do not guess or abbreviate.

| Type | Pattern | Example |
|---|---|---|
| Per-session transcript + mapping | `{Company} - {Branch} - Session {N}` | `Vantaca - CMA - Session 6` |
| Company-wide common data | `{Company} Data Product - Common` | `Vantaca Data Product - Common` |
| Company branch common data | `{Company} - {Branch} Common` | `Vantaca - CMA Common` |
| Master Rubric session data | `{Company} - Master Rubric - Session {N}` | `Vantaca - Master Rubric - Session 6` |

**If the data product name does not match any pattern above, report the mismatch and ask for confirmation before proceeding. Do not query a data product whose name has not been confirmed.**

---

## 3. Step-by-Step Workflow

### Step 1 — Extract Session Rows via session-mapping-extractor

Call `session-mapping-extractor`'s `scripts/extract_session_rows.py` via `run_skill_script`:

```json
{ "session": <N> }
```

The script returns columns B–I sorted by `planned_question_id` then `priority`. Build the rubric_rows dict immediately:

```python
rubric_rows = {row['uid']: row for row in extracted_rows}
```

**Read all subsequent field values from `rubric_rows[uid]`. Do not read them from memory, transcript evidence, or data product search results.**

**Known column names:**

| Field key | CSV original name |
|---|---|
| `planned_question_id` | Planned Question ID |
| `planned_question` | Planned Question |
| `uid` | UID |
| `qid` | QID |
| `capability` | Capability |
| `dimension` | Dimension |
| `priority` | Priority |
| `exact_master_rubric_question` | Exact Master Rubric Question |
| `townsq_capability_what_townsq_supports_today` | TownSq Capability— what TownSq supports today |

**Expected row count per session:** 80–110 rows typical. If result is 0, check the session number filter value.

---

## 3a. Metadata Integrity Contract ⚠️ (MANDATORY — enforced before every batch build)

### Rule 1: Master Rubric Fields Are Read-Only — Never Derived

Copy the following fields verbatim, character-for-character, from the mapping CSV stored in `rubric_rows[uid]`. Do not infer, paraphrase, summarise, truncate, correct, or fill them from context, memory, or transcript evidence:

| Output row field | Source — `rubric_rows[uid]` key |
|---|---|
| `uid` | `uid` |
| `qid` | `qid` |
| `session` | `session` |
| `planned_question_id` | `planned_question_id` |
| `capability` | `capability` |
| `dimension` | `dimension` |
| `priority` | `priority` |
| `discovery_question` | `exact_master_rubric_question` |
| `townsq_capability` | `townsq_capability_what_townsq_supports_today` |

**If a CSV field is empty or null → output field is blank. Never substitute.**
**If a CSV field was not retrieved → STOP. Re-query before proceeding. Do not fill from memory.**

### Rule 2: Answer–UID Binding

Every `branch_answer` is bound to one specific `(uid, exact_master_rubric_question)` pair. It must respond to the specific question for that UID — not to a neighbouring row's question.

Before writing any branch answer:
1. Re-read `exact_master_rubric_question` for that UID from `rubric_rows[uid]`.
2. Confirm the transcript evidence cited is an answer to that specific question.
3. Do not reuse one evidence chunk as the answer for a different UID's question.

### Rule 3: TownSq Capability Is Also Read-Only

Source `townsq_capability` exclusively from `rubric_rows[uid]['townsq_capability_what_townsq_supports_today']`. Do not rewrite, paraphrase, or supplement it from data product search results. If the retrieved value appears mis-mapped or incomplete, note this in Assessor Notes. Do not silently replace it.

### Rule 4: Validation Gate Before Every Batch Build

Before passing rows to `execute_code`, confirm each row in the batch:

- [ ] `row['uid']` == `rubric_rows[uid]['uid']` — exact match
- [ ] `row['dimension']` == `rubric_rows[uid]['dimension']` — exact string, not a synonym or summary
- [ ] `row['discovery_question']` == `rubric_rows[uid]['exact_master_rubric_question']` — exact string
- [ ] `row['townsq_capability']` == `rubric_rows[uid]['townsq_capability_what_townsq_supports_today']` — exact string
- [ ] `row['branch_answer']` Source citation references evidence relevant to `row['discovery_question']`

**If any check fails:** correct the field from `rubric_rows[uid]`, or set `classification: ""` and `hitl: true` with `[HITL: metadata mismatch — field X does not match CSV for this UID]` in notes.

Print a one-line pre-build report before each `execute_code` call:
```
Pre-build: [N] rows — UIDs [Q0089, Q0090, ...] — all metadata sourced from CSV ✓
```
Or, if mismatches were found and corrected:
```
Pre-build: [N] rows — corrected: [list of UIDs and fields fixed] — proceeding
```

---

### Step 2 — Load Greg-Approved Classifications

```
read_skill_resource(skillId, "references/greg_approved_classifications.md")
```

Hold in context for the full run.

### Step 3 — Fetch Transcript Evidence (Batched by Topic)

**Do NOT load the full VTT in one call.** Use 3–4 targeted `get_information_from_dataProduct` calls per topic cluster.

Example split for a Financial Operations session:
1. "management fee configuration, contract storage, fee types, rate changes, dual-sided accounting"
2. "board approval, self-billing controls, separation of duties, revenue recognition"
3. "supply charges, reimbursables, utility invoices, amenity rentals, security deposits"
4. "audit, CPA, tax filings, engagement letters, IRS, extensions"

**Context scoping (GR-2):** Interpret all evidence through the lens of **HOA/community management**.

**System-of-record tagging (GR-3):** Tag each evidence piece: `[StrongRoom]`, `[VendorSmart]`, `[native Vantaca]`, `[Stripe]`, `[other]`. This tag must appear in the Source line.

---

### Step 3b — Anchor Evidence to UIDs ⚠️ (MANDATORY before extracting answers)

After fetching transcript evidence, before writing any branch answer:

1. List every UID and its `exact_master_rubric_question` from `rubric_rows`.
2. For each retrieved evidence chunk, identify which specific UID(s) it is relevant to — based on that UID's question text, not on a broad topic label.
3. Write each branch answer only from evidence relevant to that UID's own question.
4. Do NOT reuse one evidence chunk as the answer for a different UID's question.

**Example of the problem this prevents:**
Evidence about "how invoices are received" is relevant to Q0089 ("Walk through your AP process step by step") and Q0106 ("Are paper invoices still received...") — but these are different questions that require different scope and emphasis. Do not reuse evidence scoped to Q0089 wholesale as Q0106's answer.

---

### Step 4 — Split Rows into Capability-Group Batches

**Rule: ≤ 20 rows per batch.**

Group rows by capability name. Typical splits:

| Batch | Capabilities | Approx rows |
|---|---|---|
| Run 1 | Management Fee Administration (6.15) | 35–51 |
| Run 2 | Supply Charges (6.8) + Reimbursables (6.9) + Systems (6.12.9) | 25–35 |
| Run 3 | Amenity Rentals (6.12) + Audit/Tax/CPA (6.10) | 20–30 |

If a single capability group > 20 rows, split alphabetically by dimension.

### Step 5 — Extract Branch Answers

For each row:
1. Read `exact_master_rubric_question` for this UID from `rubric_rows[uid]`. Answer that question only.
2. Check `references/greg_approved_classifications.md`. If the topic matches a Greg ruling, use it as authoritative context for scoping.
3. Use `planned_question` (col C) as the transcript search key to locate evidence.
4. Scope evidence to `capability` (col F) and `dimension` (col G).
5. Process rows in priority order within each planned_question group: P0 → P1 → P2 → P3.
6. Tag system of record in the Source line (GR-3).
7. Write `branch_answer`: `"{answer}\n\nSource: {file} [{timestamp}, {speaker}] [system: {system-of-record}]"`
8. If partial: append `"\n\nGAPS: {what is missing}"`
9. If not found: `"Not Found — {brief reason}\n\nSource: {file} (full transcript reviewed; topic not addressed)\n\nGAPS: {topic} not discussed in this session"`
10. Set `answer_confidence` (High/Medium/Low), `answer_has_gaps` (bool), `answer_not_found` (bool).

**HITL threshold:** When the transcript is silent AND the capability references a third-party integration (not native Vantaca), set `"classification": ""` and `"hitl": true`. Write `[HITL: integration applicability unconfirmed — transcript silent]` in `assessor_notes`.

### Step 6 — Emit answered_rows JSON

Output the complete `answered_rows` array. Leave `classification`, `assessor_notes`, `proximity`, and `hitl` as empty strings or `false`. Hand off to `branch-assessor-skills` for classification.

---

## ⚠️ Classification Field Contract (MANDATORY)

The `classification` field in every row JSON must be one of:

| Value | Meaning |
|---|---|
| `"PC"` | Process Change |
| `"AC"` | Adoption / Config |
| `"FB"` | Feature Backlog |
| `"NA"` | Not Applicable |
| `""` | Human review needed (HITL) |

**`"HITL"` is NOT a valid value for the `classification` field.**

For rows that require human review:
- Set `"classification": ""` (empty string)
- Set `"hitl": true`
- Write `[HITL: <reason>]` in `assessor_notes`
- Leave `"proximity": ""`

The build script applies amber fill to the Classification cell automatically for HITL rows. **The cell value will be blank — no text is written into it.**

---

## 4. Output Column Schema (13 columns, fixed order)

| # | Column | Field key | Source | Valid values |
|---|---|---|---|---|
| 1 | UID | `uid` | **Copied verbatim from CSV** | — |
| 2 | QID | `qid` | **Copied verbatim from CSV** | — |
| 3 | Session | `session` | **Copied verbatim from CSV** | — |
| 4 | Planned Question ID | `planned_question_id` | **Copied verbatim from CSV** | — |
| 5 | Capability | `capability` | **Copied verbatim from CSV** | — |
| 6 | Dimension | `dimension` | **Copied verbatim from CSV** | — |
| 7 | Priority | `priority` | **Copied verbatim from CSV** | — |
| 8 | Discovery Question | `discovery_question` | **Copied verbatim from CSV** (`exact_master_rubric_question`) | — |
| 9 | Branch Answer | `branch_answer` | **AI-written** — grounded in transcript | — |
| 10 | TownSq Capability | `townsq_capability` | **Copied verbatim from CSV** (`townsq_capability_what_townsq_supports_today`) | — |
| 11 | Classification | `classification` | **AI-written by branch-assessor-skills** | `PC`, `AC`, `FB`, `NA`, or blank. Never `HITL`. Amber fill = HITL. |
| 12 | Assessor Notes | `assessor_notes` | **AI-written by branch-assessor-skills** | `[HITL: ...]`, `[RECOMMENDATION: ...]`, `[GR-N: ...]` as applicable. |
| 13 | Proximity | `proximity` | **AI-written by branch-assessor-skills** | `Exact match`, `High (~75%)`, `Moderate (~50%)`, `Low (~25%)`, `No match`, or blank. |

#### Classification color map (column 11)

| Code | Fill | Font |
|---|---|---|
| AC | #E2EFDA (green) | Bold |
| FB | #FCE4D6 (orange) | Bold |
| PC | #FFF2CC (yellow) | Bold |
| NA | #EDEDED (grey) | Bold |
| blank/HITL | #FFEB9C (amber) | — cell is blank (no text); amber fill is the only indicator |

#### Proximity color map (column 13)

| Value | Fill |
|---|---|
| Exact match | #E2EFDA (green) |
| High (~75%) | #A9D18E (light green) |
| Moderate (~50%) | #FFF2CC (yellow) |
| Low (~25%) | #F4B942 (orange) |
| No match | #FCE4D6 (red-orange) |
| blank | #FFEB9C (amber) |

#### Other formatting constants

- Header fill: #1F4E79 (dark blue), white bold font, size 10
- Freeze panes: A2 | Wrap text: all cells | Vertical align: top
- Row height: 60pt (data), 30pt (header)
- Sheet name: `Assessment`

#### Output file naming

```
Assessment_{Branch}_Session{N}_Run{M}.xlsx
```

---

## 5. Row Data Structure

```json
{
  "uid": "Q0468",
  "qid": "6.15.1",
  "session": 6,
  "planned_question_id": "S6-Q3",
  "capability": "Management Fee Administration",
  "dimension": "Fee schedule configuration per association",
  "priority": "P0",
  "discovery_question": "How is the monthly management fee configured...",
  "branch_answer": "All billing is handled in Vantaca...\n\nSource: CMA_Session6.vtt [00:05:01, Kim Dunbar] [system: native Vantaca]",
  "townsq_capability": "After config — Management fee billing contracts configured in TownSq...",
  "answer_confidence": "High",
  "answer_has_gaps": false,
  "answer_not_found": false,
  "classification": "",
  "assessor_notes": "",
  "proximity": "",
  "hitl": false
}
```

**`classification`**: `"PC"` / `"AC"` / `"FB"` / `"NA"` / `""`. **Never `"HITL"`.**
**`proximity`**: `"Exact match"` / `"High (~75%)"` / `"Moderate (~50%)"` / `"Low (~25%)"` / `"No match"` / `""` (blank for HITL).
**`hitl`**: `true` for blank-classification rows. Script applies amber fill; cell value stays blank.

**Populate all fields in columns 1–10 exclusively from `rubric_rows[uid]`. Do not use memory or transcript evidence.**

---

## 6. Known Failure Modes and Fixes

| Failure | Cause | Fix |
|---|---|---|
| Response cut off mid-run | Payload too large | Batch at ≤ 20 rows |
| `run_skill_script` timeout | Oversized payload | Reduce to 15 rows; retry |
| `getSpreadsheetInfo` column not found | Column names vary by file | Call getSpreadsheetInfo before querying |
| Transcript evidence missing | Single broad VTT query | Use 3–4 targeted topic-cluster queries |
| 0 rows from mapping CSV | Session stored as number, queried as string | Check sample values in getSpreadsheetInfo output |
| "HITL" appearing in Classification cell | `classification` set to `"HITL"` in row data | Set `"classification": ""` + `"hitl": true`. Never use `"HITL"` as a classification value. |
| `outputFiles` empty after `execute_code` | Script errored silently | Check stderr and exitCode. Report and stop. |
| render_content produces empty download | blobKey not used correctly | Use `outputFiles[0].blobKey` as content. Do not pass a base64 string. |
| Over-generation of FB | FB bias applied before checking integrations | Check GR-1 first |
| Wrong context (business vs. community) | AI evaluating business-client features | Scope to HOA community management (GR-2) |
| StrongRoom/Vantaca conflation | Treating StrongRoom as native Vantaca | Tag system of record in Source lines (GR-3) |
| Proximity missing | Old column schema | 13 columns required; proximity is col 13 |
| File not delivered as download link | `render_content` skipped | Call `render_content` after every successful batch |
| Wrong data product queried | Name guessed rather than matched to convention | Confirm data product name against Section 2c before querying |
| Wrong Dimension or Discovery Question in output | Fields derived from context instead of copied from CSV | Read dimension and discovery_question from `rubric_rows[uid]`. Run Section 3a Rule 4 gate before every batch build. |
| TownSq Capability rewritten in output | AI paraphrased or replaced capability from search results | Read townsq_capability exclusively from `rubric_rows[uid]['townsq_capability_what_townsq_supports_today']`. |
| Branch answer addresses wrong question | Evidence not anchored to UID before extraction | Follow Step 3b. Re-read `exact_master_rubric_question` from `rubric_rows[uid]` before writing each answer. |

---

## 7. Transcript Evidence Quality Rules

- Cite speaker and timestamp for every answer (e.g., `[00:05:01–00:05:14, Kim Dunbar]`).
- Tag system of record in every Source line: `[system: native Vantaca / StrongRoom / VendorSmart / Stripe / other]`.
- Scope to community management context. Note any business-client context mismatch.
- Do not use the TownSq capability column as branch evidence.
- Synthesize only explicit statements. Do not infer.
- `Not Found` is a valid answer. Use it when the transcript is genuinely silent.
- Append a GAPS line when some sub-parts of a multi-part question are unanswered.
- Anchor evidence to the specific UID question. Do not reuse evidence for a different UID's question (see Step 3b).

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

Write Proximity in **col 13**, not inside Assessor Notes. Do not use "non-negotiable" (GR-6).

---

## 9. Greg-Approved Classifications Reference

See `references/greg_approved_classifications.md`. Load at Step 2.

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
