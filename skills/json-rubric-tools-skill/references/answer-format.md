# Rubric Answer Cell Format (Exact Spec)

This is the ONLY accepted format for text written into a rubric's answer
column (e.g., "Branch Answer" / Column H). Do not add extra labels,
headers, or a CONFIDENCE line into the cell text itself -- confidence is
tracked separately in the answers JSON metadata for reporting, and must
NOT be embedded in the delivered cell.

## Full / direct answer

```
f"{answer_corpus}\n\nSource: {source}"
```

Example:
```
We reconcile 12 operating accounts on a monthly cycle.

Source: Ops Manual Section 4.1
```

## Partial answer (some sub-parts unanswered)

Append a GAPS line describing what is missing, after the Source line:

```
f"{answer_corpus}\n\nSource: {source}\n\nGAPS: {gaps}"
```

Example:
```
All invoices require approval regardless of amount; the workflow is PM
pre-approval followed by two board-member approvals.

Source: Capability Map Section 2; Assessment Template

GAPS: No dollar threshold is stated anywhere in the materials.
```

## Not Found

Use the same "full answer" shape -- `answer_corpus` states there is no
evidence, `source` lists what was checked:

```
Not Found -- no lockbox-specific process is described in the materials.

Source: Ops Manual Section 3
```

## Conflicting sources

Use the "full answer" shape -- `answer_corpus` states the conflict
plainly, `source` lists all conflicting documents:

```
CONFLICT: Ops Manual Section 1.2 states the system of record is Jenark;
the discovery call (00:05:40, branch manager) states migration to
Vantaca occurred in Q1.

Source: Ops Manual Section 1.2; Discovery Call Transcript 00:05:40
```

## Field reference

| Field | Meaning | Appears in cell? |
|---|---|---|
| `answer_corpus` | The answer content, branch voice, first-person plural, no inline [PARTIAL]/[NOT FOUND] bracket markers -- the GAPS line carries that meaning instead | Yes |
| `source` | Semicolon-separated file + locator list | Yes, on its own line prefixed `Source:` |
| `gaps` | Plain-language description of what is missing/unanswered | Yes, only for partial answers, on its own line prefixed `GAPS:` |
| `confidence` | High / Medium / Low + rationale | No -- keep in the answers JSON only, for audit reporting |

## Building the JSON answer object

Extraction should still produce one JSON object per question with all
fields, even though only a formatted subset goes into the cell:

```json
{
  "question_index": 0,
  "answer_corpus": "We reconcile 12 operating accounts on a monthly cycle.",
  "source": "Ops Manual Section 4.1",
  "confidence": "High",
  "gaps": null,
  "branch_answer": "We reconcile 12 operating accounts on a monthly cycle.\n\nSource: Ops Manual Section 4.1"
}
```

For a partial answer:

```json
{
  "question_index": 3,
  "answer_corpus": "All invoices require approval regardless of amount; the workflow is PM pre-approval followed by two board-member approvals.",
  "source": "Capability Map Section 2; Assessment Template",
  "confidence": "High",
  "gaps": "No dollar threshold is stated anywhere in the materials.",
  "branch_answer": "All invoices require approval regardless of amount; the workflow is PM pre-approval followed by two board-member approvals.\n\nSource: Capability Map Section 2; Assessment Template\n\nGAPS: No dollar threshold is stated anywhere in the materials."
}
```

`branch_answer` is the exact, final, pre-formatted string that must be
written into the Excel cell by `patch_xlsx_inplace.py` (or into the
`branch_answer` field of a JSON template by `json-question-answer-patcher`).
Always compute `branch_answer` using the rules above BEFORE patching --
patch tools do not reformat text, they write exactly what they are given.
