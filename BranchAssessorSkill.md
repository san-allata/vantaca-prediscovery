# Branch Readiness Classifier

Compare the branch's **current state** (column H) against TownSq's **actual capability** (column I) and record the *gap between them* as a classification in column J, with the reasoning in column L.

This is not text similarity. Two answers can share almost no vocabulary and be an exact functional match, or read almost identically and hide a feature gap. What is being judged is whether the branch's required outcome can be produced by TownSq, and if so, what has to change to get there.

The skill is branch-agnostic and rubric-version-agnostic. Row counts, fill levels, and which rows are blocked differ per branch and per rubric revision, so **every quantity is measured at runtime** in Step 1 rather than assumed.

## Workbook contract

Work only on the **Assessment** sheet. Headers on **row 4**; data starts at **row 5** and runs contiguously to the last row carrying a Discovery Question.

| Col | Field | Role |
|---|---|---|
| A–E | Dom #, Domain, Cap #, Capability, Dimension | READ ONLY — context |
| F | `Priority` (P0–P3) | READ ONLY — the dimension's inherent priority. **Not** a classification input and **not** the same as column K. Some rows have none. |
| G | Discovery Question | READ ONLY |
| **H** | Branch Answer — current process | **Input** |
| **I** | TownSq Capability — what TownSq supports today | **Input** |
| **J** | Classification | **Output** — exactly `PC`, `AC`, `FB`, or `NA` |
| K | FB Priority (P0–P3) | READ ONLY unless asked. Applies **only to FB rows**. |
| **L** | Assessor Notes | **Output** |
| M–O | AC# / FB# / PC# | READ ONLY — live formulas keyed on column J. Writing J renumbers them. |

Match G and H by header **substring** (`Discovery Question`, `Branch Answer`) — the real headers carry em-dash suffixes and are singular, so exact-string tests against plural forms fail. Headers are the truth; column letters are the default. Rows 1–3 are merged banners; never write above row 5.

Rows whose Dimension is prefixed `  ↳ ` are **full standalone questions, not sub-headers**. Classify them like any other row.

**The J dropdown does not protect you.** In this rubric family the `PC,AC,FB,NA` validation covers only a leading band of rows, and the same list is also misapplied to part of column I — so many rows have no dropdown at all and Excel will not reject a bad value. Validate code strings in your own code before writing, and report the validation coverage you found.

## Reading column I: the prefix is a hypothesis, not the evidence

SME answers often open with a capability prefix, but a large share of cells carry none, and some carry markers that look structural and aren't. Profile the actual distribution in Step 1; never assume it.

**Support-level prefixes** — a genuine signal, still not sufficient alone:

| Prefix | Meaning |
|---|---|
| `Native —` | out of the box |
| `After config —` | supported once configured during onboarding |
| `Partial —` | some of the dimension supported; a gap remains |
| `Change in-progress —` | being built or rolled out now |
| `Not supported —` | no capability today |
| `TBD` | not answered — **blocked, do not classify** |

**Patterns that defeat prefix matching.** Expect all four and detect them explicitly:

- **No prefix at all.** A large minority of cells are plain prose. No shortcut exists; read them.
- **Speaker-initial prefixes** — two or three letters, or an org name, followed by `-` or `:`. These look structural but encode *who said it*, not the support level. A prefix-keyed classifier gets zero signal from them while believing it matched. The verdict is usually inside the prose instead: "still in development", "not fully available yet", "not currently supported". When an unexplained marker appears, ask the SME what it denotes rather than inferring a support level from it.
- **Bare-prefix stubs.** A cell containing only `Change in-progress`, or only `After config`, with no sentence behind it, is not a capability statement. **Treat as blocked, exactly like TBD.** Detect by cell length, not by prefix.
- **Classification leakage.** Occasionally an SME writes the verdict itself into column I (`FB — <capability> not currently supported`, sometimes with a priority attached). Treat as an SME-asserted classification to confirm and cite rather than re-derive, and report it — the judgment belongs in column J.

## Method: decompose, then compare facet by facet

Do not compare paragraph to paragraph. Reduce each side to the facets below and note which ones differ. The classification falls out of *which* facets diverge, not how much the text differs.

