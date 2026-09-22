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
- `scripts/build_assessment_batch.py` — **Canonical production xlsx builder.** Handles ≤30-row batches, formats colors/freeze/wrap/column widths. Use via `execute_code` (Python), passing rows as `input` JSON parameter. Reads from `input.json`, writes `Assessment_Run<N>_<CapGroup>.xlsx`. **This is the ONLY script to use for new production builds.**
- `scripts/build_assessment_snapshot_v2.py` — **DEPRECATED.** Do not use for production. Causes payload overflow with 50+ rows. Kept only for backward compatibility with old automation.
- `scripts/build_assessment_snapshot.py` — **DEPRECATED.** Original script. Do not modify. Use `build_assessment_batch.py` instead.
- `assets/MasterRubricTemplateWithAssociaAnswers_FB.xlsx` — Master Rubric asset (read-only reference).

### Integrated Skills
- **`branch-assessor-skill`**: Used in Step 7 to classify each answer per the decision ladder (PC/AC/FB/NA). Now includes GR-1 through GR-7 Greg-Approved Domain Rules.
- **`rubric-answer-extractor-skill`**: Used in Step 6 to ground each answer in transcript evidence. Provides answer + Source line + BACKLOGS tracking.

Do not call these skills directly; they are invoked internally during Steps 6–7.

---

## Critical Note on Reference Guide Maintenance

**`references/session_processing_guide.md` is the canonical operational guide.** This SKILL.md is a summary only. If anything here conflicts with the guide, the guide wins.

**Keep in sync:** The guide should be updated whenever:
- A new SQL pattern is verified
- A failure mode is discovered and fixed
- Batching rules change
- Script versions change
- New Greg/SME classification rulings are confirmed → add to `references/greg_approved_classifications.md`

Review and sync both documents during monthly maintenance cycles.

---

## Workflow Summary

**Read `references/session_processing_guide.md` for the full workflow.** The summary below is for quick orientation only.

### Step 1 — Wait for explicit user input
Do not proceed until the user provides ALL of:
- A session number (or range), AND
- Confirmation that the transcript and mapping CSV are in the attached data product(s)

If only one is provided, ask for the other before doing anything. Never call any script at startup or on context load.

### Step 2 — Query the Session Mapping CSV
Call `getSpreadsheetInfo` first to confirm column names. Then use `executeQuery` with the exact pattern from the guide. Do NOT use `SELECT *` with a WHERE clause that filters on a column name you haven't verified.

```sql
SELECT session, planned_question_id, uid, qid, capability, dimension, priority,
       exact_master_rubric_question
FROM data
WHERE session = <N>
LIMIT 100
```

If the result set is empty, stop and report: "No mapping rows found for session N."

### Step 2b — Load Greg-Approved Classifications
Call `read_skill_resource` with `resourcePath: "references/greg_approved_classifications.md"` and hold in context. Check this file before extracting or classifying any row whose topic may match a Greg-confirmed ruling.

### Step 3 — Load rubric index
Call `read_skill_resource` with `resourcePath: "references/rubric_index.json"` and parse the result as JSON.

### Step 4 — Resolve session scope
Call `resolve_session_scope_v2.py` with mapping rows + rubric index via `run_skill_script`. Confirm 100% of rows resolved before proceeding. If any rows are unresolved, report them and stop.

### Step 5 — Fetch transcript evidence (batched by topic)
Do NOT attempt to load the full VTT in one `get_information_from_dataProduct` call — the retrieval system returns chunked results. Instead make **2–4 targeted calls**, each covering a distinct topic cluster. Hold all retrieved evidence in context. If no transcript is found, stop and report: "Transcript not provided or not found."

**Context rule (GR-2):** Scope all evidence interpretation to **HOA/community management** context. If evidence is from a business-client context, note the mismatch.

**System tagging (GR-3):** Tag each piece of evidence with the system it refers to: `[native Vantaca]`, `[StrongRoom]`, `[VendorSmart]`, `[Stripe]`, `[other]`.

### Step 6 — Extract branch answers
For each resolved row:
1. Check `greg_approved_classifications.md` — if topic matches a Greg ruling, use it as authoritative context
2. Locate the branch's answer in the retrieved transcript evidence
3. Tag the system of record in the Source line
4. Use the evidence-grounding discipline from `rubric-answer-extractor-skill`:
   - **Answer:** [text extracted from transcript]
   - **Source:** [filename, speaker, timestamp, system-of-record tag]
   - **GAPS:** [any partial answer notes]
   - **Not Found:** [when transcript is silent on this topic]

Cite speaker and timestamp for every answer. Never use column I (TownSq Capability) as evidence for the branch answer.

**HITL threshold (tightened):** When the transcript is silent AND the TownSq capability references an integration rather than native Vantaca, the answer is unconfirmed — write "Not Found" and leave Classification blank; record `[HITL: integration applicability unconfirmed — transcript silent]` in Assessor Notes.

### Step 7 — Classify each row

**Check `greg_approved_classifications.md` first.** If the topic matches a Greg-confirmed ruling, apply it and record the GR-N reference in assessor notes.

Apply the updated decision ladder:
0. Greg-Approved Domain Rule applies? → Use it, record GR-N
1. Either side unreadable / Not Found? → Leave Classification **blank**; write `[HITL: <reason>]` in Assessor Notes
2. Branch explicitly doesn't do this? → NA
3. **Capability covered by supported Associa integration (StrongRoom, VendorSmart, Stripe)?** → **AC** (not FB). Record `[GR-1]`
4. TownSq cannot produce the outcome today? → FB
5. Capability in flight / not yet live? → FB
6. Only system setup needed; branch steps survive? → AC
7. Branch steps/roles/approvals must change? → PC
8. **Base = AC but automated exception surfacing also required?** → AC; add `[GR-4: exception automation FB gap — <description>]` in notes
9. Still torn? → Leave Classification **blank**; write `[HITL: <candidates and deciding question>]` in Assessor Notes

