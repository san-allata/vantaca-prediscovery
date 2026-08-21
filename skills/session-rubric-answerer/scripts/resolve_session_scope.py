import sys, json, os, re

WORKDIR = os.getcwd()


def load_input():
    p = os.path.join(WORKDIR, "input.json")
    if not os.path.exists(p):
        print(json.dumps({"error": "input.json not found. Provide live_interview_tracker, rubric_mapping, and assessment_rows."}))
        sys.exit(1)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def norm(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[\u2018\u2019]", "'", s)
    s = re.sub(r"[\u201c\u201d]", '"', s)
    return s


def main():
    data = load_input()
    session = data.get("session")
    tracker_rows = data.get("live_interview_tracker", [])
    mapping_rows = data.get("rubric_mapping", [])
    assessment_rows = data.get("assessment_rows", [])

    id_key = data.get("tracker_id_field", "ID")
    planned_q_key = data.get("tracker_planned_question_field", "Planned question")
    must_capture_key = data.get("tracker_must_capture_field", "Must Capture")

    mapping_id_key = data.get("mapping_id_field", "Planned Question ID")
    mapping_question_key = data.get("mapping_question_field", "Exact Rubric Question")

    assessment_row_key = data.get("assessment_row_field", "row")
    assessment_question_key = data.get("assessment_question_field", "Discovery Question")

    session_prefix = f"S{session}-"

    tracker_by_id = {}
    for t in tracker_rows:
        tid = str(t.get(id_key, ""))
        if tid.startswith(session_prefix):
            tracker_by_id[tid] = {
                "planned_question": t.get(planned_q_key),
                "must_capture": t.get(must_capture_key),
            }

    assessment_by_norm_q = {}
    duplicate_questions = set()
    for a in assessment_rows:
        q = norm(a.get(assessment_question_key))
        if not q:
            continue
        if q in assessment_by_norm_q:
            duplicate_questions.add(q)
        assessment_by_norm_q[q] = a.get(assessment_row_key)

    resolved = []
    unresolved = []

    for m in mapping_rows:
        pid = str(m.get(mapping_id_key, ""))
        if not pid.startswith(session_prefix):
            continue
        exact_q = m.get(mapping_question_key)
        ctx = tracker_by_id.get(pid, {})
        row = assessment_by_norm_q.get(norm(exact_q))
        record = {
            "planned_question_id": pid,
            "planned_question": ctx.get("planned_question"),
            "must_capture": ctx.get("must_capture"),
            "exact_rubric_question": exact_q,
            "master_rubric_row": row,
        }
        if row is None:
            unresolved.append(record)
        else:
            resolved.append(record)

    result = {
        "session": session,
        "planned_question_ids_in_scope": sorted(tracker_by_id.keys()),
        "mapped_question_count": len(resolved) + len(unresolved),
        "resolved_count": len(resolved),
        "unresolved_count": len(unresolved),
        "ambiguous_duplicate_questions_in_assessment": sorted(duplicate_questions),
        "resolved": resolved,
        "unresolved": unresolved,
    }

    out_path = os.path.join(WORKDIR, f"session_{session}_scope.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
