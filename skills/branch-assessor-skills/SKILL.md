---
name: branch-assessor-skills
description: Use this skill to classify rubric rows as PC/AC/FB/NA, assign proximity verdicts, and write auditable assessor notes. Accepts an answered_rows JSON payload from session-rubric-answerer. Apply Greg-Approved Domain Rules (GR-1 through GR-7) before the decision ladder. Emit a classified_rows JSON payload for rubric-delivery-skill. Use when asked to 'classify session N rows', 'run classification', or after session-rubric-answerer has completed its answering pass.
---

# Branch Readiness Classifier

Compare the branch's **current state** (`branch_answer`) against TownSq's **actual capability** (`townsq_capability`) and record the gap between them as a `classification`, `assessor_notes`, and `proximity` in the output `classified_rows` JSON.

This is not text similarity. Two answers can share almost no vocabulary and be an exact functional match, or read almost identically and hide a feature gap. What is being judged is whether the branch's required outcome can be produced by TownSq, and if so, what has to change to get there.

**Input:** `answered_rows` JSON payload from `session-rubric-answerer` (one object per rubric row, with `branch_answer`, `townsq_capability`, and 3 pre-signal fields).
**Output:** `classified_rows` JSON payload — same rows with `classification`, `assessor_notes`, `proximity`, and `hitl` filled in. Pass to `rubric-delivery-skill` for xlsx delivery.

---

## Input Contract — answered_rows fields

Read these fields from each incoming row. Never re-derive them.

| Field | Type | Use |
|---|---|---|
| `uid` | string | Primary key — all output rows keyed by this |
| `capability` | string | Group rows for consistency pass |
| `dimension` | string | Facet context for classification |
| `discovery_question` | string | Question being classified |
| `branch_answer` | string | **PRIMARY input** — what the branch does today |
| `townsq_capability` | string | **PRIMARY input** — what TownSq supports today |
| `answer_confidence` | High/Medium/Low | Pre-signal: Low → auto-HITL unless GR-7 applies |
| `answer_has_gaps` | bool | Pre-signal: true + Outcome/Exceptions gap → proximity blank |
| `answer_not_found` | bool | Pre-signal: true → classification = "", hitl = true, skip ladder |

All other fields (`qid`, `session`, `planned_question_id`, `domain`, `cap_num`, `priority`, `townsq_capability`) are read-only pass-through — copy verbatim to output, never modify.

### Pre-signal verification (mandatory)

The 3 pre-signal fields are AI-written by the answering skill. Before trusting them, re-verify:
- `answer_not_found`: confirm `branch_answer` starts with `"Not Found"` — if mismatch, use the text, not the flag
- `answer_has_gaps`: confirm `branch_answer` contains `"GAPS:"` — if mismatch, use the text
- `answer_confidence`: treat as a hint; override with your own judgment when evidence is clearly stronger or weaker

---

## ⚠️ Greg-Approved Domain Rules (Highest Priority)

Load `references/greg_approved_classifications.md` at the start of every classification run. These rules override the decision ladder for the topics they cover.

### GR-1: Integration = AC, Not FB
Capabilities delivered through StrongRoom, VendorSmart/VendorSpark, Stripe, or other Associa-sanctioned integrations → **AC**, not FB. Record `[GR-1]` in notes.

### GR-2: Community Management Context Only
Scope all classifications to HOA/community management. Not commercial business client context.

### GR-3: StrongRoom ≠ Native Vantaca ≠ VendorSmart
Always name the system explicitly in every TOWNSQ line. StrongRoom → StrongRoom = AC.

### GR-4: Exception Automation = FB on Top of an AC Base
Base process = AC. Automated exception surfacing = separate FB. Classify AC; add `[GR-4: exception automation FB gap — <description>]` in notes.

### GR-5: Third-Party Portal Retirement = Always FB

### GR-6: No "Non-Negotiable" Language
Never use this phrase anywhere in output.

### GR-7: Greg-Confirmed Topic Precedents
See `references/greg_approved_classifications.md` for the full table. It is the single source of truth — do not rely on any inline copy.

---

## Pre-Signal Classification Rules

Apply these BEFORE the decision ladder.

