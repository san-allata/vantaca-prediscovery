---
name: rubric-classifier
description: Compare a branch's current process against the target platform's actual capability on an exported readiness-rubric JSON, and record the gap as a classification (AC / PC / FB / NA) with an auditable assessor note. Use after branch answers have been extracted. Do NOT use to write branch answers, set FB priority, or produce a readiness score.
---

# Branch Readiness Classifier

Compare `branch_answer` against `townsq_capability` and record *the gap between
them* in `classification`, with the reasoning in `assessor_notes`.

This is not text similarity. Two answers can share almost no vocabulary and be
an exact functional match, or read almost identically and hide a feature gap.
What is judged is whether the branch's required outcome can be produced by the
platform, and if so, what has to change to get there.

Branch-agnostic and revision-agnostic. Every quantity is measured at runtime by
`plan.py`; nothing is assumed.

## What you write, and only that

| Field | Role |
|---|---|
| `classification` | **`AC` / `PC` / `FB` / `NA`**, or left null for HITL |
| `assessor_notes` | the structured note, rendered by `apply.py` |
| `branch_answer`, `townsq_capability` | **inputs, read-only** |
| `fb_priority` | never write it — business decision; propose in the note |
| everything else | read-only |

Rows are keyed on `uid`. `apply.py` aborts if any other field would change.

## Reading the capability column: the prefix is a hypothesis, not the evidence

`plan.py` profiles the actual marker distribution and prints it. On the
reference rubric, prose with no prefix was the **largest** category, so a
prefix-keyed classifier would have had no signal on most rows while believing it
matched.

| Marker | Meaning |
|---|---|
| `Native —` | out of the box |
| `After config —` | supported once configured during onboarding |
| `Partial —` | some of the dimension supported; a gap remains |
| `Change in-progress —` | being built now |
| `Not supported —` | no capability today |
| `TBD` / bare stub | not answered — **blocked, do not classify** |

Four patterns defeat prefix matching. Expect all four:

- **No prefix at all.** Read the prose. There is no shortcut.
- **Speaker-initial prefixes.** Two or three letters or an org name followed by
  `-` or `:`. These encode *who said it*, not the support level. The verdict is
  usually inside the prose: "still in development", "not currently supported".
  48 rows on the reference rubric.
- **Bare-prefix stubs.** A cell containing only `Change in-progress` is not a
  capability statement. Blocked, exactly like `TBD`. Detected by length.
- **Classification leakage.** Occasionally the SME writes the verdict itself
  into the capability column, sometimes with a priority attached. Treat it as an
  SME-asserted classification to **confirm and cite**, not re-derive, and say so
  in the note. `plan.py` flags these.

Trailing `✓` and `~` are an undocumented SME confidence annotation, not a
support level. `✓` supports High confidence; `~` and "confirm with product" cap
it at Medium.

## Method: decompose, then compare facet by facet

Do not compare paragraph to paragraph. Reduce each side to these facets as
**controlled tokens plus a cited clause from its own column**. Free-prose facets
just relocate the paraphrase problem one level down.

| Facet | Question |
|---|---|
| `outcome` | what business result is produced? |
| `system_of_record` | where does the authoritative data live? |
| `mechanism` | automated, batch, manual, integration, import? |
| `actors` | who performs and who approves — roles, not names |
| `trigger_timing` | event-driven, scheduled, monthly close, on demand? |
| `controls` | approvals, thresholds, segregation of duties, dual sign-off |
| `exceptions` | reversals, mid-year switches, edge cases |
| `evidence` | what audit trail or artefact is produced? |

Divergence in **outcome** or **exceptions** points to FB. Divergence in
**actors, timing or controls** with the outcome intact points to PC. Convergence
on everything except **mechanism setup** points to AC.

Then answer two **directed** entailment questions and record both. Never ask
"are these similar?" — similarity cannot represent an asymmetric gap.

1. Can the platform produce the branch's stated outcome? (No → FB)
2. Does the branch depend on anything the platform's answer does not cover?
   (Yes → FB or PC depending on the facet)

## Decision ladder

Walk in order; stop at the first test that resolves.

1. **Either side unreadable?** No branch answer, or capability is `TBD` or a
   stub → **blocked**, no code. Report; do not classify.
2. **Does the branch do this at all?** A positive statement that they don't, or
   that it doesn't apply → **NA**.
3. **Can the platform produce the required outcome today?** Evidence says no, or
   says `Partial` where the missing part covers something the branch actually
   depends on → **FB**.
4. **In flight rather than live?** "in development", "being built", "on the
   roadmap" → **FB**, unless availability before this branch's go-live is
   stated. Name the dependency and the date either way. `audit.py` enforces this
   — an AC or PC on a row whose capability text says in-development is a hard
   failure.
5. **Capability exists. Must the branch change how it works?**
   - Only the system needs setting up; steps, roles and timing survive → **AC**
   - Steps, roles, approvals or timing must change → **PC**
6. **Still torn** → **HITL**: leave `code` empty, give exactly two
   `hitl_candidates` and a `hitl_question`. A wrong code costs more than an
   escalated one.

### PC and AC are not mutually exclusive

Most real rows need both a configuration *and* a behaviour change. One code is
permitted, so apply the **dominant-blocker rule**: code the change that blocks
go-live if it does not happen, and put the other in `also_requires`. Without
that clause the onboarding list loses config work that genuinely existed.

### Bias toward FB when capability existence is unproven

