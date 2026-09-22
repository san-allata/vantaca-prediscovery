# Session Processing Guide
**Canonical operational guide for session-rubric-answerer**
Last updated: 2026-09-22 — added Proximity column, HITL-in-notes rule, Recommendation-in-notes rule

---

## 1. Overview

This guide documents the proven end-to-end pattern for processing any discovery session transcript against the Master Rubric. Follow it exactly before improvising.

**Output:** One xlsx workbook per capability-group batch, each containing 15 columns: rubric metadata, branch answers, TownSq capability, classification, assessor notes, and proximity.

---

## 2. Pre-flight Checklist

Before running anything, confirm:

- [ ] User has provided a session number (or range)
- [ ] Session Mapping CSV is accessible (chat upload or attached data product)
- [ ] Transcript file is accessible (chat upload or attached data product)
- [ ] `getSpreadsheetInfo` called on the mapping CSV to verify column names
- [ ] Rubric index loaded via `read_skill_resource`
- [ ] `references/greg_approved_classifications.md` loaded via `read_skill_resource`

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

If column names differ, re-run `getSpreadsheetInfo` and adjust.

**Expected row count per session:** 80–110 rows typical. If result is 0, check the session number filter value — the column may store session as a number not a string.

### Step 2 — Load Rubric Index

```
read_skill_resource(skillId, "references/rubric_index.json")
```

Parse the returned JSON array. Pass as `rubric_index` in the resolve script input.

### Step 2b — Load Greg-Approved Classifications

```
read_skill_resource(skillId, "references/greg_approved_classifications.md")
```

Hold in context for the full run. Before extracting or classifying any row, check whether the topic matches a Greg-confirmed ruling. If it does, use that ruling and note the rule reference (GR-N) in the assessor notes.

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

**Do NOT attempt to load the full VTT transcript in one call.** Use 3–4 targeted `get_information_from_dataProduct` calls, each covering one topic cluster.

Example split for a Financial Operations session:
1. "management fee configuration, contract storage, fee types, rate changes, dual-sided accounting"
2. "board approval, self-billing controls, separation of duties, revenue recognition"
3. "supply charges, reimbursables, utility invoices, amenity rentals, security deposits"
4. "audit, CPA, tax filings, engagement letters, IRS, extensions"

Adjust topic clusters to match the session's capability areas. Hold all retrieved evidence in context.

**Context scoping (GR-2):** Interpret all evidence through the lens of **HOA/community management** — not commercial business client context. Note any context mismatch.

**System-of-record tagging (GR-3):** Tag each piece of evidence with the system it refers to: `[StrongRoom]`, `[VendorSmart]`, `[native Vantaca]`, `[Stripe]`, `[other]`. This tag must appear in the Source line of the branch answer.

### Step 5 — Split Rows into Capability-Group Batches

**Rule: ≤ 30 rows per batch.**

Group rows by capability name (not cap number — cap numbers can be stored inconsistently). Typical splits:

| Batch | Capabilities | Approx rows |
|---|---|---|
| Run 1 | Management Fee Administration (6.15) | 35–51 |
| Run 2 | Supply Charges (6.8) + Reimbursables/Fee Mgmt (6.9) + Systems (6.12.9) | 25–35 |
| Run 3 | Amenity Rentals & Security Deposits (6.12) + Audit/Tax/CPA (6.10) | 20–30 |

If a single capability group > 30 rows, split alphabetically by dimension.

### Step 6 — Extract Branch Answers

For each row:
1. Check `references/greg_approved_classifications.md` — if topic has a Greg-confirmed answer, use it as authoritative context
2. Search retrieved transcript evidence for the question topic
3. **Scope to community management context** (GR-2)
4. **Tag the system of record** in the Source line (GR-3)
5. Write `branch_answer`: `"{answer}\n\nSource: {file} [{timestamp}, {speaker}] [system: {system-of-record}]"`
6. If partial: append `"\n\nGAPS: {what is missing}"`
7. If not found: `"Not Found — {brief reason}\n\nSource: {file} (full transcript reviewed; topic not addressed)\n\nGAPS: {topic} not discussed in this session"`

**HITL threshold:** When transcript is silent AND TownSq capability references a third-party integration (not native Vantaca), the integration's applicability is unconfirmed. Leave Classification **blank** and write `[HITL: integration applicability unconfirmed — transcript silent]` in Assessor Notes. Do not write "HITL" in the Classification column.

### Step 7 — Classify Each Row

**Before the decision ladder, check `references/greg_approved_classifications.md`.** If the topic matches a Greg ruling, apply it and record the GR-N reference in assessor notes.

Decision ladder (walk in order, stop at first match):
0. Greg-Approved Domain Rule applies? → Use it, record GR-N
1. Either side unreadable / Not Found? → Leave Classification **blank**; write `[HITL: <reason>]` in Assessor Notes
2. Branch explicitly doesn't do this? → **NA**
3. Capability covered by StrongRoom, VendorSmart, or Stripe? → **AC**; record `[GR-1]`
4. TownSq native cannot produce the outcome today? → **FB**
5. Capability in flight / not yet live? → **FB**
6. Only system setup needed; branch steps survive? → **AC**
7. Branch steps/roles/approvals must change? → **PC**
8. Base = AC but automated exception surfacing also required? → **AC**; add `[GR-4: exception automation FB gap — <description>]` in notes
9. Still torn? → Leave Classification **blank**; write `[HITL: <candidates and deciding question>]` in Assessor Notes

