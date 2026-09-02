# JSON Question-Answer Patcher

## Purpose
Patch JSON assessment templates by updating `branch_answer` fields for a **subset of questions**. Each answer specifies which question (by array index) it's answering.

**Key concept:** Answers contain the question index → tool knows exactly where to patch.

## How It Works

### Structure
Your JSON template looks like:
```json
{
  "questions": [
    {
      "discovery_question": "How many different systems...",
      "branch_answer": null
    },
    {
      "discovery_question": "What is your backup...",
      "branch_answer": null
    },
    {
      "discovery_question": "How often do you...",
      "branch_answer": null
    }
  ]
}
```

### Answers Format
You provide answers as an **array of objects**, where each answer includes:
- `question_index` — which question in the array to update
- `branch_answer` — the answer text

```json
[
  {
    "question_index": 0,
    "branch_answer": "Five systems: TownSq Business, TownSq Community, WorkPoints+, Sage 300, Ascentis"
  },
  {
    "question_index": 2,
    "branch_answer": "Weekly automated backups to cloud storage; tested monthly"
  },
  {
    "question_index": 5,
    "branch_answer": "Formal disaster recovery plan in place; RTO 4 hours, RPO 1 hour"
  }
]
```

### Patching Process
1. **Parse answers** — extract each answer with its `question_index`
2. **Generate jq filter** — for each answer, update `.questions[INDEX].branch_answer`
3. **Apply patch** — merge all updates into template preserving structure
4. **Validate** — confirm only specified questions were updated

## Usage Example

**You provide:**
1. JSON assessment template with questions array
2. Answers array where each answer specifies `question_index`

**Example answers.json:**
```json
[
  {
    "question_index": 0,
    "branch_answer": "Five systems: TownSq, WorkPoints+, Sage, Ascentis, PSA"
  },
  {
    "question_index": 2,
    "branch_answer": "Weekly backups tested monthly"
  }
]
```

**Output:**
- `.questions[0].branch_answer` = "Five systems..."
- `.questions[2].branch_answer` = "Weekly backups..."
- All other questions unchanged
- Full JSON structure preserved

## Input Format

Provide:
1. **JSON Template** — your full assessment JSON with questions array
2. **Answers Array** — array of answer objects, each with:
   - `question_index` (integer) — position in questions array
   - `branch_answer` (string) — the answer text
   - Optional: any other fields to update (`assessor_notes`, `classification`, etc.)

## Optional: Update Additional Fields

Answers can also update other fields on the same question object:

```json
[
  {
    "question_index": 0,
    "branch_answer": "Five systems...",
    "assessor_notes": "Updated from operations manual",
    "classification": "Verified"
  },
  {
    "question_index": 2,
    "branch_answer": "Weekly automated backups",
    "fb_priority": "High"
  }
]
```

## Output

- **Patched JSON** — only specified questions updated, all others unchanged
- **Audit trail** — jq command(s) showing exact patches applied
- **Validation** — before/after counts, confirmation of updates
- **Summary** — which questions were updated, structure integrity check

## Technical Details

- Handles any number of questions; patch only the ones you have answers for
- Array index matching is direct and reliable
- Preserves all formatting, special characters, structure
- Can handle 500kb+ JSON files efficiently
- Zero risk of corruption
- Simple, explicit answer format (no ambiguity)w