| Facet | Question |
|---|---|
| **Outcome** | What business result is produced? |
| **System of record** | Where does the authoritative data live? |
| **Mechanism** | Automated, batch, manual, integration, import? |
| **Actors** | Who performs and who approves — roles, not names |
| **Trigger & timing** | Event-driven, scheduled, monthly close, on demand? |
| **Controls** | Approvals, thresholds, segregation of duties, dual sign-off |
| **Exceptions** | NSF, reversals, mid-year switches, legal hold, edge cases |
| **Evidence** | What audit trail or artifact is produced? |

Divergence in **outcome** or **exceptions** points to FB. Divergence in **actors, timing, or controls** with the outcome intact points to PC. Convergence on everything except **mechanism setup** points to AC.

## Decision ladder

Walk it in order; stop at the first test that resolves.

1. **Is either side unreadable?** H empty, or I is `TBD` or a bare-prefix stub → **blocked**, no code. Report; do not classify.
2. **Does the branch do this at all?** H states positively that they don't, or it doesn't apply to their portfolio → **NA**.
3. **Can TownSq produce the required outcome today?** Evidence in I says no, or says `Partial` where the missing part covers something H shows the branch actually depends on → **FB**.
4. **Is the capability in flight rather than live?** `Change in-progress`, "in development", "on the roadmap" → **FB**, unless I explicitly states availability before this branch's go-live. Either way, name the dependency and the date in L.
5. **Capability exists. Must the branch change how it works?**
   - Only the system needs setting up; the branch's steps, roles, and timing survive → **AC**
   - The branch's steps, roles, approvals, or timing must change → **PC**
6. **Still torn between two codes** → **HITL**: leave J empty, write both candidates and the deciding question in L, list the row for human review. A wrong code costs more than an escalated one.

### PC and AC are not mutually exclusive

Most real rows need both — a configuration *and* a behavior change. The rubric permits one code, so apply the **dominant-blocker rule**: assign the code for the change that blocks go-live if it does not happen, and record the other explicitly in L as `Also requires: <config or process change>`. Without that clause the Onboarding List loses config work that genuinely existed.

### Bias toward FB when capability existence is unproven

The two error directions are not equally priced. A false FB surfaces in backlog grooming and is removed within days. A false AC or PC hides a build need until UAT, after the readiness score has been reported to the client. So when I does not affirmatively establish that the capability exists, classify **FB** and state what evidence would overturn it. Never infer capability from a product's general reputation, from another row, or from what TownSq "surely must" support.

### NA requires positive evidence

`NA` removes the row from the readiness denominator, making it the one code that can quietly improve the score. **Silence is not NA.** If H simply doesn't mention the topic, that is an unanswered row, not an inapplicable one. Require a statement in H that the branch does not do this, or that it does not apply.

## Capability proximity verdict

Every classified row gets one, judged from facet overlap — not from the prefix, not from text similarity.

| Verdict | Meaning | Typical pairing |
|---|---|---|
| **Exact match** | Facets align; drop-in | AC |
| **High (~75%)** | Same outcome and mechanism; minor actor or timing deltas | AC / PC |
| **Moderate (~50%)** | Outcome overlaps; material control, scope, or exception deltas | PC |
| **Low (~25%)** | Small overlap; most of the branch's need unmet or done very differently | FB / PC |
| **No match** | Nothing comparable on one side | FB / NA |

A `Native` capability the branch handles completely differently is still a Moderate or Low proximity **PC**.

## Assessor note format (column L)

Auditable by design: the note must let a reader disagree with you without re-reading both cells.

```
BRANCH: <the clause from H that drives the code>
TOWNSQ: <the clause from I that drives the code>
DELTA: <which facets differ — outcome / mechanism / actors / timing / controls / exceptions / evidence>
WHY <CODE>: <one sentence>
Also requires: <secondary config or process change, if any>
Proximity: <Exact match | High (~75%) | Moderate (~50%) | Low (~25%) | No match>.
Confidence: <High | Medium | Low> (<what is solid; what is not>)
```

Quote or tightly paraphrase both sides. No adjectives about fit quality — state what matches and what doesn't. `Confidence: Low` is a legitimate and useful result.

## Execution workflow

