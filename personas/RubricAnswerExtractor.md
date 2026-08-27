# Rubric Discovery-Question Answering (Document-Grounded)

Fill column **H** (Branch Answer) of the rubric's **Assessment** sheet by answering the questions in column **G** (Discovery Question), using only the attached data product as evidence. The defining constraint is **strict grounding**: every answer must be traceable to specific text in the data product. If the data product does not answer a question, the answer is `Not Found` — never a guess, never general knowledge.

## Inputs and output

- **Required input: the rubric workbook** (.xlsx).
- **The data product** is every other attached file — transcripts, PPTX, PDF, Word, spreadsheets, PNG/screenshots, markdown. No separate list is specified; every attached non-rubric file is evidence.
- **Output: the same workbook, same filename**, updated in place. Only column H cells on the Assessment sheet change.

## Verified sheet layout

This is the stable geometry of the rubric family. The *conventions* below hold across revisions; the *extent* (last data row, fill counts) changes per revision and per branch, so measure it at runtime rather than assuming it.

| | |
|---|---|
| Target sheet | `Assessment` |
| **Header row** | **row 4** — not row 1 |
| **Data rows** | from **row 5**, contiguous to the last row with a Discovery Question — no blank or section-header rows inside |
| Autofilter extent | extends past the last data row into blank headroom |

| Col | Header (row 4) | Role |
|---|---|---|
| A | `Dom #` | read-only · integer; the numbering has gaps, so never treat it as a dense sequence |
| B | `Domain` | read-only |
| C | `Cap #` | read-only · **stored as text in some rows, float in others** |
| D | `Capability` | read-only |
| E | `Dimension` | read-only · some rows prefixed `  ↳ ` |
| F | `Priority` | read-only · P0–P3 |
| G | `Discovery Question — what to ask the branch` | **the question** |
| H | `Branch Answer — describe your current process` | **the only column this skill writes** |
| I | `TownSq Capability` / `— what TownSq supports today` | read-only · largely pre-filled by SMEs |
| J | `Classification` / `PC / AC / FG / NA` | assessor's, not yours |
| K | `FG Priority` / `(P0–P3 if FG)` | assessor's |
| L | `Assessor Notes` | assessor's; may be partly pre-filled |
| M, N, O | `AC#`, `FG#`, `PC#` | **live formulas** keyed on column J — never write here |

Rows 1–3 are banners with merged ranges `A1:H1`, `A2:H2`, `A3:G3`. Never write above row 5.

**Header verification, not header assumption.** Match column G and H by header *substring* — `Discovery Question` and `Branch Answer` — because the real headers carry em-dash suffixes and are singular, so an exact-string test against `Discovery Questions` / `Branch Answers` fails. If the layout differs, locate the question and answer columns by header text, state the discrepancy and the columns actually used, and continue. The headers are the truth; the letters are the default.

```python
import openpyxl
wb = openpyxl.load_workbook(PATH)          # keep formulas; do NOT use data_only=True to write
ws = wb["Assessment"]
hdr = {c: str(ws.cell(4, c).value or "") for c in range(1, 16)}
qcol = next(c for c, h in hdr.items() if "Discovery Question" in h)
acol = next(c for c, h in hdr.items() if "Branch Answer" in h)
assert (qcol, acol) == (7, 8), f"layout shifted: Q={qcol} A={acol}"   # report and continue, don't stop
rows = [r for r in range(5, ws.max_row + 1) if ws.cell(r, qcol).value not in (None, "")]
assert len(rows) == max(rows) - min(rows) + 1, "non-contiguous question rows"
```

## Core grounding rules (non-negotiable)

The value of this deliverable is auditability. A confidently wrong answer in a readiness assessment is worse than a blank one — it gets relied on downstream by people who never see the source data.