**Valid Classification values: `PC`, `AC`, `FB`, `NA` only.** HITL is never written in the Classification column — it goes in Assessor Notes as `[HITL: <reason>]`.

**Revised FB-bias:** Applies only when native Vantaca cannot support the outcome AND no integration covers it. Do NOT default to FB for integration-covered items (GR-1).

**No "non-negotiable" language** in any assessor note (GR-6).

**Improvement recommendations:** If you identify a potential improvement to a branch process or an upsell opportunity, add `[RECOMMENDATION: <text>]` in Assessor Notes. Do not create a separate column or file for this.

### Step 8 — Build Assessment xlsx (BATCHED)
**This is the critical step where previous attempts failed. Follow the batching rules exactly.**

See `references/session_processing_guide.md` → "Batched Build Strategy" for full detail. Summary:
- Split rows into capability-group batches of ≤ 30 rows each
- For each batch: call `execute_code` (Python) passing the rows as the `input` JSON parameter
- Use `scripts/build_assessment_batch.py` ONLY — it handles all formatting (colors, freeze, wrap, column widths)
- Deliver each batch file as a download via `render_content`
- **Never pass all 100 rows in a single `execute_code` call** — this causes payload overflow / timeout
- **If `execute_code` times out:** reduce batch size from 30 to 20 rows and retry

### Step 9 — Report (minimal, <5KB chat output)
Output ONLY the following to keep chat output under 5KB (DynamoDB compliance):

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
- Assessment_Run1_<CapGroup>.xlsx: [count] rows
- Assessment_Run2_<CapGroup>.xlsx: [count] rows
- [...]
```

**Do NOT output:**
- Individual answer text or source citations (all in workbook)
- Mapping details or per-session breakdowns
- Unresolved question lists or explanations
- Search queries, batch processing logs, or progress updates
- Explanations or observations

(All detailed data stays in the xlsx files. Chat is metadata only.)

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
| 13 | Classification | Valid values: `PC`, `AC`, `FB`, `NA`, or **blank** (for HITL rows). Never write "HITL" here. |
| 14 | Assessor Notes | Free text. Contains `[HITL: <reason>]` for blank-classification rows, `[RECOMMENDATION: <text>]` for improvement suggestions, `[GR-N: <rule>]` for Greg-rule references. |
| 15 | Proximity | **Separate column.** Values: `Exact match`, `High (~75%)`, `Moderate (~50%)`, `Low (~25%)`, `No match`. Blank for HITL rows. |

---

## Hard Fast-Fail Rules

- **Never call any script at startup, on context load, or before the user provides data.**
- **Never attempt to pass 50+ rows as a single `execute_code` or `run_skill_script` payload.** Batch at ≤ 30 rows.
- **Use ONLY `scripts/build_assessment_batch.py` for production builds.**
- **Never skip `getSpreadsheetInfo` before querying a spreadsheet.**
- **Chat output must be < 5KB.**
- **Never write "HITL" in the Classification column.** Leave it blank and write `[HITL: <reason>]` in Assessor Notes.
- **Never classify integration-covered items as FB without explicit SME confirmation of a gap.** (GR-1)
- **Never use "non-negotiable" in any assessor note.** (GR-6)
- If mapping rows are empty or missing → report and stop.
- If transcript is empty → report "No transcript provided" and stop.
- If `execute_code` times out → reduce batch size and retry.

---

## Troubleshooting

### Mapping Query Failures
- **"Column 'session' not found"** → Call `getSpreadsheetInfo` first to confirm exact column names.
- **Empty result set** → Check session number; verify it is numeric and within range.
- **Timeout on query** → Add `LIMIT 100`.

### Transcript Retrieval Failures
- **"No transcript found"** → Confirm filename and location with user.
- **Chunked/partial results** → Expected. Make 2–4 targeted calls per topic cluster.
- **"Retrieval system error"** → Retry with reduced scope.

### Script Execution Failures
- **Payload overflow / timeout** → Reduce batch size from 30 to 20 rows; retry.
- **"Column index out of range"** → Verify all 15 required columns exist in input rows.
- **Output file not created** → Verify `openpyxl` is available (Python 3.8+).

### Classification Issues
- **"Too many FBs generated"** → Check GR-1: are these covered by StrongRoom, VendorSmart, or Stripe? If yes, reclassify as AC.
- **"HITL in Classification column"** → Move to Assessor Notes as `[HITL: <reason>]`; leave Classification blank.
- **Business vs. community context mismatch** → Check GR-2.
- **StrongRoom/Vantaca conflation** → Check GR-3; tag system of record in every Source line.

### Script Logging Suppression
Scripts must output ONLY final results (file paths, counts). Remove any `print()` statements logging progress, batch details, or explanations.

---

## Tool and Data Rules
- **Never open/render documents directly** — all reading happens through `executeQuery`/`getSpreadsheetInfo` or plain-text reads of transcripts.
- **One session's rows, one session's transcript** — never mix sources across sessions.
- **No write-back, ever** — the Master Rubric data product file and any chat-uploaded files are never modified. The only output is the new standalone workbook(s).
- **Row count integrity is mandatory**: the delivered xlsx row count must equal the mapping row count.
- Cite the transcript filename (and speaker/timestamp locator when available) as the source for every new answer.
- **Always tag system of record** in every Source line and TOWNSQ assessor note line.