1. **Profile the workbook before deciding anything.** Measure, don't assume — then report:
   - last data row, question-row count, capability count
   - column H fill count; column I fill count
   - column I marker distribution: each support-level prefix, no-prefix, speaker-initial, bare-prefix stub, `TBD`, classification leakage
   - pre-existing fill counts for columns J, K, L
   - `PC,AC,FB,NA` validation coverage, and which rows fall outside it
   - **any column J value that is not `PC` / `AC` / `FB` / `NA`** — earlier automated passes have left sentinels such as an em-dash to mean "escalated". They look classified in the grid but count as unclassified everywhere else, so report them and treat them as unclassified
   - whether the **Summary** sheet's formulas reference column J over the full row range, and whether its domain roster matches the Dom # values actually present (see step 9)
   - **triage buckets**: classifiable (H filled **and** I substantive) · blocked-on-SME (I is TBD or a stub) · blocked-on-branch (H empty) · already-classified · HITL

   Report the classifiable count as a fraction of rows that have a branch answer. It is routinely well below 100%, and that number sets expectations before any work begins.

2. **Load** with `openpyxl.load_workbook(path)` — no `data_only` — so the formulas in M–O survive. Read cached values in a separate pass if needed. Never save a `data_only=True` workbook.

3. **Audit rows already carrying a code.** Test each pre-existing J against ladder rule 1: a code on a row where **H is empty** is unsupported, because there was no branch answer to compare against. Flag these rather than trusting them or silently overwriting them. Skip already-classified rows by default; if re-classifying, report every change as old → new.

4. **Classify by capability, not row by row in file order.** Group on capability *name* — Cap # is stored as text in some rows and as a number in others in this rubric family, which silently splits a capability in two. Working a whole capability at once is what makes step 5 possible.

5. **Consistency pass, per capability.** Before writing, re-read the capability's rows side by side. Materially identical H/I pairs must carry identical codes. Row-at-a-time classification drifts across hundreds of rows, and inconsistency inside a single capability is the defect a reviewer finds first.

6. **Stage for review; do not ask once per row.** Write the proposed `J`, `L`, proximity, and confidence to a **`Classification Review`** sheet — one row per Assessment row, carrying the Assessment row number — and get sign-off there. Commit to columns J and L only after approval. Per-row confirmation does not scale at rubric size, and per-capability sampling misses the outliers.

7. **Write J and L only.** Assert every J value is in `{PC, AC, FB, NA}` in code before writing, since the dropdown covers only part of the sheet. Never write to A–G, K, or M–O.

8. **Recalculate and verify.** Run `recalc.py` — writing J changes what M/N/O compute, and openpyxl saves formulas without cached values. Then grep the saved XML for `hidden="1"` on every sheet and assert zero; a LibreOffice round-trip has silently hidden rows on this workbook family before, which makes the file look filtered to a single domain. Reload and spot-check five written rows against their Assessment row numbers.

9. **Verify the Summary sheet actually reflects what you wrote — this is part of the job, not an optional extra.** A classification nobody can see at the domain level has not been delivered. Before reporting, check all four:
   - its `PC` / `AC` / `FB` / `NA` formulas reference Assessment column **J**, not column I (pointing at I is a known defect in this workbook family and makes every count read zero)
   - its ranges cover the **full** data extent, not a stale lower bound from an earlier, shorter rubric revision
   - its domain roster matches the Dom # values actually present on the Assessment sheet — stale rosters name domains the workbook does not contain and omit ones it does
   - each row's counts reconcile against an independent recount of column J

   If any check fails the Summary is stale and your classifications roll up as zero. **Repair it** — correct the column reference, the ranges and the roster — or, if the user has told you to leave it alone, say plainly in the report that the roll-up is broken and by how much. Repairing the plumbing is not the same as typing a readiness figure; the gate stays.

10. **Report** counts by domain and code, the HITL and blocked lists, and a readiness figure *only for domains that are fully answered and fully classified*.

## Guardrails

- **Never classify on column I alone.** No branch answer means no gap to measure.
- **Never infer a branch answer.** Classify strictly on the text in H. If H is vague, say so in `Confidence` and consider HITL rather than picking the flattering reading.
- **Never type a readiness number into the Summary sheet.** Its readiness column is deliberately gated to show `—` until a domain's branch answers are complete and its classification is finished. That dash is by design, not a broken formula.
- **Do not set column K** unless asked. It belongs to FB rows only, and priority is a business decision, not a classification output.
- **Never overwrite an existing assessor note** without confirmation; if appending, separate with ` | `.
- **Work on a copy** in the working directory and deliver the copy.
- **Threaded comments do not survive** an openpyxl round-trip. If the workbook carries a comments part, say so at delivery.
