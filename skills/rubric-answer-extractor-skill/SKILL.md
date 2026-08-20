# Rubric Answer Extractor — Integrated Version

## Purpose

Extract answers from source documents and populate rubric assessment questions with full source attribution, confidence scoring, and conflict detection. This skill maintains strict grounding in provided evidence, produces audit-ready documentation, and integrates seamlessly with JSON and Excel rubric workflows.

## When to Use This Skill

- **Populate discovery questions** from operational documents (PDFs, transcripts, presentations, spreadsheets, Word docs, images)
- **Ground answers in evidence** — every answer includes source file, locator, and confidence level
- **Handle conflicts and partial answers** — surface contradictions and unanswered sub-questions explicitly
- **Work with mixed rubric formats** — Excel workbooks AND/OR JSON assessment templates
- **Audit compliance** — produce fully traceable, defensible assessment documentation
- **Integrate with other rubric skills** — output feeds to json-question-answer-patcher for JSON updates or json-rubric-tools-skill for format conversion

## Core Principles

### 1. Strict Grounding (Non-Negotiable)

Every answer must be traceable to specific evidence in the provided source documents. No training knowledge, industry norms, inferences, or guesses — only what the documents explicitly state.

- **Only the data product is valid evidence.** If not in the documents, answer is `Not Found`
- **Don't use column I (TownSq Capability) as evidence.** Column H must describe the branch's *current* process, not what the vendor supports
- **Every answer cites its source** — file name plus locator (page, slide, section, timestamp, sheet!cell)
- **Synthesize only explicit statements** — combining two statements is fine; bridging with assumptions is not

### 2. Answer Format (Standardized, Auditable)

```
<answer in branch voice, first person plural> [PARTIAL / NOT FOUND markers inline]

SOURCE: <file with locator>; <file with locator>
CONFIDENCE: <High | Medium | Low> (<what is solid; what is not>)
```

**Format details:**
- Write in the branch's voice: "We reconcile 12 accounts monthly" (not "The branch reconciles…")
- Mark unanswered sub-parts inline: `[PARTIAL]` for partial coverage, `[NOT FOUND]` for named missing parts
- **SOURCE:** lists every file used, semicolon-separated, with locators where available
- **CONFIDENCE:** always required. High/Medium/Low with explanation of what's certain vs. uncertain
- Quote numbers, dates, dollar amounts, names, and system names exactly as they appear in the source

### 3. No Guessing, No Over-Synthesis

- `Not Found` is a valid answer — used when evidence is insufficient
- Speculation by a speaker is evidence of the statement, not the fact: `Per branch manager: "I think we reconcile monthly"` ≠ `Reconciliation is monthly`
- Contradictions are surfaced, not resolved: `CONFLICT: Source A says X; Source B says Y`
- Row misalignment is critical — every answer is anchored to its specific row's question

## Workflow: Answer Extraction

### Step 1 — Preflight & Planning

1. **Assess the rubric layout:**
   - **Excel workbook:** Locate the Assessment sheet; find question column (usually "Discovery Question") and answer column (usually "Branch Answer")
   - **JSON template:** Identify the questions array and the branch_answer field structure
   - Measure the scope: total questions, existing fill count, domains/capabilities represented

2. **Inventory the source documents:**
   - List all attached files: PDFs, PPTX, Word, transcripts, spreadsheets, images
   - Note which business functions each document covers
   - Flag any incomplete or unclear documents

3. **Report findings:**
   - Total questions to answer
   - Current fill status (fully answered / partial / empty)
   - Recommendation: overwrite existing answers or fill only empty cells? (default: fill only empty)
   - Expected coverage by domain (some domains may show high `Not Found` rates — this is valid)

### Step 2 — Extract & Index the Corpus

Convert all source documents to searchable text while preserving locators:

**PDF** → per-page text with page numbers inline
**PPTX** → per-slide text with slide number and title
**Word** → heading hierarchy preserved
**Transcripts** → speaker labels and timestamps retained
**Spreadsheets** → sheet name + row/cell reference
**Images/Screenshots** → describe visual content; cite filename (usually no precise locator)

