---
name: session-rubric-answerer
description: Use this skill when processing Associa branch discovery session transcripts against the Master Rubric. Extracts branch answers from transcripts and emits a structured answered_rows JSON payload for downstream classification. Use when asked to 'process session N', 'run session N', or 'answer rubric rows for session N'. Does NOT classify — classification is handled by branch-assessor-skills.
---

## Session Rubric Answerer — Full Instructions

You extract branch answers from discovery session transcripts against the Associa Branch Readiness Master Rubric. Your output is a structured `answered_rows` JSON payload — one object per rubric row — ready for classification by `branch-assessor-skills` and delivery by `rubric-delivery-skill`.

**This skill does NOT classify rows.** Classification (PC/AC/FB/NA), assessor notes, and proximity are written by `branch-assessor-skills`. Do not write those fields here.

**Before doing anything, read `references/session_processing_guide.md`.** It is the canonical operational guide and contains the complete workflow, batching strategy, transcript fetch strategy, and all verified patterns from live runs.

**Also load `references/greg_approved_classifications.md` at the start of every run** — GR rules provide context for scoping answers correctly (e.g. GR-2: community management only, GR-3: system-of-record tagging).

---

## Reference Files & Resources

- `references/session_processing_guide.md` — **Read this first.** End-to-end workflow, transcript fetch approach, verified SQL patterns, known failure modes and fixes.
- `references/greg_approved_classifications.md` — **Load at Step 2b.** GR-1–7 rules. Used here for answer scoping context (GR-2, GR-3) only — NOT for classification decisions.
- `references/rubric_index.json` — Lightweight rubric index. Use for domain/cap_num resolution. Pass as `rubric_index` in inputData when calling scope resolution scripts.
- `scripts/resolve_session_scope_v2.py` — Resolves session mapping rows to rubric rows. Use via `run_skill_script` only.

---

## answered_rows Output Schema (per row)

These are ALL the fields this skill emits. Classification fields are left empty — they are written by `branch-assessor-skills`.

| Field | Source | Written by |
|---|---|---|
| `uid` | CSV verbatim | session-mapping-extractor |
| `qid` | CSV verbatim | session-mapping-extractor |
| `session` | CSV verbatim | session-mapping-extractor |
| `planned_question_id` | CSV verbatim | session-mapping-extractor |
| `domain` | rubric_index match | this skill |
| `cap_num` | rubric_index match | this skill |
| `capability` | CSV verbatim | session-mapping-extractor |
| `dimension` | CSV verbatim | session-mapping-extractor |
| `priority` | CSV verbatim | session-mapping-extractor |
| `discovery_question` | CSV verbatim (`exact_master_rubric_question`) | session-mapping-extractor |
| `branch_answer` | AI-written from transcript | **this skill** |
| `townsq_capability` | CSV verbatim | session-mapping-extractor |
| `answer_confidence` | AI-written | **this skill** — `High`, `Medium`, or `Low` |
| `answer_has_gaps` | AI-written | **this skill** — `true` if branch_answer contains a GAPS line |
| `answer_not_found` | AI-written | **this skill** — `true` if branch_answer starts with "Not Found" |
| `classification` | ⛔ empty string `""` | branch-assessor-skills writes this |
| `assessor_notes` | ⛔ empty string `""` | branch-assessor-skills writes this |
| `proximity` | ⛔ empty string `""` | branch-assessor-skills writes this |
| `hitl` | ⛔ `false` | branch-assessor-skills writes this |

### answer_confidence definition

| Level | When to use |
|---|---|
| `High` | Direct quote or explicit statement in transcript; speaker is unambiguous; multiple sources agree |
| `Medium` | Clear from context but not explicitly stated; single source only; or speaker qualifies the statement |
| `Low` | Partial evidence only; speaker speculates; inference at edge of explicit text; image-based with no text locator |

### answer_has_gaps

Set `true` when `branch_answer` contains a `GAPS:` line — meaning some sub-parts of `exact_master_rubric_question` were not addressed in the transcript.

### answer_not_found

Set `true` when `branch_answer` starts with `"Not Found"` — meaning the transcript was silent on this question entirely.

---

## Data Integrity Rules (Highest Priority)

### All metadata fields are Read-Only — Never Derived

Fields `uid`, `qid`, `session`, `planned_question_id`, `capability`, `dimension`, `priority`, `discovery_question`, and `townsq_capability` are sourced **exclusively** from the mapping CSV query result. Never infer, paraphrase, summarise, truncate, or fill from memory or transcript evidence.

**If a CSV field is empty or null → output field is blank. Never substitute.**
**If a CSV field was not retrieved → STOP. Re-query before proceeding.**

### Build a UID Lookup Dict Immediately After Extraction

```python
rubric_rows = {row['uid']: row for row in extracted_rows}
```

All subsequent field population reads from `rubric_rows[uid]` — never from memory.

### Every Answer Is Bound to Its UID

`branch_answer` must respond to the `exact_master_rubric_question` for **that specific UID**. Before writing any answer, re-read `rubric_rows[uid]['exact_master_rubric_question']` and confirm the transcript evidence addresses that question — not a neighbouring row's question.

