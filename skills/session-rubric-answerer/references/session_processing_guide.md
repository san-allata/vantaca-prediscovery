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
Last updated: 2026-11-04 — added evidence source filter (Step 3), screen-walk split rule (Step 5), branch-answer TownSq contamination guard.

---

## 1. Overview

This guide documents the proven end-to-end pattern for processing any discovery session transcript against the Master Rubric. It was written after a live Session 6 run that encountered and resolved three distinct failure modes, then updated with classification corrections from four Greg Hamm SME review sessions, then updated again (2026-11-04) with evidence source filter and screen-walk split rules after a Session 3 audit identified TownSq-description contamination in branch answers. Follow it exactly before improvising.

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

Copy the following fields verbatim, character-for-character, from the mapping CSV stored in `rubric_rows[uid]`:

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

Every `branch_answer` is bound to one specific `(uid, exact_master_rubric_question)` pair.

Before writing any branch answer:
1. Re-read `exact_master_rubric_question` for that UID from `rubric_rows[uid]`.
2. Confirm the transcript evidence cited is an answer to that specific question.
3. Do not reuse one evidence chunk as the answer for a different UID's question.

### Rule 3: TownSq Capability Is Also Read-Only

Source `townsq_capability` exclusively from `rubric_rows[uid]['townsq_capability_what_townsq_supports_today']`. Do not rewrite, paraphrase, or supplement it from data product search results.

### Rule 4: Validation Gate Before Every Batch Build

Before passing rows to `execute_code`, confirm each row in the batch:

- [ ] `row['uid']` == `rubric_rows[uid]['uid']` — exact match
- [ ] `row['dimension']` == `rubric_rows[uid]['dimension']` — exact string
- [ ] `row['discovery_question']` == `rubric_rows[uid]['exact_master_rubric_question']` — exact string
- [ ] `row['townsq_capability']` == `rubric_rows[uid]['townsq_capability_what_townsq_supports_today']` — exact string
- [ ] `row['branch_answer']` Source citation references evidence relevant to `row['discovery_question']`

Print a one-line pre-build report before each `execute_code` call.

---

### Step 2 — Load Greg-Approved Classifications

```
read_skill_resource(skillId, "references/greg_approved_classifications.md")
```

Hold in context for the full run.

### Step 3 — Fetch Transcript Evidence (Batched by Topic)

**Do NOT load the full transcript in one call.** Use 3–4 targeted `get_information_from_dataProduct` calls per topic cluster.

**Context scoping (GR-2):** Interpret all evidence through the lens of HOA/community management.

**System-of-record tagging (GR-3):** Tag each evidence piece: `[StrongRoom]`, `[VendorSmart]`, `[native Vantaca]`, `[Stripe]`, `[other]`.

#### ⚠️ Evidence Source Filter (MANDATORY after every data product query)

After each `get_information_from_dataProduct` call, inspect every returned chunk's source filename and discard non-transcript chunks before using any evidence.

**Valid transcript file extensions: `.docx`, `.vtt`, `.md`**

**Discard a chunk immediately if its source file:**
- Has an `.xlsx` or `.csv` extension
- Contains any of these patterns in its filename: `MasterRubric`, `plain`, `mapping`, `Associa`, `Rubric`, `Crosswalk`, `Facilitator`, `Guide`
- Is written in third-person product-documentation style (opens with "✅", "⚠️", or a TownSq product name as the subject of a capability description)

**Only use chunks whose source filename contains the branch/client name and `Session`** — e.g., `CAMS - Vantaca Prediscovery Phase 2 - Session 3.docx`, `CMA_Session6.vtt`, `Q0914-Q0943.md`.

Log the filenames of all retained and discarded chunks before proceeding to Step 3b.

---

### Step 3b — Anchor Evidence to UIDs ⚠️ (MANDATORY before extracting answers)

After fetching and filtering transcript evidence, before writing any branch answer:

1. List every UID and its `exact_master_rubric_question` from `rubric_rows`.
2. For each retained evidence chunk, identify which specific UID(s) it is relevant to.
3. Write each branch answer only from evidence relevant to that UID's own question.
4. Do NOT reuse one evidence chunk as the answer for a different UID's question.