| Pre-signal | Rule |
|---|---|
| `answer_not_found == true` | Set `classification: ""`, `hitl: true`. Write `[HITL: Not Found — transcript silent on this dimension]`. Skip the ladder entirely. |
| `answer_confidence == "Low"` | Set `classification: ""`, `hitl: true`. Write `[HITL: Low confidence answer — verify evidence before classifying]`. Skip the ladder. **Exception:** if a GR-7 ruling unambiguously covers this topic, apply the ruling and record `[GR-7: <topic>]` instead of HITL. |
| `answer_has_gaps == true` AND gap covers Outcome or Exceptions facet | Leave `proximity` blank. Write `[HITL: proximity undetermined — answer has material gaps in Outcome or Exceptions]` in `assessor_notes`. Still classify if enough evidence exists. |

---

## Method: Decompose, Then Compare Facet by Facet

Do not compare paragraph to paragraph. Reduce each side to these 8 facets and note which ones differ. The classification falls out of **which** facets diverge, not how much the text differs.

| Facet | Question |
|---|---|
| **Outcome** | What business result is produced? |
| **System of record** | Where does the authoritative data live? (native Vantaca / StrongRoom / VendorSmart / other) |
| **Mechanism** | Automated, batch, manual, integration, import? |
| **Actors** | Who performs and who approves — roles, not names |
| **Trigger & timing** | Event-driven, scheduled, monthly close, on demand? |
| **Controls** | Approvals, thresholds, segregation of duties, dual sign-off |
| **Exceptions** | NSF, reversals, mid-year switches, legal hold, edge cases; automated exception surfacing? |
| **Evidence** | What audit trail or artifact is produced? |

Divergence in **Outcome** or **Exceptions** → FB. Divergence in **Actors, Timing, or Controls** with outcome intact → PC. Convergence on everything except **Mechanism setup** → AC.

> Always name the system explicitly in the TOWNSQ facet: `[native Vantaca]`, `[StrongRoom]`, `[VendorSmart]`, `[Stripe]`, `[other integration]`.

---

## Decision Ladder

Walk in order; stop at the first test that resolves.

0. **Apply pre-signal rules first** (see above)
1. **Greg-Approved Domain Rule applies?** → Use it, record `[GR-N: ...]` in notes
2. **Either side unreadable?** → Classification `""`, `hitl: true`, write `[HITL: <reason>]`
3. **Branch explicitly doesn't do this?** → `NA`
4. **Capability covered by StrongRoom, VendorSmart, or Stripe?** → `AC`, record `[GR-1]`
5. **TownSq native cannot produce the outcome today?** → `FB`
6. **Capability in flight / not yet live?** → `FB`; name dependency and date
7. **Facet check:** Only Mechanism diverges; branch steps, roles, timing survive → `AC`
8. **Facet check:** Actors, Controls, or Timing diverge → `PC`
9. **Base = AC but automated exception surfacing also required?** → `AC`; add `[GR-4: ...]`
10. **Still torn?** → Classification `""`, `hitl: true`, write `[HITL: <candidates and deciding question>]`

**Valid values: `"PC"`, `"AC"`, `"FB"`, `"NA"`, or `""`.**
`"HITL"` is **never** a valid classification value. When a row requires human review, leave classification blank and write `[HITL: <reason>]` in assessor_notes.

### Dominant-Blocker Rule (AC + PC co-exist)

Most real rows need both a configuration AND a behavior change. The rubric takes one code — assign the code for the change that **blocks go-live if it does not happen**, and record the other in assessor_notes as `Also requires: <config or process change>`.

### FB Bias Rule

When TownSq native capability is absent **and** no supported integration covers the gap → classify **FB**. Do NOT classify FB solely because native Vantaca lacks the capability — check GR-1 first.

### NA Requires Positive Evidence

`NA` removes the row from the readiness denominator. Silence is not NA — require a positive statement in `branch_answer` that the branch does not do this or that it does not apply.

---

## Capability Proximity Verdict

Every classified row gets one, judged from **facet overlap** — not text similarity, not the TownSq capability prefix.

| Verdict | Meaning | Typical pairing |
|---|---|---|
| Exact match | All facets align; drop-in | AC |
| High (~75%) | Same outcome and mechanism; minor actor or timing deltas | AC / PC |
| Moderate (~50%) | Outcome overlaps; material control, scope, or exception deltas | PC |
| Low (~25%) | Small overlap; most of the branch's need unmet or done very differently | FB / PC |
| No match | Nothing comparable on one side | FB / NA |
| *(blank)* | HITL row, or answer_has_gaps covers Outcome/Exceptions | — |

