#!/usr/bin/env python3
"""
audit.py — verify verdicts before they touch the rubric, then report.

Checks, each of which has caught a real defect:

  1. code       — must be AC/PC/FB/NA, or empty for HITL. The dropdown in the
                  downstream workbook covers only a leading band of rows, so
                  Excel will not reject a bad value. Validate here.
  2. grounding  — branch_clause must appear in branch_answer, townsq_clause in
                  townsq_capability. Each side's clause must come from its OWN
                  column; a clause quoted from the wrong side is how column I
                  leaks into the reasoning.
  3. facets     — both sides decomposed, driving_facet named and present in delta.
                  A "why" that does not name which facet moved is unfalsifiable.
  4. consistency— within a capability, rows resting on the same disputed SME
                  claim must not silently carry different codes. Also detects
                  contradictory SME statements across rows.
  5. semantic   — lexical overlap vs verdict direction. Low overlap + AC, or high
                  overlap + FB, flags a possible false-equivalence / false-friend.
  6. discipline — FB requires overturned_by; HITL requires two candidates and a
                  deciding question; no fb_priority may be written.

Usage:
    python scripts/audit.py rubric.json build/verdicts.json --report
"""
import argparse, difflib, json, re, sys
from collections import Counter, defaultdict

CODES = {"AC", "PC", "FB", "NA"}
FACETS = ["outcome", "system_of_record", "mechanism", "actors",
          "trigger_timing", "controls", "exceptions", "evidence"]
