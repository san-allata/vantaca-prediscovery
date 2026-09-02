#!/usr/bin/env python3
"""
plan.py — triage the rubric for classification and emit the verdicts skeleton.

Measures, never assumes. Reports the pathologies in column I that defeat
prefix-keyed classification, and refuses to put a row in the work set unless
BOTH sides are substantive.

Usage:
    python scripts/plan.py rubric.json -o build/
"""
import argparse, json, os, re
from collections import Counter

PREFIXES = ["Native", "After config", "Partial", "Change in-progress", "Not supported"]
CODES = ["AC", "PC", "FB", "NA"]
STUB_LEN = 28
NOANS = re.compile(r"no answer found", re.I)
LEAK = re.compile(r"^(FB|AC|PC|NA)\s*[—\-:]", re.I)
SPEAKER = re.compile(r"^[A-Za-z][A-Za-z&.\s]{0,14}\s*[-:]\s")
INFLIGHT = re.compile(r"in development|not yet|roadmap|being built|not fully available", re.I)
NEGATION = re.compile(r"does not support|not supported|no dedicated|cannot|not currently", re.I)


def sme_state(i):
    i = (i or "").strip()
    if not i:
        return "empty"
    if i.upper().startswith("TBD"):
        return "tbd"
    if len(i) < STUB_LEN:
        return "stub"
    if NOANS.search(i):
        return "no_answer_found"
    return "substantive"


def marker(i):
    i = (i or "").strip()
    if LEAK.match(i):
        return "classification_leakage"
    for p in PREFIXES:
        if i.startswith(p):
            return p
    if SPEAKER.match(i):
        return "speaker_prefix"
    return "no_prefix"


def conf_ceiling(i):
    """What confidence a verdict on this SME cell can legitimately reach."""
    i = i or ""
    if "~" in i or re.search(r"confirm with product", i, re.I):
        return "Medium (unconfirmed marker)"
    if INFLIGHT.search(i):
        return "Medium (in-flight)"
    if any(i.strip().startswith(p) for p in PREFIXES):
        return "High" + (" (prefix + confirmed)" if "\u2713" in i else " (prefix)")
    if NEGATION.search(i):
        return "High (explicit negation)"
    return "Low (prose, no support level)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rubric")
    ap.add_argument("-o", "--outdir", default="build")
    args = ap.parse_args()

    d = json.load(open(args.rubric, encoding="utf-8"))
    Q = d["questions"]

    buckets = {k: [] for k in ("classifiable", "blocked_sme", "blocked_branch",
                               "already_classified", "placeholder")}
    for q in Q:
        h = (q.get("branch_answer") or "").strip()
        st = sme_state(q.get("townsq_capability"))
        if q.get("is_placeholder_question"):
            buckets["placeholder"].append(q["uid"])
        elif q.get("classification"):
            buckets["already_classified"].append(q["uid"])
        elif not h or h.startswith("Not Found"):
            buckets["blocked_branch"].append(q["uid"])
        elif st != "substantive":
            buckets["blocked_sme"].append(q["uid"])
        else:
            buckets["classifiable"].append(q["uid"])

    print(f"RUBRIC {os.path.basename(args.rubric)}  rows {len(Q)}")
    for k, v in buckets.items():
        print(f"  {k:20s} {len(v)}")

    # sentinels: a J value that is not a real code counts as unclassified everywhere else
    bad = [(q["uid"], q["classification"]) for q in Q
           if q.get("classification") and q["classification"] not in CODES]
    print(f"\n  non-code values in classification (treat as unclassified): {len(bad)}")
    for uid, v in bad:
        print(f"    {uid}: {v!r}")

    # codes sitting on rows with no branch answer are unsupported
    unsupported = [q["uid"] for q in Q if q.get("classification") in CODES
                   and not (q.get("branch_answer") or "").strip()]
    print(f"  existing codes on rows with NO branch answer (unsupported): "
          f"{len(unsupported)} {' '.join(unsupported)}")

    print("\n  column I marker distribution (all rows with content):")
    for k, v in Counter(marker(q.get("townsq_capability")) for q in Q
                        if (q.get("townsq_capability") or "").strip()).most_common():
        print(f"    {k:26s} {v}")

    work = [q for q in Q if q["uid"] in set(buckets["classifiable"])]
    print(f"\n  confidence ceiling across the {len(work)} classifiable rows:")
    for k, v in Counter(conf_ceiling(q.get("townsq_capability")) for q in work).most_common():
        print(f"    {k:34s} {v}")
    leak = [q["uid"] for q in work if marker(q.get("townsq_capability")) == "classification_leakage"]
    if leak:
        print(f"\n  !! SME wrote a verdict into column I on: {' '.join(leak)}")
        print("     Confirm and cite it; do not re-derive. Judgment belongs in `classification`.")

    per_cap = Counter(q["capability"] for q in work)
    print("\n  work set by capability (classify a whole capability at a time):")
    for cap, n in per_cap.most_common():
        print(f"    {cap:<44} {n}")

    os.makedirs(args.outdir, exist_ok=True)
    FACETS = ["outcome", "system_of_record", "mechanism", "actors",
              "trigger_timing", "controls", "exceptions", "evidence"]
    skel = {"verdicts": {
        q["uid"]: {
            "_capability": q["capability"],
            "_dimension": q["dimension"],
            "_priority": q.get("priority"),
            "_question": q["discovery_question"],
            "_sme_marker": marker(q.get("townsq_capability")),
            "_confidence_ceiling": conf_ceiling(q.get("townsq_capability")),
            "facets_branch": {f: "" for f in FACETS},
            "facets_townsq": {f: "" for f in FACETS},
            "entailment": {"townsq_produces_branch_outcome": "", "branch_depends_on_uncovered": ""},
            "code": "", "delta": [], "driving_facet": "",
            "branch_clause": "", "townsq_clause": "", "why": "",
            "also_requires": "", "overturned_by": "",
            "proximity": "", "confidence": "", "confidence_note": "",
            "flags": [], "hitl_candidates": [], "hitl_question": "",
            "proposed_fb_priority": "",
        }
        for q in sorted(work, key=lambda q: (q["capability"], q["uid"]))
    }}
    path = os.path.join(args.outdir, "verdicts.json")
    if os.path.exists(path):
        print(f"\n!! {path} exists — not overwriting.")
    else:
        json.dump(skel, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"\n-> {path}  ({len(skel['verdicts'])} rows to classify)")


if __name__ == "__main__":
    main()
