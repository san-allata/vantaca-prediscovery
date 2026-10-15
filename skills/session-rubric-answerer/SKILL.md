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
- `references/xlsx_builder.py` — **The canonical xlsx builder source code.** Read this via `read_skill_resource` at Step 3b, then embed it verbatim inside every `execute_code` call to build Assessment xlsx files. This is the ONLY supported delivery mechanism.
- `scripts/resolve_session_scope_v2.py` — Resolves session mapping rows to rubric rows. Input: `{ "mapping_rows": [...], "rubric_index": [...] }`. Output: resolved rows or list of unresolved questions. **Use via `run_skill_script` only.**

- `scripts/build_assessment_snapshot_v2.py` — **DEPRECATED.** Do not use for production.
- `scripts/build_assessment_snapshot.py` — **DEPRECATED.** Do not use.
- `assets/MasterRubricTemplateWithAssociaAnswers_FB.xlsx` — Master Rubric asset (read-only reference).

---

## ⚠️ CRITICAL: xlsx Delivery Architecture

### Two sandboxes — completely isolated

| Sandbox | Tool | outputFiles captured? | Use for |
|---|---|---|---|
| Skill sandbox | `run_skill_script` | ❌ Never | Scope resolution only |
| Code sandbox | `execute_code` | ✅ Always | xlsx delivery |

### The ONLY correct xlsx delivery pattern

```
Step 1: read_skill_resource("references/xlsx_builder.py")
         → returns the builder source code as a string

Step 2: execute_code(
          language: "python",
          code: <xlsx_builder source> + "\n\nwith open('input.json') as f: build(json.load(f))",
          input: { "branch": "CAMS", "session": 6, "run": 1, "rows": [...] }
        )
         → outputFiles[0].blobKey = path to the written xlsx file

Step 3: render_content(
          displayType: "download",
          content: <blobKey from outputFiles[0]>,   ← NOT base64, NOT stdout
          metadata: {
            filename: "Assessment_CAMS_Session6_Run1.xlsx",
            mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          }
        )
```

### Why NOT stdout base64

`run_skill_script` stdout carries the xlsx as base64. Passing that base64 directly to `render_content` **produces empty/corrupt files** for payloads above ~15KB because the base64 string is silently truncated. The blobKey path approach has no size limit.

### Why NOT run_skill_script for xlsx

`run_skill_script` `outputFiles` is always empty — the skill sandbox never captures written files.

### If outputFiles is empty after execute_code

STOP. Do not attempt a base64 fallback. Report what failed and retry.

---

## Output Column Schema (15 columns, fixed order)

| # | Column | Source | Valid values |
|---|---|---|---|
| 1 | UID | Read-only — copied from CSV verbatim | e.g. Q0285 |
| 2 | QID | Read-only — copied from CSV verbatim | e.g. 6.8.1 |
| 3 | Session | Read-only — copied from CSV verbatim | integer |
| 4 | Planned Question ID | Read-only — copied from CSV verbatim | e.g. S6-Q12 |
| 5 | Domain | Matched from rubric_index by UID — verbatim | e.g. Financial Operations |
| 6 | Cap # | Matched from rubric_index by UID — verbatim | e.g. 6.8 |
| 7 | Capability | Read-only — copied from CSV verbatim | e.g. Supply Charges |
| 8 | Dimension | Read-only — copied from CSV verbatim | e.g. Ancillary billing visibility |
| 9 | Priority | Read-only — copied from CSV verbatim | P0–P3 |
| 10 | Discovery Question | Read-only — copied from CSV verbatim | exact_master_rubric_question |
| 11 | Branch Answer | AI-written | Transcript-grounded + Source + system tag |
| 12 | TownSq Capability | Read-only — copied from CSV verbatim | townsq_capability_what_townsq_supports_today |
| 13 | Classification | AI-written | `PC`, `AC`, `FB`, `NA`, or **blank**. "HITL" is **never** a valid value here. |
| 14 | Assessor Notes | AI-written | `[HITL: <reason>]` for blank rows; `[RECOMMENDATION: <text>]`; `[GR-N: <rule>]` |
| 15 | Proximity | AI-written | `Exact match`, `High (~75%)`, `Moderate (~50%)`, `Low (~25%)`, `No match`, or blank for HITL rows. **Separate column — never embedded in notes.** |

---

## Data Integrity Rules (Highest Priority)

### Columns 1–10 and 12 are Read-Only — Never Derived

These fields are sourced **exclusively** from the mapping CSV query result. They are never inferred, paraphrased, summarised, truncated, or filled from memory or context.

**If a CSV field is empty or null → output field is blank. Never substitute.**
**If a CSV field was not retrieved → STOP. Re-query before proceeding. Do not fill from memory.**

### Build a UID Lookup Dict Immediately After the Step 2 Query

```python
rubric_rows = {row['uid']: row for row in query_results}
```

