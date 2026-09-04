---
name: excel-qa-processor
description: Process Excel assessment files by extracting complete datasets without pre-filtering in SQL, then use jq to filter by session number (Column A values). Handles multi-session workbooks, detects actual column structure (column_1, column_2, etc.), extracts all rows starting from row 5, and outputs session-filtered questions with accurate question counts per session. Use this skill when processing assessment workbooks where SQL row/column references fail—the skill will export raw JSON and use jq for safe filtering.
---

# Excel QA Processor — Fixed for Column Detection & jq Filtering

## Purpose

Extract assessment data from Excel workbooks without pre-filtering in SQL. This skill:
- Exports the ENTIRE Assessment sheet to JSON (no WHERE clauses)
- Detects actual column structure (handles column_1, column_2, etc. naming)
- Uses jq to filter by session number safely
- Counts TOTAL questions per session
- Outputs clean, filtered questions JSON

## When to Use This Skill

- **Excel export without filtering**: Query returns all rows, then jq filters
- **Column detection failures**: "rowid not found", "column_a not found" errors
- **Multi-session workbooks**: Need to count ALL questions per session, not hardcode to 9
- **Session filtering**: Use jq instead of SQL WHERE clauses
- **Accurate question counts**: Report total_questions_in_session (may be 20+, not 9)

## Core Issues This Skill Fixes

### ❌ Problem 1: rowid Column Not Found
**Old Approach**: `SELECT rowid FROM data WHERE rowid >= 5`
**Error**: "rowid" is not a valid spreadsheet column
**Solution**: Use `SELECT *` to get all columns; filter in jq instead

### ❌ Problem 2: column_a Not Found
**Old Approach**: `SELECT column_a FROM data WHERE column_a != ''`
**Error**: First column is named differently (varies by sheet structure)
**Solution**: Extract all columns, detect first column name automatically, filter in jq

### ❌ Problem 3: Hardcoded 9-Question Limit
**Old Approach**: Assume 9 questions per session
**Error**: Session 1 may have 20+ questions; missing rows
**Solution**: jq counts all questions matching session number; report accurate total_questions_in_session

## Workflow: Complete Sheet Export + jq Filtering

### Step 1: Export Assessment Sheet (NO WHERE clause)

```sql
SELECT * FROM data LIMIT 10000
```

**Key Points**:
- Use LIMIT 10000 (high enough to capture all rows)
- Do NOT use WHERE to filter
- Do NOT use rowid
- Export as JSON array (list of objects)

### Step 2: Detect Actual Column Names

After export, examine first row:
```json
{
  "branch_assessment_one_row_per_dimension_...": null,
  "column_b": "Domain",
  "column_c": 1.1,
  "column_d": "General System Access",
  ...
}
```

**The actual column for session/domain number** is the first key (often has a long name like "branch_assessment_one_row_per_dimension_...").

**In jq, reference it as**: `.["branch_assessment_one_row_per_dimension_..."]` or use `.[0]` (first property).

Better approach: Use jq to detect dynamically:
```bash
jq 'map(to_entries[0].key) | .[0]'  # Get the first column's key name
```

Then reference in filter:
```bash
jq '.[] | select(.["<first_column_key>"] == 1)'  # Filter where session = 1
```

### Step 3: Filter by Session Using jq

**Command Structure**:
```bash
jq '.[] | select(.["<first_col_key>"] == 1) | {<keep_relevant_columns>}' assessment.json
```

**Example** (if first column key is "branch_assessment_one_row_per_dimension_..."):
```bash
jq '.[] | select(.["branch_assessment_one_row_per_dimension_branch_answers_assessor_classifies"] == 1)' assessment.json
```

**To count questions in session**:
```bash
jq '[.[] | select(.["<first_col_key>"] == 1)] | length' assessment.json
```

### Step 4: Build Filtered Questions JSON

Use jq to extract only needed columns and reshape:
```bash
jq '.[] | select(.column_1 == 1) | {
  question_index: .,
  domain_number: .,
  domain_name: .column_b,
  capability_number: .column_c,
  capability_name: .column_d,
  dimension: .column_e,
  priority: .column_f,
  discovery_question: .column_g
}' assessment.json | jq -s '.'
```

