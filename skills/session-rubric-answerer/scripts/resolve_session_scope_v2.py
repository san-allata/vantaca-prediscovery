#!/usr/bin/env python3
"""
resolve_session_scope_v2.py  —  TEST COPY (v2)

Key difference from v1: rubric data is passed IN via input.json
under the key "rubric_index" (a list of dicts). No file I/O needed.

Input (input.json):
  {
    "mapping_rows": [
      { "uid": "Q0001", "qid": "1.1.1",
        "exact_master_rubric_question": "How many...",
        "planned_question_id": "Q1", "session": 1 }
    ],
    "rubric_index": [
      { "uid": "Q0001", "qid": "1.1.1", "row": 5,
        "domain": "Platform Foundation", "cap_num": 1.1,
        "capability": "General System Access",
        "dimension": "Multi-system navigation",
        "priority": "P0",
        "discovery_question": "How many...",
        "townsq_capability": "After config — ..." }
    ]
  }

Output (stdout JSON):
  { "resolved": [...], "unresolved": [...] }
"""

import json
import os
import re
import sys


def normalize(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_lookup(rubric_rows: list) -> tuple:
    uid_lookup  = {}
    qid_lookup  = {}
    text_lookup = {}
    for r in rubric_rows:
        uid = str(r.get("uid", "")).strip().upper()
        qid = str(r.get("qid", "")).strip()
        dq  = normalize(r.get("discovery_question", ""))
        if uid:
            uid_lookup[uid] = r
        if qid:
            qid_lookup[qid] = r
        if dq:
            text_lookup[dq] = r
    return uid_lookup, qid_lookup, text_lookup


def main():
    input_path = os.path.join(os.getcwd(), "input.json")
    if not os.path.exists(input_path):
        print(json.dumps({"resolved": [], "unresolved": [],
                          "error": "input.json not found"}))
        return

    with open(input_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    mapping_rows = payload.get("mapping_rows", [])
    rubric_index = payload.get("rubric_index", [])

    # Fast-fail
    if not mapping_rows:
        print(json.dumps({"resolved": [], "unresolved": []}))
        return

    if not rubric_index:
        print(json.dumps({
            "resolved": [],
            "unresolved": [{"reason": "rubric_index not provided in input"}]
        }))
        return

    uid_lookup, qid_lookup, text_lookup = build_lookup(rubric_index)

    resolved   = []
    unresolved = []

    for m in mapping_rows:
        hit, method = None, None

        # 1. UID match
        m_uid = str(m.get("uid", "")).strip().upper()
        if m_uid and m_uid in uid_lookup:
            hit, method = uid_lookup[m_uid], "uid"

        # 2. QID match
        if hit is None:
            m_qid = str(m.get("qid", "")).strip()
            if m_qid and m_qid in qid_lookup:
                hit, method = qid_lookup[m_qid], "qid"

        # 3. Normalized text match
        if hit is None:
            m_text = normalize(m.get("exact_master_rubric_question", ""))
            if m_text and m_text in text_lookup:
                hit, method = text_lookup[m_text], "normalized_text"

        if hit is not None:
            merged = dict(m)
            merged.update({
                "rubric_row":         hit["row"],
                "domain":             hit["domain"],
                "cap_num":            hit["cap_num"],
                "capability":         hit["capability"],
                "dimension":          hit["dimension"],
                "priority":           hit["priority"],
                "discovery_question": hit["discovery_question"],
                "townsq_capability":  hit.get("townsq_capability", ""),
                "_match_method":      method,
            })
            resolved.append(merged)
        else:
            unresolved.append({
                "planned_question_id":          m.get("planned_question_id", ""),
                "uid":                          m.get("uid", ""),
                "qid":                          m.get("qid", ""),
                "exact_master_rubric_question": m.get("exact_master_rubric_question", ""),
                "reason": "no UID / QID / normalized text match in rubric_index",
            })

    print(json.dumps({
        "resolved":   resolved,
        "unresolved": unresolved,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