All subsequent row field population reads from `rubric_rows[uid]` — never from memory.

### TownSq Capability Is Read-Only

Column 12 is copied from `rubric_rows[uid]['townsq_capability_what_townsq_supports_today']`. It is **never** rewritten, paraphrased, or replaced with content from a data product search result. Data product searches supply branch/transcript evidence only.

### Every Answer Is Bound to Its UID

`branch_answer`, `classification`, `assessor_notes`, and `proximity` must correspond to the **specific question in col 10 for that UID**. Before building any batch, verify:

```
row['discovery_question'] == rubric_rows[uid]['exact_master_rubric_question']
```

If they do not match exactly: set `classification: ""`, `hitl: true`, write `[HITL: discovery_question mismatch — verify row binding before classifying]` in assessor_notes.

### Mandatory Pre-Build Verification

Before every `execute_code` batch call, confirm per-row:
- `uid` — exact copy from `rubric_rows[uid]['uid']`
- `dimension` — exact copy from `rubric_rows[uid]['dimension']`
- `discovery_question` — exact copy from `rubric_rows[uid]['exact_master_rubric_question']`
- `townsq_capability` — exact copy from `rubric_rows[uid]['townsq_capability_what_townsq_supports_today']`
- `branch_answer` — source line references this UID's question, not another's

If any check fails: correct from `rubric_rows[uid]` or flag HITL. Never build with mismatched metadata.

---

## Greg-Approved Domain Rules (Highest Priority)

Apply **before** the decision ladder. Confirmed by Greg Hamm, Sept 14–21, 2026.

### GR-1: Integration = AC, Not FB
If a capability is delivered through a supported Associa integration — **StrongRoom** (AP/workflow), **VendorSmart/VendorSpark** (cache management, payables), **Stripe** (payments) — classify as **AC**, not FB. Only classify FB if Greg has explicitly named the specific sub-feature as a gap.

### GR-2: Community Management Context Only
All classifications must be scoped to HOA/community management. Not commercial business client context.

### GR-3: StrongRoom vs. Native Vantaca vs. VendorSmart
Three distinct systems. Always name the system explicitly in every TOWNSQ line. StrongRoom to StrongRoom = AC.

### GR-4: Exception Automation = FB on Top of an AC Base
Base process = AC. Automated exception surfacing on top = separate FB. Classify AC; add `[GR-4: exception automation FB gap — <description>]` in notes.

### GR-5: Third-Party Portal Retirement = Always FB
Retiring and replacing an external access portal = always FB.

### GR-6: No "Non-Negotiable" Language
Never use this phrase anywhere in output.

### GR-7: Greg-Confirmed Topic Precedents

| Topic | Classification |
|---|---|
| Billing frequencies (monthly/quarterly/semi-annual/annual) | AC |
| Billing start dates / fiscal year flexibility | AC |
| Homeowner self-service payment | AC |
| AR exception handling / manual review workflow | AC |
| Financial statement distribution & tracking | AC |
| Chargebacks (90-day dispute window) | AC |
| Assessment mid-year changes | AC |
| Direct debit consent & recurring charge updates | AC + PC (comms) |
| StrongRoom AP workflow (StrongRoom to StrongRoom) | AC |
| VendorSmart cache management module | AC |
| Stop payments / voiding checks | AC (bank config) |
| Credit reporting — native platform | FB (no native capability) |
| Credit reporting — third-party integration | AC (if integration exists) |
| Third-party auditor portal (retirement required) | FB |
| Recurring charge exception automation | FB (on top of AC base) |

---

## Classification Decision Ladder

Walk in order; stop at the first test that resolves.

0. **Greg-Approved Domain Rule applies?** Use it, record `[GR-N: ...]` in Assessor Notes
1. **Either side unreadable / Not Found?** Leave Classification **blank**; write `[HITL: <reason>]` in Assessor Notes
2. **Branch explicitly doesn't do this?** `NA`
3. **Capability covered by StrongRoom, VendorSmart, or Stripe?** `AC`; record `[GR-1]`
4. **TownSq native cannot produce the outcome today?** `FB`
5. **Capability in flight / not yet live?** `FB`
6. **Only system setup needed; branch steps survive?** `AC`
7. **Branch steps/roles/approvals must change?** `PC`
8. **Base = AC but automated exception surfacing also required?** `AC`; add `[GR-4: ...]` in notes
9. **Still torn?** Leave Classification **blank**; write `[HITL: <candidates and deciding question>]` in notes

**Valid values: `PC`, `AC`, `FB`, `NA`, or blank.**
- **"HITL" is never written in the Classification column.** When a row requires human review, leave Classification blank and write `[HITL: <reason>]` in Assessor Notes.
- **Proximity is always in its own column (col 15)**, never embedded inside Assessor Notes text.
- **Improvement recommendations** go in Assessor Notes as `[RECOMMENDATION: <text>]`.

---

## Assessor Note Format