Result:
```json
[
  {
    "question_index": 5,
    "domain_number": 6,
    "domain_name": "Financial Operations",
    "capability_number": "6.1",
    "capability_name": "Accounts Payable",
    "dimension": "Invoice intake & routing",
    "priority": "P0",
    "discovery_question": "Walk through your AP process..."
  },
  // ... ALL other session questions (20+, not just 9)
]
```

### Step 5: Wrap in questions_sessionN.json Structure

Add metadata:
```bash
jq --arg session "1" --arg transcript "transcript.txt" --arg count "25" \
  '{
    session: ($session | tonumber),
    session_transcript: $transcript,
    total_questions_in_session: ($count | tonumber),
    questions: .
  }' filtered_questions.json > questions_session1.json
```

## Column Name Reference (Typical Assessment Sheet)

| Position | Key Name (varies) | Sample Content | Use |
|----------|-------------------|-----------------|-----|
| 1 | `branch_assessment_one_row_per_...` | 1, 2, 3, ... | Session/Domain number |
| 2 | `column_b` | "Financial Operations" | Domain name |
| 3 | `column_c` | 6.1, 6.2, ... | Capability number |
| 4 | `column_d` | "Accounts Payable" | Capability name |
| 5 | `column_e` | "Invoice intake & routing" | Dimension |
| 6 | `column_f` | "P0", "P1", ... | Priority |
| 7 | `column_g` | "How do you..." | Discovery Question |
| 8 | `column_h` | (empty or answer) | Branch Answer (TARGET) |

**NOTE**: First column key name varies. Detect it at runtime using jq.

## Error Avoidance Checklist

- [x] Do NOT use `rowid` in SQL queries
- [x] Do NOT pre-filter with WHERE clauses; export all rows
- [x] Do NOT hardcode column references; detect first column name at runtime
- [x] Do NOT assume 9 questions; count actual questions via jq
- [x] Do NOT use `SELECT col_a`; use `SELECT * LIMIT 10000`
- [x] Use jq to filter, not SQL WHERE clauses
- [x] Report `total_questions_in_session` as actual count, not 9

## Example: Complete jq Filtering Session

```bash
# Step 1: Export sheet
sqlquery="SELECT * FROM data LIMIT 10000"
# (execute query, save as assessment.json)

# Step 2: Detect first column name
FIRST_COL=$(jq -r 'keys[0]' assessment.json | head -1)
# Result: "branch_assessment_one_row_per_dimension_branch_answers_assessor_classifies"

# Step 3: Filter for session 1 and count
TOTAL_COUNT=$(jq "[.[] | select(.[$FIRST_COL] == 1)] | length" assessment.json)
# Result: 25 (not 9!)

# Step 4: Create filtered questions
jq --arg col "$FIRST_COL" --arg count "$TOTAL_COUNT" \
  '.[] | select(.[$col] == 1)' assessment.json | \
  jq -s --arg count "$TOTAL_COUNT" '{
    session: 1,
    session_transcript: "transcript.txt",
    total_questions_in_session: ($count | tonumber),
    questions: .
  }' > questions_session1.json
```

## Integration with Answer Extraction

Once questions_sessionN.json is created:
1. Extract question_index and discovery_question for each question
2. Search session transcript for answers (ALL questions, not just first 9)
3. Build sessionN_answers.json with all answers
4. Update Excel Column H for ALL rows (may be 25+ rows, not just 9)

## Key Improvements Over SQL Filtering

| Aspect | SQL Filter | jq Filter |
|--------|-----------|-----------|
| **rowid error** | ❌ Fails | ✅ No rowid needed |
| **Column detection** | ❌ Hardcoded column names | ✅ Dynamic detection |
| **Question count** | ❌ Limited to first 9 | ✅ Counts all |
| **Accuracy** | ❌ Misses rows | ✅ Complete export |
| **Flexibility** | ❌ Rigid SQL syntax | ✅ Scriptable jq |

---

## How to Request Sheet Export

When using this skill, provide:
1. Assessment workbook file
2. Sheet name to export (usually "Assessment")
3. Session number to filter for
4. Request: "Export full Assessment sheet, detect column structure, filter for session N, count total questions, output questions_sessionN.json"