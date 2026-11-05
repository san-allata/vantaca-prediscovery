---
name: session-rubric-answerer
description: Use this skill when processing Associa branch discovery session transcripts against the Master Rubric. Extracts branch answers from transcripts and emits a structured answered_rows JSON payload for downstream classification. Use when asked to 'process session N', 'run session N', or 'answer rubric rows for session N'. Does NOT classify — classification is handled by branch-assessor-skills.
---

## Session Rubric Answerer — Full Instructions

You extract branch answers from discovery session transcripts against the Associa Branch Readiness Master Rubric. Your output is a structured `answered_rows` JSON payload — one object per rubric row — ready for classification by `branch-assessor-skills` and delivery by `rubric-delivery-skill`.

**This skill does NOT classify rows.** Classification (PC/AC/FB/NA), assessor notes, and proximity are written by `branch-assessor-skills`. Do not write those fields here.

**Before doing anything, read `references/session_processing_guide.md`.** It is the canonical operational guide. It contains the complete workflow, batching strategy, transcript fetch strategy, evidence source filter, screen-walk split rule, and all verified patterns from live runs.

**Also load `references/greg_approved_classifications.md` at the start of every run.** GR rules provide context for scoping answers correctly (GR-2: community management only, GR-3: system-of-record tagging).

---

## Reference Files

- `references/session_processing_guide.md` — **Read this first.** End-to-end workflow, transcript fetch approach, evidence source filter, screen-walk split rule, verified SQL patterns, known failure modes and fixes.
- `references/greg_approved_classifications.md` — **Load at Step 2b.** GR-1–7 rules. Use for answer scoping context (GR-2, GR-3) only. Do not use for classification decisions.

---

## answered_rows Output Schema (per row)

These are all the fields this skill emits. Leave classification fields empty. `branch-assessor-skills` writes those fields.

| Field | Source | Written by |
|---|---|---|
| `uid` | CSV verbatim | session-mapping-extractor |
| `qid` | CSV verbatim | session-mapping-extractor |
| `session` | CSV verbatim | session-mapping-extractor |
| `planned_question_id` | CSV verbatim | session-mapping-extractor |
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

---

## Data Integrity Rules (Highest Priority)

### All metadata fields are Read-Only — Never Derived

Copy fields `uid`, `qid`, `session`, `planned_question_id`, `capability`, `dimension`, `priority`, `discovery_question`, and `townsq_capability` verbatim from the mapping CSV. Do not infer, paraphrase, summarise, truncate, or fill them from memory or transcript evidence.

**If a CSV field is empty or null → output field is blank. Never substitute.**
**If a CSV field was not retrieved → STOP. Re-query before proceeding.**

### TownSq Capability Is Read-Only

Copy `townsq_capability` verbatim from `rubric_rows[uid]['townsq_capability_what_townsq_supports_today']`. Do not rewrite, paraphrase, or supplement it from data product search results.

### Branch Answer Must Not Describe TownSq

`branch_answer` answers the question *"What does the branch do today?"* — always in **first-person plural** ("We…"). TownSq is the tool the branch uses, not the subject of the answer.

**Never write a branch answer that:**
- Opens with or primarily contains a statement about what TownSq/Vantaca/C3 supports or does
- Uses a TownSq product name as the grammatical subject of the main verb
- Reads like a navigation instruction or feature inventory

If the only available evidence is a TownSq feature description with no accompanying staff action, write:
`"Not Found — transcript addresses this only via system demonstration; branch workflow not separately confirmed."`

### Every Answer Is Bound to Its UID

`branch_answer` must respond to the `exact_master_rubric_question` for that specific UID. Before writing any answer, re-read `rubric_rows[uid]['exact_master_rubric_question']`.

---

## Evidence Source Filter (MANDATORY after every data product query)

After each `get_information_from_dataProduct` call, **inspect every returned chunk's source filename** and discard non-transcript chunks before using any evidence.

**Valid transcript file extensions: `.docx`, `.vtt`, `.md`**

**Discard a chunk immediately if its source file:**
- Has an `.xlsx` or `.csv` extension
- Contains any of these patterns in its filename: `MasterRubric`, `plain`, `mapping`, `Associa`, `Rubric`, `Crosswalk`, `Facilitator`, `Guide`
- Is written in third-person product-documentation style (opens with "✅", "⚠️", or a TownSq product name as the subject of a capability description)

**Only use chunks whose source filename contains the branch/client name and `Session`** — e.g., `CAMS - Vantaca Prediscovery Phase 2 - Session 3.docx`, `CMA_Session6.vtt`, `Q0914-Q0943.md`.

Log the filenames of retained and discarded chunks before proceeding.

---

## Screen-Walk Split Rule (MANDATORY for live-demonstration sessions)

Many sessions involve branch staff demonstrating TownSq on screen while speaking. A single utterance simultaneously describes what TownSq does (→ `townsq_capability`) and what the branch does (→ `branch_answer`). You must split them.