**Valid Classification values: `PC`, `AC`, `FB`, `NA`, or blank.**
**"HITL" is NEVER a valid Classification value.** It always goes in Assessor Notes.

**Revised FB-bias:** Applies only when native Vantaca cannot support the outcome AND no integration covers it.

**Improvement recommendations:** When you spot a potential upsell, process improvement, or platform capability that exceeds what the branch currently does, add `[RECOMMENDATION: <text>]` in Assessor Notes. Do not create a separate field or column.

### Step 8 — Build Assessment xlsx (BATCHED via execute_code)

**Use `scripts/build_assessment_batch.py` ONLY.** Never use deprecated snapshot scripts.

For each batch (≤ 30 rows), call `execute_code` (Python) passing rows as the `input` JSON parameter. The script writes `Assessment_Run<N>_<CapGroup>.xlsx`.

**If `execute_code` times out:** reduce batch size from 30 to 20 rows and retry.

#### Column schema (15 columns, fixed order)

| # | Column | Valid values / notes |
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
| 13 | Classification | `PC`, `AC`, `FB`, `NA`, or **blank**. Never "HITL". |
| 14 | Assessor Notes | Free text. Contains `[HITL: ...]`, `[RECOMMENDATION: ...]`, `[GR-N: ...]` tags as applicable. |
| 15 | Proximity | `Exact match`, `High (~75%)`, `Moderate (~50%)`, `Low (~25%)`, `No match`, or blank (HITL rows). |

#### Classification color map (column 13)

| Code | Fill color | Font |
|---|---|---|
| AC | #70AD47 (green) | White bold |
| FB | #FF0000 (red) | White bold |
| PC | #4472C4 (blue) | White bold |
| NA | #FFD966 (yellow) | Black bold |
| blank (HITL) | #FFC000 (amber) | Black bold — write "HITL" as display text in the cell, but do NOT store it in the classification field of the row data |

**Important:** For rows where Classification is blank (HITL), the xlsx builder displays "HITL" in the cell with amber fill as a visual indicator. The underlying data field `classification` remains empty/null.

#### Proximity color map (column 15)

| Value | Fill color | Font |
|---|---|---|
| Exact match | #70AD47 (green) | White bold |
| High (~75%) | #A9D18E (light green) | Black bold |
| Moderate (~50%) | #FFD966 (yellow) | Black bold |
| Low (~25%) | #F4B942 (orange) | Black bold |
| No match | #FF0000 (red) | White bold |
| blank | #FFC000 (amber) | — |

#### Other formatting constants

- Header fill: #1F4E79 (dark blue), white bold font, size 11
- Freeze panes: A2
- Wrap text: all cells
- Vertical align: top (data rows)
- Row height: 80pt (data rows), 30pt (header)
- Column widths: [10, 10, 8, 14, 18, 8, 22, 28, 9, 45, 55, 45, 14, 60, 18]
- Sheet name: `Assessment`

#### Output file naming

```
Assessment_Run<N>_<CapabilityGroup>.xlsx
```

### Step 9 — Deliver and Report

For each batch:
1. Deliver xlsx via `render_content` (displayType: download)
2. Report: rows written, classification breakdown (AC/FB/PC/NA/blank counts), HITL count

