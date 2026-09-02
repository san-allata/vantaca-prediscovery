# rubric-classifier

JSON in, JSON out. Compares `branch_answer` against `townsq_capability` and
records the gap as `classification` (AC / PC / FB / NA) plus a structured
`assessor_notes`. Writes those two fields and nothing else.

Python 3.8+, stdlib only. Runs after the extractor; never touches `branch_answer`.

## Layout

    SKILL.md                the judgment: facets, decision ladder, note format
    scripts/plan.py         triage, column-I pathology profile, verdicts skeleton
    scripts/audit.py        verify verdicts BEFORE they touch the rubric
    scripts/apply.py        render notes, write classification only
    scripts/check_rollup.py verify the .xlsx roll-up reflects what you wrote (read-only)
    fixtures/               a complete worked run (12 rows), for testing your setup

## Run

```bash
python scripts/plan.py rubric.json -o build/
# fill facets / entailment / code / clauses / proximity / confidence in
# build/verdicts.json, working one capability at a time

python scripts/audit.py rubric.json build/verdicts.json --report   # must exit 0

python scripts/apply.py rubric.json build/verdicts.json -o out/rubric.json
# add --append-notes if rows already carry an assessor note

# after your JSON->xlsx converter runs, verify the roll-up:
python scripts/check_rollup.py updated.xlsx
```

## Verify your install

```bash
python scripts/audit.py fixtures/rubric_in.json fixtures/verdicts.json --report
# expect: HARD FAILURES: none, and 2 consistency warnings

python scripts/apply.py fixtures/rubric_in.json fixtures/verdicts.json \
    -o /tmp/check.json --append-notes
# expect: fields changed: {'classification': 10, 'assessor_notes': 12}
#         fb_priority written: 0
```

## Deliberate design choices

- **HITL rows get no code.** `classification` stays null so the row reads as
  unclassified everywhere downstream, rather than looking decided. Both
  candidates and the deciding question go in the note.
- **`fb_priority` is never written.** Priority is a business decision. A
  proposal appears in the note text only.
- **No readiness number, ever.** The gate holds until a domain is fully answered
  and fully classified.
- **`check_rollup.py` reports, it does not repair.** Rewriting formula columns is
  a deliberate, separately verified pass, not a side effect of a conversion. Run
  it on the first conversion and on any new rubric revision.

## Known defects in this workbook family

Found by `check_rollup.py` on a real file. Expect them:

- **AC#/FB#/PC# helper columns mis-anchored.** The formula on a row reads the
  classification of a *different* row (observed: 94 anchored, 207 mis-anchored,
  340 missing, out of 641). Those columns feed the PC / AC / FB worklist sheets
  via `MATCH`, so those tabs silently drop real rows and list unrelated ones.
  The Summary is unaffected because it reads the classification column directly
  with `SUMPRODUCT` — so the domain roll-up can be correct while the worklists
  are wrong. Do not hand out the worklist tabs until this is fixed.
- **Summary counts pointing at the wrong column**, stale ranges, and a stale
  domain roster. Not present on the file checked, but checks 1-3 exist because
  they have been.
- **`soffice` called bare hangs in a container** (AF_UNIX sockets under seccomp).
  If your JSON-to-xlsx converter shells out to `soffice` for recalc, run with
  recalc disabled and recalculate with a sandbox-safe wrapper instead.
- **Threaded comments do not survive an openpyxl round-trip.** Re-add from the
  original if the workbook carried reviewer comments.