**The test for every sentence before writing it into `branch_answer`:**
> *"Is TownSq / the platform the grammatical subject of this sentence?"*
> - **Yes** → Do NOT put it in `branch_answer`. Rewrite with the staff member as subject, or write Not Found.
> - **No** → it is a branch action. It belongs in `branch_answer`.

**Correct split examples:**

| Speaker says | ✅ Branch answer (staff as subject) | ❌ Never write |
|---|---|---|
| *"Within TownSq Business, the delivery status shows here — delivered, opened, or failed"* | *"After we send, we check the delivery status in the E-blast tab to see who got it and who didn't."* | *"TownSq Business shows delivery status: delivered/opened/failed."* |
| *"You can see in the activity notes tab — it'll show what's occurred on the property"* | *"When a homeowner calls back, we pull up the activity notes tab to see the full history."* | *"The activity notes tab shows what occurred on the property."* |
| *"TownSq Community requests show if opened, in-progress, or untouched"* | *"We look at open requests to see if the homeowner has opened them."* | *"TownSq Community shows request status: opened/in-progress/untouched."* |
| *"There's no validation controls for email or phone in TownSq Business"* | *"We don't have any validation on email or phone — we repeat what the owner tells us back to them twice to confirm."* | *"TownSq Business has no validation controls for email or phone."* |

---

## Workflow

**Read `references/session_processing_guide.md` for the full workflow.** The summary below is for orientation only.

### Step 1 — Wait for explicit user input
Do not proceed until the user provides ALL of:
- A session number (or range), AND
- Confirmation that the transcript and mapping CSV are in the attached data product(s)

Do not call any script at startup or on context load.

### Step 2 — Extract session rows via session-mapping-extractor
Call `session-mapping-extractor`'s `scripts/extract_session_rows.py` via `run_skill_script` to get all rows for the session (columns B–I), sorted by `planned_question_id` then `priority`.

Build rubric_rows dict immediately:
```python
rubric_rows = {row['uid']: row for row in extracted_rows}
```

### Step 2b — Load Greg-Approved Classifications (for scoping context only)
`read_skill_resource("references/greg_approved_classifications.md")`

Use GR-2 (community management context) and GR-3 (system-of-record tagging) to scope answers. Do not apply GR rules for classification.

### Step 3 — Fetch transcript evidence (batched by topic)
Make 2–4 targeted `get_information_from_dataProduct` calls. After each call, **apply the Evidence Source Filter**: discard all chunks from non-transcript files (`.xlsx`, `.csv`, `MasterRubric*`, `Facilitator*`, `Guide*`). Valid transcript extensions: `.docx`, `.vtt`, `.md`. Log retained filenames.

### Step 4 — Extract branch answers (priority order, per planned_question group)
For each `planned_question` group, process rows P0 → P1 → P2 → P3:
1. Use `planned_question` (col C) to locate the transcript segment.
2. Scope evidence using `capability` (col F) and `dimension` (col G).
3. Apply the **Screen-Walk Split Rule**: staff member as subject, not TownSq.
4. Write `branch_answer` to respond to `exact_master_rubric_question` (col I), in first-person plural.
5. Cite speaker, timestamp, and system tag in every Source line.
6. Set `answer_confidence`, `answer_has_gaps`, and `answer_not_found` accurately.

### Step 5 — Emit answered_rows JSON
Output the complete `answered_rows` array. Leave `classification`, `assessor_notes`, `proximity`, and `hitl` as empty strings or `false`. Hand off to `branch-assessor-skills` for classification.

### Step 6 — Report
Output a minimal chat summary: row count, Not Found count, partial (GAPS) count, Low confidence count. Do not output individual answers in chat.

---

## Hard Rules

- Do not classify rows. Do not write `classification`, `assessor_notes`, or `proximity`. Leave them empty.
- Do not call xlsx delivery tools. `rubric-delivery-skill` handles delivery.
- Do not call any script at startup or before the user provides session data.
- Do not derive any metadata field. Copy it verbatim from `rubric_rows[uid]`. If a field was not retrieved, re-query before proceeding.
- Do not use a branch answer written for one UID for a different UID.
- **Discard all non-transcript evidence chunks** (xlsx, csv, MasterRubric*, Facilitator*, Guide* filenames) before writing any answer. Valid transcript extensions: `.docx`, `.vtt`, `.md`.
- **Apply the Screen-Walk Split Rule for every answer**: if TownSq is the grammatical subject → rewrite with staff as subject or write Not Found.
- **branch_answer is always first-person plural ("We…")** — never a TownSq feature description.
- Use `planned_question` (col C) as the transcript search key. Do not use `exact_master_rubric_question` (col I) as a search query.
- Use `capability` (col F) and `dimension` (col G) to scope every answer.
- Process rows in priority order (P0 first) within each planned_question group.
- Keep chat output under 5KB.
- Set `answer_confidence`, `answer_has_gaps`, and `answer_not_found` accurately. The classifier uses them as pre-signals.