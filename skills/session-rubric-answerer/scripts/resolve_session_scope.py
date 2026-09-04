"""
resolve_session_scope.py

Matches a session's Session-Mapping question rows to their exact Master Rubric
Assessment-sheet rows by normalized text comparison. Never fuzzy-matches --
an unresolved question is reported, not guessed.

Input (input.json in the working directory), shape:
{
  "mapping_rows": [
    {"planned_question_id": "S3-Q1", "planned_question": "...", "exact_master_rubric_question": "...",
     "uid": "Q0089", "qid": "6.1.1", "capability": "Accounts Payable", "dimension": "...", "priority": "P0"},
    ...
  ],
  "assessment_questions": [
    {"row": 5, "discovery_question": "...", "uid": "Q0001"},
    ...
  ]
}

Matching is attempted in order:
  1. By UID, if both sides carry one and they agree (fastest, most reliable).
  2. By normalized discovery_question text equality.

Output (printed to stdout as JSON):
{
  "resolved": [ {"planned_question_id":..., "planned_question":..., "exact_master_rubric_question":...,
                  "master_rubric_row":5, "uid":"Q0001", "matched_by":"uid"|"text"} ],
  "unresolved": [ {"planned_question_id":..., "exact_master_rubric_question":..., "reason":"..."} ]
}
"""
import json
import re
import sys


def normalize(text):
    if text is None:
        return ""
    t = str(text)
    # normalize curly quotes/dashes to plain equivalents
    t = t.replace("\u2019", "'").replace("\u2018", "'")
    t = t.replace("\u201c", '"').replace("\u201d", '"')
    t = t.replace("\u2014", "-").replace("\u2013", "-")
    t = t.strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = t.rstrip(" ?.!")
    return t


def main():
    with open("input.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    mapping_rows = data.get("mapping_rows", [])
    assessment_questions = data.get("assessment_questions", [])

    by_uid = {}
    by_text = {}
    for aq in assessment_questions:
        uid = aq.get("uid")
        if uid:
            by_uid[uid] = aq
        norm = normalize(aq.get("discovery_question"))
        if norm:
            by_text.setdefault(norm, []).append(aq)

    resolved = []
    unresolved = []

    for mr in mapping_rows:
        pqid = mr.get("planned_question_id")
        exact_q = mr.get("exact_master_rubric_question")
        uid = mr.get("uid")

        match = None
        matched_by = None

        if uid and uid in by_uid:
            match = by_uid[uid]
            matched_by = "uid"
        else:
            norm = normalize(exact_q)
            candidates = by_text.get(norm, [])
            if len(candidates) == 1:
                match = candidates[0]
                matched_by = "text"
            elif len(candidates) > 1:
                # ambiguous text match -- do not guess
                unresolved.append({
                    "planned_question_id": pqid,
                    "exact_master_rubric_question": exact_q,
                    "reason": f"ambiguous: {len(candidates)} rows share this normalized question text"
                })
                continue

        if match is None:
            unresolved.append({
                "planned_question_id": pqid,
                "exact_master_rubric_question": exact_q,
                "reason": "no normalized text match and no UID match found in Master Rubric"
            })
            continue

        resolved.append({
            "planned_question_id": pqid,
            "planned_question": mr.get("planned_question"),
            "exact_master_rubric_question": exact_q,
            "master_rubric_row": match.get("row"),
            "uid": match.get("uid"),
            "matched_by": matched_by,
        })

    print(json.dumps({"resolved": resolved, "unresolved": unresolved}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