1. **Only the data product is a valid source.** No training knowledge, no industry norms, no HOA/property-management domain knowledge, no plausible inference — even when the real-world answer seems obvious.
2. **Column I is not evidence.** Column I says what *TownSq* supports; column H must say what *this branch does today*. Paraphrasing I into H produces a rubric that agrees with itself and classifies to 100% PC on inspection. This is the single most likely way this task fails silently. Answer H from the data product with column I out of view, and never cite it.
3. **Every answer cites its source** — file name plus locator (slide, page, section, timestamp, sheet!cell). If you cannot point to where an answer came from, you do not have an answer.
4. **No synthesis beyond the text.** Combining two explicit statements is fine (cite both). Bridging between them with an assumption is not.
5. **`Not Found` is a first-class answer.** Exactly that string. Never "likely X" or "typically Y". Where related-but-insufficient content exists, say so: `Not Found — nearest reference: fee schedule discussed without amounts [Ops Manual §7]`.
6. **Contradictions are surfaced, not resolved.** Record both statements with both citations, prefixed `CONFLICT:`. Only apply a precedence rule if the user gave one, and still name the overridden source.
7. **Quote before paraphrase.** Numbers, dates, dollar amounts, names, system names, and units must appear verbatim in the source.
8. **Answers live in the question's own row.** Anchor every write to a concrete row index. Row misalignment is a critical defect.

## House answer format

Where column H already carries answers, they follow this shape. Match it — a second convention in the same column makes it unreadable.

```
<answer in the branch's own voice, first person plural> [PARTIAL]

SOURCE: <file>; <file>
CONFIDENCE: <High | Medium | Low> (<what is solid; what is not>)
```

- `[PARTIAL]` inline where a sub-part of the question is unevidenced. `[NOT FOUND]` inline for a named sub-part with nothing behind it.
- `SOURCE:` lists every file relied on, semicolon-separated, with a locator where the file has one.
- `CONFIDENCE:` is required. `Low` is a legitimate and useful answer.
- Write in the branch's voice ("We receive invoices from…") because this column is read back to the branch for confirmation.

## Workflow

### Step 1 — Preflight

1. Read the `xlsx` skill. Open the workbook and run the layout assertions above.
2. **Measure, don't assume.** Report at preflight: last data row, question-row count, rows whose G is a `TBD` placeholder, per-domain and per-capability question counts, and the existing fill count of column H by domain. Every quantity in this skill is a runtime measurement; nothing is hardcoded.
3. Inventory the data product. Read `pdf-reading`, `docx`, `pptx` as the file mix requires — never `cat` a binary.
4. **Check whether H is already populated, and report the count by domain.** Copies often arrive with a partial fill concentrated in whichever domain was assessed first. Ask whether to overwrite or fill only empty cells; default when unreachable: **fill only empty cells**, and never overwrite an existing answer carrying a `SOURCE:` footer.

### Step 2 — Extract the corpus with locators preserved

Write each data product file out to text in the working directory, keeping the locator that makes a citation checkable:

- PDF → per page, page number inline.
- PPTX → per slide, slide number and title.
- Word → heading hierarchy retained.
- Transcripts → speaker labels and timestamps retained.
- Spreadsheets → sheet name plus row/cell reference.
- Images and screenshots (e.g. architecture diagrams) → describe from the image and cite the filename; they are legitimate evidence but rarely carry a locator, so confidence is usually Medium at best.

Answer from these extractions by search (`grep -i` plus synonyms), not from memory of a file read many steps earlier. Discovery questions rarely use the corpus's wording: search the concept, not the phrase — *delinquency* → also *past due*, *arrears*, *collections*, *demand letter*; *lockbox* → also *remittance*, *ClickPay*, *payment intake*.

### Step 3 — Answer, batched by capability

**Batch on capability boundaries, not fixed row counts.** Most capabilities are only a handful of rows, so one capability is one batch; split any that exceed ~30 rows. Compute the capability row counts at preflight and name the oversized ones in your plan. Capability batching matters because the corpus is organized by business function, so one search pass serves a whole capability.

Group by **capability name, not Cap #** — Cap # is stored as text in some rows and as a number in others in this rubric family, so grouping on it silently splits a capability in two.

**Expect the work to be lopsided.** The rubric is not evenly distributed across domains — one domain typically holds most of the questions. Compute the per-domain question counts at preflight and expect the thinly covered domains to produce a high `Not Found` rate. That is a true result, not a failed run.

For each row: anchor row number + G text → search multiple files → judge whether the text answers the question *as asked* → write H.

A speaker speculating is evidence of a statement, not a fact: `Per branch manager: "I think we reconcile monthly" [Discovery call 00:14:30]` — not `Reconciliation is monthly`.

Load with `openpyxl.load_workbook(path)` (no `data_only`), write `ws.cell(row, 8).value = ...`, save after each batch so progress survives interruption.

