#!/bin/bash
# jq-based JSON question-answer patcher using array index matching
# Each answer must have question_index and branch_answer
# Usage: ./patcher.sh template.json answers.json [output.json]

TEMPLATE="$1"
ANSWERS="$2"
OUTPUT="${3:-patched.json}"

if [[ ! -f "$TEMPLATE" ]]; then
    echo "Error: Template file not found: $TEMPLATE"
    exit 1
fi

if [[ ! -f "$ANSWERS" ]]; then
    echo "Error: Answers file not found: $ANSWERS"
    exit 1
fi

echo "Patching with array index matching..."

# Validate answers format
jq -e '.[] | has("question_index") and has("branch_answer")' "$ANSWERS" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: Each answer must have question_index and branch_answer fields"
    exit 1
fi

# Apply patches using reduce (exclude question_index from being added to template)
jq --slurpfile answers "$ANSWERS" '. as $template | reduce $answers[0][] as $answer ($template; .questions[$answer.question_index] |= . + ($answer | del(.question_index)))' "$TEMPLATE" > "$OUTPUT"

if [ $? -eq 0 ]; then
    echo "✓ Patching complete: $OUTPUT"
    echo ""
    echo "Statistics:"
    TOTAL=$(jq '.questions | length' "$OUTPUT")
    ANSWERED=$(jq '.questions | map(select(.branch_answer != null)) | length' "$OUTPUT")
    ANSWERS_APPLIED=$(jq 'length' "$ANSWERS")
    echo "  Total questions: $TOTAL"
    echo "  Questions with branch_answer: $ANSWERED"
    echo "  Answers applied in this patch: $ANSWERS_APPLIED"
    echo ""
    echo "Updated question indices: $(jq -r --slurpfile ans "$ANSWERS" '$ans[0][].question_index' "$ANSWERS" | paste -sd ',' -)"
else
    echo "✗ Patching failed"
    exit 1
fi
