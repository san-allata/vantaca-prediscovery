#!/usr/bin/env python3
"""
apply.py — write verdicts into the rubric JSON.

Writes exactly two fields: `classification` and `assessor_notes`. Renders the
assessor note from structured fields so the format cannot drift, and aborts if
any other field would change.

HITL rows deliberately get NO code — `classification` stays null and the note
carries both candidates and the deciding question, so the row shows up as
unclassified everywhere downstream rather than looking decided.

`fb_priority` is never written. It is a business decision; a proposal goes in
the note.

Usage:
    python scripts/apply.py rubric.json build/verdicts.json -o out/rubric.json
                            [--append-notes]
"""
import argparse, json, os, sys
from collections import Counter

CODES = {"AC", "PC", "FB", "NA"}
WRITABLE = {"classification", "assessor_notes"}


def render(r):
    L = []
    L.append(f"BRANCH: {r['branch_clause']}")
    L.append(f"TOWNSQ: {r['townsq_clause']}")
    L.append("DELTA: " + (", ".join(r.get("delta") or []) or "none"))
    if r.get("code"):
        L.append(f"WHY {r['code']}: {r['why']}")
    else:
        a, b = r["hitl_candidates"]
        L.append(f"HITL — candidates {a} or {b}: {r['why']}")
        L.append(f"DECIDING QUESTION: {r['hitl_question']}")
    if r.get("also_requires"):
        L.append(f"Also requires: {r['also_requires']}")
    if r.get("overturned_by"):
        L.append(f"Overturned by: {r['overturned_by']}")
    if r.get("proposed_fb_priority"):
        L.append(f"Proposed FB priority (not written to fb_priority): {r['proposed_fb_priority']}")
    L.append(f"Proximity: {r['proximity']}.")
    note = r.get("confidence_note") or ""
    L.append(f"Confidence: {r['confidence']}" + (f" ({note})" if note else ""))
    if r.get("flags"):
        L.append("Flags: " + ", ".join(r["flags"]))
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rubric")
    ap.add_argument("verdicts")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--append-notes", action="store_true",
                    help="append to an existing assessor_notes instead of skipping the row")
    args = ap.parse_args()

    d = json.load(open(args.rubric, encoding="utf-8"))
    V = json.load(open(args.verdicts, encoding="utf-8"))["verdicts"]
    by = {q["uid"]: q for q in d["questions"]}
    before = {q["uid"]: dict(q) for q in d["questions"]}

    coded, hitl, skipped = [], [], []
    for uid, r in V.items():
        if not (r.get("code") or r.get("hitl_candidates")):
            continue
        q = by[uid]
        if q.get("classification"):
            skipped.append(uid)
            continue
        code = (r.get("code") or "").strip()
        if code and code not in CODES:
            sys.exit(f"{uid}: refusing to write '{code}' — not in {sorted(CODES)}")
        note = render(r)
        existing = (q.get("assessor_notes") or "").strip()
        if existing:
            if not args.append_notes:
                sys.exit(f"{uid} already has an assessor note. Re-run with --append-notes "
                         f"to append, or clear it deliberately. Never silently overwrite.")
            note = existing + " | " + note
        if code:
            q["classification"] = code
            coded.append(uid)
        else:
            hitl.append(uid)          # classification stays null by design
        q["assessor_notes"] = note

    changed = Counter()
    for q in d["questions"]:
        for k, v in q.items():
            if before[q["uid"]].get(k) != v:
                changed[k] += 1
    illegal = {k: v for k, v in changed.items() if k not in WRITABLE}
    if illegal:
        sys.exit(f"ABORT: would have modified {illegal}")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    json.dump(d, open(args.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    print(f"coded {len(coded)}  HITL (left unclassified by design) {len(hitl)}  "
          f"skipped (already classified) {len(skipped)}")
    print("code mix: " + "  ".join(f"{k}={v}" for k, v in
          Counter(by[u]["classification"] for u in coded).most_common()))
    print(f"HITL rows: {' '.join(sorted(hitl))}")
    print(f"fields changed: {dict(changed)}")
    print(f"fb_priority written: {changed.get('fb_priority', 0)} (must be 0)")
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