The two error directions are not equally priced. A false FB surfaces in backlog
grooming and is removed within days. A false AC or PC hides a build need until
UAT, after the readiness score has been reported. So when the capability column
does not affirmatively establish the capability, classify **FB** and record
`overturned_by` — what evidence would reverse it. An FB that cannot be appealed
will not be trusted, so `audit.py` requires that field.

Never infer capability from a product's general reputation, from another row, or
from what the platform "surely must" support.

### The gap can run backwards

Sometimes the platform exceeds current state — it offers a control the branch
has been unable to give its boards. That is an **AC** with a note, not a gap.
Flag it, because it is an upsell and an onboarding decision rather than a build
item.

### NA requires positive evidence

`NA` removes the row from the readiness denominator, making it the one code that
quietly improves the score. **Silence is not NA.** Require a statement that the
branch does not do this, or that it does not apply.

## Capability proximity

Judged from facet overlap — not from the prefix, not from text similarity.

| Verdict | Meaning | Typical pairing |
|---|---|---|
| `Exact match` | facets align; drop-in | AC |
| `High (~75%)` | same outcome and mechanism; minor actor or timing deltas | AC / PC |
| `Moderate (~50%)` | outcome overlaps; material control, scope or exception deltas | PC |
| `Low (~25%)` | small overlap; most of the branch's need unmet or done very differently | FB / PC |
| `No match` | nothing comparable on one side | FB / NA |

A `Native` capability the branch handles completely differently is still a
Moderate or Low proximity **PC**.

## Confidence is derived, not felt

A free judgement drifts across hundreds of rows and means nothing in aggregate.
`plan.py` prints the ceiling each row can legitimately reach:

| Level | Conditions |
|---|---|
| **High** | driving facet explicit on both sides · support-level prefix or clear negation · both entailment answers unambiguous · lexical and semantic signals agree |
| **Medium** | driving facet inferable but not stated on one side · or `~` / "confirm with product" · or one entailment answer is partial · or a sub-feature is unverified |
| **Low** | capability side is prose with no support level and no explicit negation · or only part of a multi-part question compares · or an unresolved flag |
| → HITL | below Low — two codes remain equally defensible |

`Confidence: Low` is a legitimate and useful result.

## Assessor note format

Auditable by design: a reader must be able to disagree without re-reading both
cells. `apply.py` renders this, so you never type it.

```
BRANCH: <the clause from the branch answer that drives the code>
TOWNSQ: <the clause from the capability column that drives the code>
DELTA: <which facets differ>
WHY <CODE>: <one or two sentences>
Also requires: <secondary config or process change, if any>
Overturned by: <required on FB>
Proximity: <verdict>.
Confidence: <level> (<what is solid; what is not>)
Flags: <...>
```

Quote or tightly paraphrase both sides, each from its **own** column —
`audit.py` fails a branch clause that also appears in the capability column. No
adjectives about fit quality; state what matches and what doesn't.

## Workflow

### 1. Triage
```bash
python scripts/plan.py rubric.json -o build/
```
Buckets every row, profiles the marker distribution, prints the confidence
ceiling, flags classification leakage, and emits `build/verdicts.json` for rows
where **both** sides are substantive.

Two audits it performs that matter more than they look:
- **non-code sentinels in `classification`.** Earlier automated passes leave
  values like an em-dash to mean "escalated". They look classified in a grid and
  count as unclassified everywhere else.
- **codes on rows with no branch answer.** Unsupported — there was no branch
  answer to compare against. Flag; do not trust and do not silently overwrite.

Report the classifiable count as a fraction of rows that have a branch answer.
It is routinely far below 100%, and that number sets expectations before any
work begins.

### 2. Classify, by capability
Fill the skeleton. Group on **capability name**, not the capability number,
which is text on some rows and a float on others and silently splits a
capability in two.

Work a whole capability at once and re-read its rows side by side before
committing. Materially identical pairs must carry identical codes; row-at-a-time
classification drifts, and inconsistency inside a single capability is the
defect a reviewer finds first. Rows resting on the same disputed capability
claim should not quietly carry different codes.

### 3. Audit
```bash
python scripts/audit.py rubric.json build/verdicts.json --report
```
Must exit 0. Fix the verdict, not the checker.

### 4. Apply
```bash
python scripts/apply.py rubric.json build/verdicts.json -o out/rubric.json
```
Add `--append-notes` where rows already carry a note; existing notes are joined
with ` | `, never replaced.

### 5. Report
Counts by domain and code, the FB list with proposed priorities, the HITL list
with its deciding questions, the blocked lists — and a readiness figure **only**
for domains that are fully answered and fully classified.

## Guardrails

- **Never classify on the capability column alone.** No branch answer means no
  gap to measure.
- **Never infer a branch answer.** Classify strictly on the text. If it is
  vague, say so in confidence and consider HITL rather than picking the
  flattering reading.
- **Never write a readiness number.** The gate shows `—` until a domain's branch
  answers are complete and its classification is finished. That dash is by
  design.
- **Never set `fb_priority`.** It belongs to FB rows only and priority is a
  business decision.
- **Never overwrite an existing assessor note** without confirmation.
- **The roll-up repair belongs to the xlsx layer**, not here. Known defects in
  that workbook family: summary formulas referencing the capability column
  instead of the classification column, ranges frozen at a stale lower bound,
  and a domain roster that no longer matches the domains present. If the roll-up
  is broken, these classifications display as zero — check it on the first
  conversion.