---

## Assessor Note Format

```
BRANCH: <clause from branch_answer that drives the code>
TOWNSQ: <clause from townsq_capability; name system — native Vantaca / StrongRoom / VendorSmart / integration>
DELTA: <which facets differ — outcome / mechanism / actors / timing / controls / exceptions / evidence>
WHY <CODE>: <one sentence>
Also requires: <secondary config, process change, or FB automation layer — if any>
[GR-N: <Greg-Approved Rule applied>]
[HITL: <reason — only on blank-classification rows>]
[RECOMMENDATION: <improvement or upsell note — if applicable>]
Confidence: <High | Medium | Low> (<what is solid; what is not>)
```

Proximity is written in the **proximity field**, never embedded inside assessor_notes.

---

## Confidence Level (in assessor_notes)

| Level | When |
|---|---|
| High | GR rule applies with clear match, or both sides unambiguous and facets align well |
| Medium | One side partially ambiguous, or minor inference required |
| Low | Significant ambiguity, speculation, or conflicting signals — consider HITL instead |

---

## Execution Workflow

### Step 1 — Load Greg-Approved Classifications
`read_skill_resource("references/greg_approved_classifications.md")`

Hold in context for the full classification run.

### Step 2 — Receive answered_rows (in capability-group batches, ≤ 20 rows)

Accept the answered_rows payload from `session-rubric-answerer` in the same ≤ 20-row capability-group batches used for delivery. **Never receive the full session in one call** — context window fragmentation risk.

Re-verify all 3 pre-signals by scanning `branch_answer` text before using the flags.

### Step 3 — Apply pre-signal rules
For each row, apply `answer_not_found`, `answer_confidence`, and `answer_has_gaps` rules before touching the decision ladder.

### Step 4 — Classify by capability group
Group rows by `capability` name. Classify all rows in a capability together — never row-by-row in file order.

### Step 5 — Consistency pass (mandatory, per capability)
Before finalising any batch, re-read all rows in the same capability side by side. Materially identical (`branch_answer`, `townsq_capability`) pairs must carry identical classification and proximity codes. Row-at-a-time classification drifts — the consistency pass catches it. Log any corrections.

### Step 6 — Emit classified_rows JSON
Output `classified_rows` array: each row from `answered_rows` with `classification`, `assessor_notes`, `proximity`, and `hitl` filled in. All other fields copied verbatim from input.

Pass to `rubric-delivery-skill` for xlsx build and delivery.

### Step 7 — Report
Minimal chat output (< 5KB): counts by classification, HITL list with reasons, consistency corrections made.

---

## classified_rows Output Schema (per row)

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
  "answer_confidence": "High",
  "answer_has_gaps": false,
  "answer_not_found": false,
  "classification": "AC",
  "assessor_notes": "BRANCH: ...\nTOWNSQ: [native Vantaca] ...\nDELTA: ...\nWHY AC: ...\nConfidence: High",
  "proximity": "High (~75%)",
  "hitl": false
}
```

**`classification`**: `"PC"` / `"AC"` / `"FB"` / `"NA"` / `""`. **Never `"HITL"`.**
**`proximity`**: `"Exact match"` / `"High (~75%)"` / `"Moderate (~50%)"` / `"Low (~25%)"` / `"No match"` / `""`.
**`hitl`**: `true` for blank-classification rows only.

---

## Hard Rules

- **Never fetch transcript evidence.** The answering skill has already done this — branch_answer is the authoritative record.
- **Never build or deliver xlsx.** That is rubric-delivery-skill's job.
- **Never rewrite townsq_capability.** It is read-only from the input payload.
- **Always check Greg-Approved Domain Rules before applying the decision ladder.**
- **Always run the per-capability consistency pass** before emitting classified_rows.
- **Always re-verify pre-signal flags** by scanning branch_answer text — treat flags as hints, not ground truth.
- **Receive rows in batches of ≤ 20** — never the full session in one call.
- **Never use "non-negotiable"** anywhere in output (GR-6).
- **Always name the system of record** in every TOWNSQ line.
- **classification must be "PC", "AC", "FB", "NA", or ""** — never "HITL".
- **Proximity must be in the proximity field** — never embedded in assessor_notes.
- **Chat output must stay < 5KB.**