Create a working copy of extractions in the current directory so answers can be verified by search rather than memory.

### Step 3 — Answer by Capability Batch

**Batch on capability boundaries, not fixed row counts.** Group questions by capability name (not Cap #, which may be stored inconsistently as text or number).

For each row:

1. Read the question in column G (Excel) or the question text (JSON)
2. **Search the corpus for concepts, not phrases** — use synonyms and variations
   - *lockbox* → also *remittance*, *payment intake*, *ClickPay*
   - *delinquency* → also *past due*, *arrears*, *collections*
3. Judge whether the evidence answers the question *as asked*
4. Write the answer in the standardized format (see Answer Format above)
5. Save after each batch — progress survives interruption

**Example answering flow:**

Question: "How many bank accounts does the branch reconcile monthly?"

Corpus extract: "Each branch reconciles 12 operating accounts on a monthly cycle." [Ops Manual §4.1]

Answer to write:
```
We reconcile 12 operating accounts on a monthly cycle.

SOURCE: Ops Manual §4.1
CONFIDENCE: High
```

### Step 4 — Handle Special Cases

**`Not Found` — when evidence is insufficient:**
```
Not Found — payment intake described without lockbox specifics [Ops Manual §3]
```
(Not: "Typically outsourced…" — no guessing)

**Partial answers — when some parts are unanswered:**
```
All invoices require approval regardless of amount; the workflow is PM pre-approval followed by two board-member approvals. No dollar threshold is stated anywhere in the materials. [PARTIAL]

SOURCE: Capability Map §2; Assessment Template
CONFIDENCE: High (workflow confirmed; threshold [NOT FOUND])
```

**Conflicts — when sources contradict:**
```
CONFLICT: Ops Manual §1.2 states Jenark; discovery call (00:05:40, branch manager) states migrated to Vantaca in Q1.
```

**TBD questions** — Some rubrics have placeholder questions like "TBD — confirm with domain expert":
- Leave H (Excel) or branch_answer (JSON) empty on these rows
- List them in the final report as blocked on question authoring

**Multi-part questions** — Answer each part; mark unanswered parts `[NOT FOUND]` individually inside the answer

### Step 5 — Self-Audit (Mandatory)

Re-verify every row with numbers, dates, dollar amounts, or proper names, plus a 10% random sample of all answers:

- Re-locate each cited passage — does it match H exactly?
- **Every figure, date, and name must appear verbatim** in the source
- **Row alignment check:** for each answered row, re-read the question and confirm the answer addresses *that specific question*
- **Contamination check:** diff H against I (TownSq Capability) — if substantial phrase overlap, rewrite from corpus or downgrade to `Not Found`
- Anything unverifiable → downgrade to `Not Found` or remove the unverifiable clause

### Step 6 — Format & Deliver

**For Excel workbooks:**
1. Save to outputs directory under the **same filename**
2. Run `recalc.py` — Columns M/N/O contain formulas that need cached values
3. Assert zero hidden rows before delivery
4. Report: total questions, counts of answered/partial/conflict/`Not Found`, and the lists of all conflicts and gaps

**For JSON templates:**
1. Export answers in JSON format ready for json-question-answer-patcher integration:
   ```json
   {
     "question_index": 0,
     "branch_answer": "We reconcile 12 accounts monthly...",
     "source": "Ops Manual §4.1",
     "confidence": "High"
   }
   ```
2. Can then be fed to json-question-answer-patcher for programmatic update to the template

**Round-trip workflow (Excel → JSON → Updated Excel):**
1. Extract answers into Excel with this skill
2. Convert Excel to JSON with json-rubric-tools-skill
3. Further edit or patch JSON with json-question-answer-patcher
4. Convert back to Excel with json-rubric-tools-skill
5. Deliver final workbook

## Rubric Layout Reference (Excel)

**Location:**
- Sheet: `Assessment`
- Header row: **row 4** (not row 1)
- Data rows: from **row 5** onward, contiguous

| Col | Header | Role |
|---|---|---|
| A | `Dom #` | Domain number |
| B | `Domain` | Domain name |
| C | `Cap #` | Capability number (may be text or number) |
| D | `Capability` | Capability name |
| E | `Dimension` | Dimension (some prefixed `  ↳ `) |
| F | `Priority` | Priority (P0–P3) |
| **G** | **`Discovery Question`** | **← Questions to answer** |
| **H** | **`Branch Answer`** | **← This skill writes here** |
| I | `TownSq Capability` | Reference only (not evidence) |
| J | `Classification` | Assessor's judgment (do not write) |
| K | `FG Priority` | Assessor's (do not write) |
| L | `Assessor Notes` | Assessor's (do not write) |
| M, N, O | Live formulas | Do not write |

**Header verification by substring match** — column headers carry em-dash suffixes and may vary slightly, so match on substrings like `Discovery Question` and `Branch Answer` rather than exact strings.

## Integration Points

### With json-rubric-tools-skill

**Sequence:**
1. Extract answers into Excel with this skill → Excel workbook with populated column H
2. Use json-rubric-tools-skill's `rubric_json_to_xlsx.py` to convert JSON templates to Excel
3. Or use `rubric_xlsx_to_json.py` to convert completed Excel back to JSON for downstream processing

### With json-question-answer-patcher

**For JSON-first workflows:**
1. Start with JSON assessment template
2. Extract answers with this skill (outputs JSON-compatible format with question_index, branch_answer, source, confidence)
3. Feed to json-question-answer-patcher to update the template programmatically
4. Result: fully answered, auditable JSON assessment

### As Part of a Persona

When attached to a persona alongside both tools:
- This skill **extracts** answers from source documents
- json-rubric-tools-skill **converts** between formats as needed
- json-question-answer-patcher **updates** JSON templates with extracted answers

This trio handles complete rubric workflows: discover → extract → structure → integrate.

## Confidence Scoring Guidance

| Level | When to Use | Example |
|---|---|---|
| **High** | Direct quote or explicit statement; multiple sources agree | "We reconcile 12 accounts monthly" [Ops Manual + confirmed in call] |
| **Medium** | Clear enough from context but not explicitly stated; or single source only | "Fee schedule exists" [mentioned once in board minutes] |
| **Low** | Partial evidence, speaker speculation, inference at edge of explicit text, or image-based (no text locator) | "We likely have 15–20 accounts" [per CFO estimate in call; no written record] |

Always explain *why* — what's solid, what's inferred, what's missing.

## Edge Cases

- **Whitespace/merged cells in Excel:** openpyxl reads them consistently; no special handling needed
- **Comments/threaded feedback in workbooks:** openpyxl drops comments on round-trip; note this in delivery
- **Data validation:** may be incomplete in some rubric versions; do not attempt to fix — report findings
- **Revisiting after new corpus arrives:** re-run Steps 2–4 **only for rows currently `Not Found` or partial**

## Example Audit Trail

**Source document:** Ops Manual, Section 4.1
**Question (G5):** "How many bank accounts does the branch reconcile monthly?"
**Extracted evidence:** "Each branch reconciles 12 operating accounts on a monthly cycle."
**Answer (H5):**
```
We reconcile 12 operating accounts on a monthly cycle.

SOURCE: Ops Manual §4.1
CONFIDENCE: High
```

**Audit:** ✓ Exact quote from locator ✓ Answers the question ✓ First-person voice ✓ Row-specific alignment

---

## How to Request Answer Extraction

Provide:
1. **The rubric file** (Excel .xlsx OR JSON template)
2. **All source documents** (PDFs, transcripts, PPTX, Word, spreadsheets, images)
3. **Scope**: which domains/capabilities, or all questions?
4. **Existing answers:** overwrite or fill only empty cells?
5. **Format preference:** deliver as updated Excel, JSON, or both?