Final summary:
- Total rows: N
- AC: N | FB: N | PC: N | NA: N | Blank (HITL): N
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
  "branch_answer": "All billing is handled in Vantaca...\n\nSource: CMA_Session6.vtt [00:05:01, Kim Dunbar] [system: native Vantaca]",
  "townsq_capability": "After config — Management fee billing contracts configured in TownSq...",
  "classification": "AC",
  "assessor_notes": "BRANCH: ... TOWNSQ: [native Vantaca] ... DELTA: ... WHY AC: ... [GR-N: ...] Confidence: ...",
  "proximity": "High (~75%)",
  "hitl": false
}
```

**`classification`** must be one of `"PC"`, `"AC"`, `"FB"`, `"NA"`, or `""` (empty string for HITL rows).
**`proximity`** must be one of `"Exact match"`, `"High (~75%)"`, `"Moderate (~50%)"`, `"Low (~25%)"`, `"No match"`, or `""` (empty for HITL rows).
**`hitl`** — set to `true` for blank-classification rows. The builder will display "HITL" with amber fill in the Classification cell as a visual indicator only.

---

## 5. Known Failure Modes & Fixes

| Failure | Cause | Fix |
|---|---|---|
| Response cut off mid-run | Payload too large for single tool call | Batch at ≤ 30 rows per execute_code call |
| `execute_code` timeout | Inline Python string literals for 100 rows too large | Pass rows as `input` JSON parameter, not inline strings |
| `run_skill_script` payload overflow | 100-row JSON too large for inputData | Use execute_code + build_assessment_batch.py instead |
| `getSpreadsheetInfo` column not found | Column names vary by file | Always call getSpreadsheetInfo before querying |
| Transcript evidence missing for a topic | Single broad VTT query misses detail | Use 3–4 targeted topic-cluster queries |
| 0 rows returned from mapping CSV query | Session column stored as number, queried as string | Check sample values in getSpreadsheetInfo output |
| Over-generation of FB on integration items | FB bias applied without checking integrations first | Check GR-1 before classifying FB |
| Wrong context (business vs. community) | AI evaluating business-client features for community branches | Scope all evidence to HOA community management context (GR-2) |
| StrongRoom/Vantaca conflation | Treating StrongRoom capabilities as native Vantaca | Tag system of record in every answer source line (GR-3) |
| "HITL" written in Classification column | Misapplication of old behavior | Classification must be blank; write `[HITL: <reason>]` in Assessor Notes |
| Proximity missing from output | Old 14-column schema used | Ensure build script outputs 15 columns; proximity is column 15 |
| False ACs on integration topics | Transcript silent but classified AC | Tighten HITL: transcript silent + integration capability → blank Classification + HITL note |

---

## 6. Transcript Evidence Quality Rules

- **Cite speaker and timestamp for every answer**
- **Tag system of record** in every Source line: `[system: native Vantaca / StrongRoom / VendorSmart / Stripe / other]`
- **Scope to community management context** — note any business-client context mismatch
- **Do not use TownSq capability column as branch evidence**
- **Synthesize only explicit statements** — no inference beyond what is said
- **Not Found is valid** — use it when transcript is genuinely silent; do not guess
- **GAPS line required** when some sub-parts of a multi-part question are unanswered

---

## 7. Classification Quick Reference

| Code | When |
|---|---|
| AC | TownSq supports it after config; OR supported Associa integration covers it; branch steps/roles survive |
| PC | TownSq supports it; branch steps/roles/approvals must change |
| FB | TownSq cannot produce the required outcome today AND no supported integration covers it |
| NA | Branch positively does not do this / does not apply |
| **blank** | Not Found, low confidence, or torn between codes — write `[HITL: <reason>]` in Assessor Notes |

**Dominant-blocker rule:** When a row needs both AC and PC, assign PC and note `Also requires: <config>` in Assessor Notes.

**Exception automation rule (GR-4):** Base = AC; add `[GR-4: exception automation FB gap — <description>]` in Assessor Notes.

**Improvement recommendations:** Add `[RECOMMENDATION: <text>]` in Assessor Notes when a platform capability exceeds the branch's current state or an upsell exists.

---

## 8. Assessor Note Format

Every classified row must have assessor notes in this format:

```
BRANCH: <clause from branch answer that drives the code>
TOWNSQ: <clause from TownSq capability; name system — native Vantaca / StrongRoom / VendorSmart / integration>
DELTA: <which facets differ — outcome / mechanism / actors / timing / controls / exceptions / evidence>
WHY <CODE>: <one sentence>
[Also requires: <secondary config or process change, or FB automation layer, if any>]
[GR-N: <Greg-Approved Rule applied, e.g. GR-1: Integration = AC>]
[HITL: <reason — only on blank-classification rows>]
[RECOMMENDATION: <improvement or upsell note — if applicable>]
Confidence: <High | Medium | Low> (<what is solid; what is not>)
```

Note: Proximity is written in the dedicated **Proximity column (col 15)**, not inside Assessor Notes.
Do not use the phrase "non-negotiable" anywhere in notes (GR-6).

---

## 9. Greg-Approved Classifications Reference

See `references/greg_approved_classifications.md` for the full table. Load at Step 2b.

Key rules summary:
- **GR-1:** Integration (StrongRoom / VendorSmart / Stripe) = AC, not FB
- **GR-2:** Community management context only
- **GR-3:** StrongRoom ≠ native Vantaca ≠ VendorSmart
- **GR-4:** Exception automation = FB on top of AC base
- **GR-5:** Third-party portal retirement = always FB
- **GR-6:** No "non-negotiable" language
- **GR-7:** 14 specific topics with Greg-confirmed classifications

---

## 10. Session 6 / CMA Reference Run (2026-09-10)

| Batch | Capabilities | Rows | AC | FB | PC | NA | Blank(HITL) |
|---|---|---|---|---|---|---|---|
| Run 1 | Management Fee Admin (6.15) | 39 | 14 | 18 | 3 | 4 | 7 |
| Run 2 | Systems (6.12.9) + Supply (6.8) + Reimbursables (6.9) | 32 | 18 | 8 | 3 | 3 | 14 |
| Run 3 | Amenity Rentals (6.12) + Audit/Tax/CPA (6.10) | 29 | TBD | TBD | TBD | TBD | TBD |

Note: Run 1's 18 FBs likely include items reclassifiable as AC under GR-1. Re-review against StrongRoom/VendorSmart coverage.

Total Session 6 mapped rows: 100. Transcript: `CMA _ Financial Operations Discovery - Session 6.vtt`.
Data product: `Vantaca - CMA - Session 6`. Mapping CSV: `Sessions_6_Master_Rubric_Mapping.csv`.