```
BRANCH: <clause from branch answer that drives the code>
TOWNSQ: <clause from TownSq capability; name system — native Vantaca / StrongRoom / VendorSmart / integration>
DELTA: <which facets differ — outcome / mechanism / actors / timing / controls / exceptions / evidence>
WHY <CODE>: <one sentence>
Also requires: <secondary config, process change, or FB automation layer — if any>
[GR-N: <Greg-Approved Rule applied>]
[HITL: <reason — only on blank-classification rows>]
[RECOMMENDATION: <improvement or upsell note — if applicable>]
Confidence: <High | Medium | Low> (<what is solid; what is not>)
```

Proximity is written in the **Proximity column (col 15)**, not inside this text.

---

## Capability Proximity Verdicts

| Verdict | Meaning | Typical pairing |
|---|---|---|
| Exact match | Facets align; drop-in | AC |
| High (~75%) | Same outcome and mechanism; minor actor or timing deltas | AC / PC |
| Moderate (~50%) | Outcome overlaps; material control, scope, or exception deltas | PC |
| Low (~25%) | Small overlap; most of the branch's need unmet or done very differently | FB / PC |
| No match | Nothing comparable on one side | FB / NA |

---

## Row Dict Schema (passed in `rows` array to execute_code)

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

---

## Workflow Summary

**Read `references/session_processing_guide.md` for the full workflow.** Summary below is for orientation only.

### Step 1 — Wait for explicit user input
Do not proceed until the user provides ALL of:
- A session number (or range), AND
- Confirmation that the transcript and mapping CSV are in the attached data product(s)

Never call any script at startup or on context load.

### Step 2 — Query the Session Mapping CSV
Call `getSpreadsheetInfo` first to confirm column names. Then query:

```sql
SELECT session, planned_question_id, uid, qid, capability, dimension, priority,
       exact_master_rubric_question, townsq_capability_what_townsq_supports_today
FROM data
WHERE session = <N>
LIMIT 100
```

Build rubric_rows dict immediately:
```python
rubric_rows = {row['uid']: row for row in query_results}
```

### Step 2b — Load Greg-Approved Classifications
`read_skill_resource("references/greg_approved_classifications.md")`

### Step 3 — Load rubric index
`read_skill_resource("references/rubric_index.json")`

### Step 3b — Load xlsx builder source ⚠️ CRITICAL
`read_skill_resource("references/xlsx_builder.py")`

Store the returned content string. Embed it verbatim in every `execute_code` call. Do not re-write it; do not paraphrase it. The builder is already tested and correct.

### Step 4 — Resolve session scope
Call `resolve_session_scope_v2.py` via `run_skill_script`. Confirm 100% resolved before proceeding.

### Step 5 — Fetch transcript evidence (batched by topic)
Make 2–4 targeted `get_information_from_dataProduct` calls, each covering a distinct topic cluster.

### Step 6 — Extract branch answers
For each row, ground the answer in transcript evidence. Cite speaker + timestamp + system tag in every Source line.

### Step 7 — Classify each row
Apply GR-1 through GR-7 first, then decision ladder. `classification` must be `"PC"`, `"AC"`, `"FB"`, `"NA"`, or `""`.

### Step 8 — Build xlsx via execute_code

```python
# execute_code — code parameter:
<full content of references/xlsx_builder.py>

with open("input.json") as f:
    build(json.load(f))

# execute_code — input parameter:
{
  "branch": "CAMS",
  "session": 6,
  "run": 1,
  "rows": [ ...up to 20 row dicts... ]
}
```

After execute_code returns, check `outputFiles`:
- If non-empty → use `outputFiles[0].blobKey` as `content` in `render_content`
- If empty → STOP. Do not attempt base64 fallback. Report failure.

### Step 9 — Report
Minimal chat output (< 5KB): counts by classification, HITL list, file list.

---

## Hard Rules

- **Never call build_assessment_batch.py via run_skill_script for delivery** — outputFiles will be empty.
- **Never pass stdout base64 to render_content** — truncation produces corrupt/empty files above ~15KB.
- **Always use execute_code + outputFiles blobKey** for xlsx delivery.
- **Always read references/xlsx_builder.py before building any batch** — embed it verbatim, do not rewrite it.
- **Never call any script at startup** or before the user provides session data.
- **Batch at ≤ 20 rows** per execute_code call.
- **classification must be "PC", "AC", "FB", "NA", or ""** — never "HITL".
- **HITL rows:** set `"classification": ""` and `"hitl": true`.
- **Never use "non-negotiable"** in any assessor note (GR-6).
- **Never derive Dimension, Discovery Question, TownSq Capability, or any other metadata field** — copy verbatim from `rubric_rows[uid]`; if not retrieved, re-query before proceeding.
- **Never allow a branch answer written for one UID to be used for a different UID** — verify (uid, discovery_question) binding before every batch build.
- **Chat output must stay < 5KB** — all detailed data goes in xlsx files.