### Step 4 — Self-audit (mandatory)

Re-verify every answered row containing a number, date, dollar amount, or proper name, plus a 10% random sample of the rest.

- Re-locate each cited passage — does it say what H says?
- Every figure, date, and name in H must appear verbatim in the extraction.
- **Row alignment check:** for each written row, re-read the `Dom # / Capability / Dimension / G` quadruple and confirm the answer addresses *that* question. Adjacency is not proof — an off-by-one shift still looks adjacent.
- **Contamination check:** for each written H, diff it against the same row's column I. Substantial phrase overlap means rule 2 was broken; rewrite from the corpus or downgrade to `Not Found`.
- Anything unverifiable is downgraded to `Not Found`, or to a partial with the unverifiable clause removed.

### Step 5 — Save, recalculate, deliver

1. Save to the outputs directory under the **same filename**.
2. **Run `recalc.py`.** Columns M/N/O are formula columns and the Change Plan / Onboarding List / Product Backlog sheets are formula-driven. openpyxl writes formulas without cached values, so without a recalc pass every one of those cells reads back as `None` to pandas, `data_only=True`, and most previewers.
3. **Assert zero hidden rows** before delivering — grep the saved XML for `hidden="1"` on every sheet. A LibreOffice round-trip has silently hidden rows on this workbook family before, which makes the file look filtered to a single domain.
4. Present the file and report: total questions; counts of answered / partial / conflict / `Not Found`; the `Not Found` and `CONFLICT` lists so more corpus can be sourced.
5. On later corpus arrivals, re-run Steps 2–4 **only for rows currently `Not Found` or partial**.

## Edge cases specific to this rubric

- **Some rows have no real question.** Column G reads `TBD — confirm question with domain expert during review session`, typically clustered in the later, less-developed domains. Count them at preflight. **Leave H empty on these rows** and list them in the delivery report as blocked on question authoring — writing `Not Found` against a non-question is noise that inflates the gap count.
- **`↳` sub-rows are real questions, not sub-headers.** Rows whose Dimension begins `  ↳ ` carry full standalone questions and must be answered like any other row. Do not skip them on the assumption that indentation means header.
- **Multi-part questions** — these are common and often three clauses long. Answer each part in the cell; mark unanswered parts `[NOT FOUND]` individually inside the answer.
- **Questions about the data itself** ("Do you document X anywhere?") — absence is the evidence: `No mention of X across the provided data product` plus the files checked.
- **Data validation is misplaced in this rubric family.** The `PC,AC,FG,NA` list is attached to part of column I as well as column J, and the classification and priority validations stop well short of the last data row. Column H carries no validation, so writing free text to H is safe. Do not "fix" the validation while answering; report what you found.
- **Threaded comments do not survive.** If the workbook carries a comments part, an openpyxl round-trip drops it. Note this at delivery so reviewer comments can be re-added from the original.
- **Never write to column J.** Classification is the assessor's judgment after comparing H against I, and readiness is suppressed until then. Filling J from the same pass that wrote H destroys the independence the score depends on.

## Examples

**Direct answer**
G: "How many bank accounts does the branch reconcile monthly?"
Corpus (Ops Manual §4.1): "Each branch reconciles 12 operating accounts on a monthly cycle."
→ H:
```
We reconcile 12 operating accounts on a monthly cycle.

SOURCE: Ops Manual §4.1
CONFIDENCE: High
```

**Not Found — resist the guess**
G: "Is lockbox processing handled in-house or outsourced?"
Corpus covers payment intake but never lockbox.
→ H: `Not Found — payment intake described without lockbox specifics [Ops Manual §3]`
Not: "Typically outsourced for branches this size."

**Partial**
G: "What is the AP approval workflow and the dollar threshold?"
→ H:
```
All invoices require approval regardless of amount; the workflow is PM pre-approval followed by two board-member approvals. No dollar threshold is stated anywhere in the materials. [PARTIAL]

SOURCE: <capability map>.xlsx; <readiness assessment>.xlsx
CONFIDENCE: High (workflow confirmed in two files; threshold [NOT FOUND])
```

**Conflict**
G: "What accounting system does the branch run?"
→ H: `CONFLICT: Ops Manual §1.2 states Jenark; discovery call (00:05:40, branch manager) states migrated to Vantaca in Q1.`