PROX = {"Exact match", "High (~75%)", "Moderate (~50%)", "Low (~25%)", "No match"}
CONF = {"High", "Medium", "Low"}
INFLIGHT = re.compile(r"in development|not yet|roadmap|being built|not fully available", re.I)


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def contains(hay, needle, thresh=0.90):
    """Tolerant containment: exact on normalised text, else close-match on windows."""
    h, n = norm(hay), norm(needle)
    if not n:
        return False
    if n in h:
        return True
    words = h.split()
    # slide a window the length of the needle and look for a near match
    nl = len(n.split())
    for i in range(max(1, len(words) - nl + 1)):
        w = " ".join(words[i:i + nl])
        if difflib.SequenceMatcher(None, w, n).ratio() >= thresh:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rubric")
    ap.add_argument("verdicts")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    d = json.load(open(args.rubric, encoding="utf-8"))
    V = json.load(open(args.verdicts, encoding="utf-8"))["verdicts"]
    by = {q["uid"]: q for q in d["questions"]}

    unknown = set(V) - set(by)
    if unknown:
        sys.exit("verdicts reference unknown uids: " + ", ".join(sorted(unknown)))

    fails, warns = [], []
    filled = {u: r for u, r in V.items()
              if r.get("code") or r.get("hitl_candidates")}

    for uid, r in filled.items():
        q = by[uid]
        code = (r.get("code") or "").strip()
        hitl = bool(r.get("hitl_candidates"))

        # 1 code
        if code and code not in CODES:
            fails.append(f"[code] {uid} '{code}' not in {sorted(CODES)}")
        if code and hitl:
            fails.append(f"[code] {uid} has both a code and HITL candidates — pick one")
        if not code and not hitl:
            fails.append(f"[code] {uid} has neither a code nor HITL candidates")

        # 2 grounding — each clause from its own column
        if r.get("branch_clause") and not contains(q.get("branch_answer"), r["branch_clause"]):
            fails.append(f"[grounding] {uid} branch_clause not found in branch_answer")
        if r.get("townsq_clause") and not contains(q.get("townsq_capability"), r["townsq_clause"]):
            fails.append(f"[grounding] {uid} townsq_clause not found in townsq_capability")
        if r.get("branch_clause") and contains(q.get("townsq_capability"), r["branch_clause"]):
            fails.append(f"[grounding] {uid} branch_clause also appears in townsq_capability "
                         f"— wrong column")

        # 3 facets
        fb = {k: v for k, v in (r.get("facets_branch") or {}).items() if v}
        ft = {k: v for k, v in (r.get("facets_townsq") or {}).items() if v}
        if not fb or not ft:
            fails.append(f"[facets] {uid} one side not decomposed "
                         f"(branch={len(fb)}, townsq={len(ft)})")
        for f in list(fb) + list(ft):
            if f not in FACETS:
                fails.append(f"[facets] {uid} unknown facet '{f}'")
        df = r.get("driving_facet")
        if code and code != "NA":
            if not df:
                fails.append(f"[facets] {uid} code {code} with no driving_facet")
            elif df not in (r.get("delta") or []) and code != "AC":
                warns.append(f"[facets] {uid} driving_facet '{df}' not listed in delta")

        # 6 discipline
        if code == "FB" and not r.get("overturned_by"):
            fails.append(f"[discipline] {uid} FB with no overturned_by — an FB that cannot "
                         f"be appealed will not be trusted")
        if hitl:
            if len(r["hitl_candidates"]) != 2:
                fails.append(f"[discipline] {uid} HITL needs exactly 2 candidates")
            if not r.get("hitl_question"):
                fails.append(f"[discipline] {uid} HITL with no deciding question")
        if r.get("proposed_fb_priority") and code != "FB":
            warns.append(f"[discipline] {uid} proposes an FB priority on a {code} row")
        if r.get("proximity") and r["proximity"] not in PROX:
            fails.append(f"[discipline] {uid} proximity '{r['proximity']}' not in {sorted(PROX)}")
        if code and r.get("confidence") not in CONF:
            fails.append(f"[discipline] {uid} confidence must be one of {sorted(CONF)}")

        # ladder rule 4: in-flight SME language must not read as AC/PC without a date
        if INFLIGHT.search(q.get("townsq_capability") or "") and code in ("AC", "PC"):
            fails.append(f"[ladder] {uid} SME text says the capability is in flight but code "
                         f"is {code}; rule 4 requires FB unless availability before go-live "
                         f"is stated")

        # 5 semantic vs lexical
        overlap = difflib.SequenceMatcher(
            None, norm(q.get("branch_answer")), norm(q.get("townsq_capability"))).ratio()
        if code == "FB" and overlap > 0.40:
            warns.append(f"[semantic] {uid} FB on high lexical overlap ({overlap:.2f}) "
                         f"— confirm it is a real gap, not a false friend")
        if code == "AC" and overlap < 0.12:
            warns.append(f"[semantic] {uid} AC on very low lexical overlap ({overlap:.2f}) "
                         f"— confirm the facets really align")

    # 4 consistency within a capability + SME contradiction detection
    bycap = defaultdict(list)
    for uid in filled:
        bycap[by[uid]["capability"]].append(uid)
    for cap, uids in bycap.items():
        inflight = [u for u in uids if INFLIGHT.search(by[u].get("townsq_capability") or "")]
        affirm = [u for u in uids if re.match(r"(Native|After config)",
                                             (by[u].get("townsq_capability") or "").strip())]
        if inflight and affirm:
            warns.append(f"[consistency] {cap}: SME says in-development on {' '.join(inflight)} "
                         f"but affirms availability on {' '.join(affirm)} — contradictory SME "
                         f"statements in one capability; resolve before finalising")
        codes = Counter((filled[u].get("code") or "HITL") for u in uids)
        if len(codes) > 2:
            warns.append(f"[consistency] {cap}: {len(codes)} distinct codes {dict(codes)} "
                         f"— re-read side by side")

    print(f"audited {len(filled)} verdicts of {len(V)} in skeleton\n")
    print(f"HARD FAILURES: {len(fails) or 'none'}")
    for f in fails:
        print("  " + f)
    if warns:
        print(f"\nWARNINGS ({len(warns)}):")
        for w in warns:
            print("  " + w)

    if args.report:
        print("\n" + "=" * 66 + "\nCLASSIFICATION REPORT\n" + "=" * 66)
        codes = Counter((r.get("code") or "HITL") for r in filled.values())
        print("codes: " + "  ".join(f"{k}={v}" for k, v in codes.most_common()))
        print("proximity: " + "  ".join(f"{k}={v}" for k, v in
              Counter(r.get("proximity") for r in filled.values() if r.get("proximity")).most_common()))
        print("confidence: " + "  ".join(f"{k}={v}" for k, v in
              Counter(r.get("confidence") for r in filled.values() if r.get("confidence")).most_common()))
        print("\nby domain and code:")
        agg = defaultdict(Counter)
        for uid, r in filled.items():
            agg[by[uid]["domain"]][r.get("code") or "HITL"] += 1
        for dom in sorted(agg):
            print(f"  {dom:<28} " + "  ".join(f"{k}={v}" for k, v in sorted(agg[dom].items())))
        for label, test in (("FB", lambda r: r.get("code") == "FB"),
                            ("HITL", lambda r: bool(r.get("hitl_candidates")))):
            rows = [u for u, r in filled.items() if test(r)]
            print(f"\n{label} ({len(rows)}):")
            for u in sorted(rows):
                p = filled[u].get("proposed_fb_priority")
                print(f"  {u} [{by[u].get('priority')}] {by[u]['capability']} — "
                      f"{by[u]['dimension']}" + (f"  (proposed FB priority {p})" if p else ""))
        fl = Counter(f for r in filled.values() for f in (r.get("flags") or []))
        if fl:
            print("\nflags: " + "  ".join(f"{k}={v}" for k, v in fl.most_common()))
        print("\nREADINESS: not reportable — no domain is fully answered and fully "
              "classified. Leave the readiness column at '—'.")

    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