---

### Step 4 — Split Rows into Capability-Group Batches

**Rule: ≤ 20 rows per batch.**

Group rows by capability name. If a single capability group > 20 rows, split alphabetically by dimension.

### Step 5 — Extract Branch Answers

For each row:
1. Read `exact_master_rubric_question` for this UID from `rubric_rows[uid]`. Answer that question only.
2. Check `references/greg_approved_classifications.md` for topic rulings.
3. Use `planned_question` (col C) as the transcript search key to locate evidence.
4. Scope evidence to `capability` (col F) and `dimension` (col G).
5. Process rows in priority order: P0 → P1 → P2 → P3.
6. Tag system of record in the Source line (GR-3).
7. Write `branch_answer` in first-person plural.
8. If partial: append `"\n\nGAPS: {what is missing}"`
9. If not found: `"Not Found — {brief reason}\n\nSource: {file} (full transcript reviewed; topic not addressed)\n\nGAPS: {topic} not discussed"`
10. Set `answer_confidence`, `answer_has_gaps`, `answer_not_found`.

#### ⚠️ Screen-Walk Split Rule (MANDATORY for live-demonstration sessions)

Many sessions involve branch staff demonstrating TownSq on screen. A single utterance simultaneously describes what TownSq does (→ `townsq_capability`) and what the branch does (→ `branch_answer`). You must split them.

**The test for every sentence before writing it into `branch_answer`:**
> *Is TownSq / the platform the grammatical subject of this sentence?*
> - **Yes** → Do NOT put it in `branch_answer`. Rewrite with the staff member as subject, or write Not Found.
> - **No** → it is a branch action. It belongs in `branch_answer`.

**Correct split examples:**

| Speaker says | ✅ Write in branch_answer | ❌ Never write in branch_answer |
|---|---|---|
| *"Within TownSq Business, the delivery status shows here — delivered, opened, or failed"* | *"After we send, we check the delivery status in the E-blast tab to see who got it and who didn't."* | *"TownSq Business shows delivery status: delivered/opened/failed."* |
| *"You can see in the activity notes tab — it'll show what's occurred"* | *"When a homeowner calls back, we pull up the activity notes tab to see the full history."* | *"The activity notes tab shows what occurred on the property."* |
| *"TownSq Community requests show if opened, in-progress, or untouched"* | *"We look at open requests to see if the homeowner has opened them."* | *"TownSq Community shows request status: opened/in-progress/untouched."* |
| *"There's no validation controls for email or phone in TownSq Business"* | *"We don't have any validation on email or phone — we repeat what the owner tells us twice to confirm."* | *"TownSq Business has no validation controls for email or phone."* |

**If the only available evidence is a TownSq feature description with no accompanying staff action:**
→ Write `"Not Found — transcript addresses this only via system demonstration; branch workflow not separately confirmed."`
→ Do NOT convert a TownSq feature description into a branch answer.

#### ⚠️ Branch Answer Must Not Describe TownSq

`branch_answer` answers *"What does the branch do today?"* — always in first-person plural ("We…").

It must **never** open with or primarily contain:
- A statement about what TownSq/Vantaca/C3 supports or does
- A navigation instruction ("Click on X to see Y")
- A feature inventory ("TownSq Business supports A, B, and C")

These belong in `townsq_capability` (col 10), which is read-only from the CSV.

### Step 6 — Emit answered_rows JSON

Output the complete `answered_rows` array. Leave `classification`, `assessor_notes`, `proximity`, and `hitl` as empty strings or `false`. Hand off to `branch-assessor-skills` for classification.

---

## ⚠️ Classification Field Contract (MANDATORY)

`"HITL"` is NOT a valid value for the `classification` field.

For HITL rows: `"classification": ""` + `"hitl": true` + `[HITL: <reason>]` in `assessor_notes`.

---

## 4. Output Column Schema (13 columns, fixed order)