### TownSq Capability Is Read-Only

`townsq_capability` is copied verbatim from `rubric_rows[uid]['townsq_capability_what_townsq_supports_today']`. Never rewrite, paraphrase, or supplement from data product search results.

---

## Transcript Evidence & Answer Extraction Rules

### Column C (planned_question) Is the Transcript Search Key

Use `planned_question` (col C) as the primary search key to locate the relevant transcript passage. The branch's spoken response to that question is the raw evidence for `branch_answer`.

Multiple rubric rows (UIDs) may share the same `planned_question` — they were answered in the same transcript segment. Extract the sub-answer relevant to each row's specific `exact_master_rubric_question` (col I).

### Columns F and G Scope the Answer

- **Column F (`capability`)** — narrows evidence to the right business domain.
- **Column G (`dimension`)** — narrows evidence to the correct facet within that capability. A broad transcript answer must be scoped to this specific dimension before writing.

### Column H (priority) Governs Processing Order

Within each `planned_question` group, process rows **P0 first, then P1, P2, P3**. When evidence is limited, allocate it to higher-priority rows first. Lower-priority rows get `Not Found + GAPS` rather than a diluted answer.

### Column I (exact_master_rubric_question) Is What Gets Answered

The `branch_answer` must respond to `exact_master_rubric_question` (col I), not to `planned_question` (col C). Col C is the search key; col I is the question to answer.

### Answer Format

```
{answer in branch voice, first-person plural}

Source: {file} [{timestamp}, {speaker}] [system: {system-of-record}]
```

For partial answers, append:
```

GAPS: {what sub-parts of exact_master_rubric_question were not addressed}
```

For not found:
```
Not Found — {brief reason scoped to this dimension}

Source: {file} (transcript reviewed for planned_question "{planned_question}"; this dimension not addressed)

GAPS: {dimension} not discussed in this session
```

---

## Workflow

**Read `references/session_processing_guide.md` for the full workflow.** Summary below is for orientation only.

### Step 1 — Wait for explicit user input
Do not proceed until the user provides ALL of:
- A session number (or range), AND
- Confirmation that the transcript and mapping CSV are in the attached data product(s)

Never call any script at startup or on context load.

### Step 2 — Extract session rows via session-mapping-extractor
Call `session-mapping-extractor`'s `scripts/extract_session_rows.py` via `run_skill_script` to get all rows for the session (columns B–I), sorted by `planned_question_id` then `priority`.

Build rubric_rows dict immediately:
```python
rubric_rows = {row['uid']: row for row in extracted_rows}
```

### Step 2b — Load Greg-Approved Classifications (for scoping context only)
`read_skill_resource("references/greg_approved_classifications.md")`

Use GR-2 (community management context) and GR-3 (system-of-record tagging) to scope answers. Do NOT apply GR rules for classification — that is branch-assessor-skills' job.

### Step 3 — Load rubric index
`read_skill_resource("references/rubric_index.json")`

Use to resolve `domain` and `cap_num` per UID.

### Step 4 — Resolve session scope
Call `resolve_session_scope_v2.py` via `run_skill_script`. Confirm 100% resolved before proceeding.

### Step 5 — Fetch transcript evidence (batched by topic)
Make 2–4 targeted `get_information_from_dataProduct` calls, each covering a distinct topic cluster. Use `planned_question` (col C) values as search keys.

### Step 6 — Extract branch answers (priority order, per planned_question group)
For each `planned_question` group, process rows P0 → P1 → P2 → P3:
1. Use `planned_question` (col C) to locate the transcript segment
2. Scope evidence using `capability` (col F) and `dimension` (col G)
3. Write `branch_answer` responding to `exact_master_rubric_question` (col I)
4. Cite speaker + timestamp + system tag in every Source line
5. Set `answer_confidence`, `answer_has_gaps`, `answer_not_found` accurately

### Step 7 — Emit answered_rows JSON
Output the complete `answered_rows` array. Leave `classification`, `assessor_notes`, `proximity`, and `hitl` as empty strings / `false`. Hand off to `branch-assessor-skills` for classification.

### Step 8 — Report
Minimal chat output: row count, Not Found count, partial (GAPS) count, Low confidence count. Do NOT output individual answers in chat.

---

## Hard Rules

- **Never classify rows.** Do not write `classification`, `assessor_notes`, or `proximity`. Leave them empty.
- **Never call xlsx delivery tools.** Delivery is handled by `rubric-delivery-skill`.
- **Never call any script at startup** or before the user provides session data.
- **Never derive any metadata field** — copy verbatim from `rubric_rows[uid]`; if not retrieved, re-query before proceeding.
- **Never allow a branch answer written for one UID to be used for a different UID.**
- **Use planned_question (col C) as transcript search key** — never use `exact_master_rubric_question` (col I) as a search query.
- **Use capability (col F) and dimension (col G) to scope every answer.**
- **Process rows in priority order (P0 first)** within each planned_question group.
- **Chat output must stay < 5KB.**
- **answer_confidence, answer_has_gaps, answer_not_found must be set accurately** — the classifier depends on them as pre-signals.