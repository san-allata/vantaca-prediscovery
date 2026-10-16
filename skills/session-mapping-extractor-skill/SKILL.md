---
name: session-rubric-answerer
description: Run a Python script against the Sessions Master Rubric Mapping CSV to extract all rows for a single session number, returning columns B–I sorted by `planned_question_id` (col B) then `priority` (col H).

---

# Session Mapping Extractor

## Purpose

Run a Python script against the Sessions Master Rubric Mapping CSV to extract all rows for a single session number, returning columns B–I sorted by `planned_question_id` (col B) then `priority` (col H).

## When to Use

- Before processing any discovery session — call this first to get the full list of rubric rows for that session
- One session number per call — do not attempt to extract multiple sessions in one call
- Use the returned JSON as the input for transcript evidence fetching and rubric answering

## Column Reference (B–I)

| Output field | CSV column | Description |
|---|---|---|
| `planned_question_id` | B | e.g. S1-Q1 |
| `planned_question` | C | The question asked in the discovery session transcript — use as transcript search key |
| `uid` | D | Unique rubric row ID — e.g. Q0089 |
| `qid` | E | Rubric QID — e.g. 6.1.1 |
| `capability` | F | Capability name — use as answer context |
| `dimension` | G | Dimension name — use as answer context |
| `priority` | H | P0–P3 (P0 = highest priority) — governs processing order |
| `exact_master_rubric_question` | I | The exact rubric question to answer |

## Sort Order

Results are sorted **first by `planned_question_id` (B), then by `priority` (H)**. Priority values sort as P0 < P1 < P2 < P3.

## How to Run

1. Confirm the mapping CSV spreadsheet is attached to the chat (or available as a data product)
2. Call `run_skill_script` with `scripts/extract_session_rows.py` passing `{ "session": <N> }` as `inputData`
3. The script outputs a JSON array of row objects to stdout
4. Use the returned rows as the authoritative source for all downstream processing — never derive or infer these fields

## Output Format

```json
[
  {
    "planned_question_id": "S1-Q1",
    "planned_question": "Before we walk through the process...",
    "uid": "Q0089",
    "qid": "6.1.1",
    "capability": "Accounts Payable",
    "dimension": "Invoice intake & routing",
    "priority": "P0",
    "exact_master_rubric_question": "Walk through your AP process step by step..."
  },
  ...
]
```

## Hard Rules

- **One session number per call.** If the user provides multiple session numbers, call the script once per session.
- **Do not filter or modify the returned rows.** All downstream skills (session-rubric-answerer) must receive the rows exactly as returned.
- **All fields are read-only.** Never derive, paraphrase, or infer any of the 8 fields — they come exclusively from the CSV.
- **If the script returns 0 rows**, report the empty result and ask the user to confirm the session number. Do not proceed.