| # | Column | Field key | Source |
|---|---|---|---|
| 1 | UID | `uid` | Copied verbatim from CSV |
| 2 | QID | `qid` | Copied verbatim from CSV |
| 3 | Session | `session` | Copied verbatim from CSV |
| 4 | Planned Question ID | `planned_question_id` | Copied verbatim from CSV |
| 5 | Capability | `capability` | Copied verbatim from CSV |
| 6 | Dimension | `dimension` | Copied verbatim from CSV |
| 7 | Priority | `priority` | Copied verbatim from CSV |
| 8 | Discovery Question | `discovery_question` | Copied verbatim from CSV |
| 9 | Branch Answer | `branch_answer` | AI-written — grounded in transcript |
| 10 | TownSq Capability | `townsq_capability` | Copied verbatim from CSV |
| 11 | Classification | `classification` | AI-written by branch-assessor-skills |
| 12 | Assessor Notes | `assessor_notes` | AI-written by branch-assessor-skills |
| 13 | Proximity | `proximity` | AI-written by branch-assessor-skills |

---

## 6. Known Failure Modes and Fixes

| Failure | Cause | Fix |
|---|---|---|
| Response cut off mid-run | Payload too large | Batch at ≤ 20 rows |
| Transcript evidence missing | Single broad query | Use 3–4 targeted topic-cluster queries |
| 0 rows from mapping CSV | Session stored as number, queried as string | Check sample values in getSpreadsheetInfo output |
| "HITL" in Classification cell | `classification` set to `"HITL"` | Set `"classification": ""` + `"hitl": true` |
| `outputFiles` empty after `execute_code` | Script errored silently | Check stderr and exitCode. Stop. |
| render_content produces empty download | blobKey not used correctly | Use `outputFiles[0].blobKey` as content |
| Over-generation of FB | FB bias applied before checking integrations | Check GR-1 first |
| Wrong context | AI evaluating business-client features | Scope to HOA community management (GR-2) |
| StrongRoom/Vantaca conflation | Treating StrongRoom as native Vantaca | Tag system of record in Source lines (GR-3) |
| Wrong Dimension or Discovery Question | Fields derived from context instead of CSV | Read from `rubric_rows[uid]`. Run Rule 4 gate. |
| TownSq Capability rewritten | AI paraphrased capability from search results | Read from `rubric_rows[uid]` only |
| Branch answer addresses wrong question | Evidence not anchored to UID | Follow Step 3b |
| Branch answer describes TownSq features | Rubric xlsx chunks used as branch evidence | Apply Step 3 Evidence Source Filter. Discard all non-transcript chunks. Valid extensions: .docx, .vtt, .md |
| Branch answer opens with "TownSq Business supports…" | Screen-walk session — TownSq description extracted instead of branch action | Apply Step 5 Screen-Walk Split Rule. Rewrite with staff as subject. If no staff action → write Not Found |
| Wrong data product queried | Name guessed rather than matched | Confirm name against Section 2c before querying |

---

## 7. Transcript Evidence Quality Rules

- Cite speaker and timestamp for every answer.
- Tag system of record in every Source line: `[system: native Vantaca / StrongRoom / VendorSmart / Stripe / other]`.
- Scope to community management context.
- **Do not use chunks from non-transcript files as branch evidence.** Valid transcript extensions: `.docx`, `.vtt`, `.md`.
- **Do not use the TownSq capability column as branch evidence.**
- Synthesize only explicit statements. Do not infer.
- `Not Found` is valid when the transcript is genuinely silent.
- Append a GAPS line when sub-parts of a question are unanswered.
- Anchor evidence to the specific UID question.
- **branch_answer is always first-person plural ("We…").** TownSq is the tool, not the subject.

---

## 8. Assessor Note Format

```
BRANCH: <clause from branch answer>
TOWNSQ: <clause from TownSq capability; name system>
DELTA: <which facets differ>
WHY <CODE>: <one sentence>
[Also requires: <secondary config or FB automation layer>]
[GR-N: <Greg-Approved Rule applied>]
[HITL: <reason — only on blank-classification rows>]
[RECOMMENDATION: <improvement note>]
Confidence: <High | Medium | Low> (<what is solid; what is not>)
```

Write Proximity in col 13, not inside Assessor Notes. Do not use "non-negotiable" (GR-6).

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
