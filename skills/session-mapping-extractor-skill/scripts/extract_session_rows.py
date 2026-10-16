#!/usr/bin/env python3
"""
extract_session_rows.py

Extracts all rubric mapping rows for a single session number from the
Sessions Master Rubric Mapping CSV (attached to the chat or provided as input).

Input  (input.json): { "session": <int or str> }
Output (stdout):     JSON array of row objects, columns B-I only,
                     sorted by planned_question_id (B) then priority (H).

Priority sort order: P0 < P1 < P2 < P3
"""

import json
import sys
import csv
import os
import re

# ---------------------------------------------------------------------------
# Load input
# ---------------------------------------------------------------------------
try:
    with open("input.json") as f:
        params = json.load(f)
except FileNotFoundError:
    print(json.dumps({"error": "input.json not found. Provide {\"session\": <N>} as inputData."}), file=sys.stderr)
    sys.exit(1)
except json.JSONDecodeError as e:
    print(json.dumps({"error": f"input.json is not valid JSON: {e}"}), file=sys.stderr)
    sys.exit(1)

if "session" not in params:
    print(json.dumps({"error": "Missing required field 'session' in input.json."}), file=sys.stderr)
    sys.exit(1)

target_session = str(params["session"]).strip()

# ---------------------------------------------------------------------------
# Locate the CSV file
# ---------------------------------------------------------------------------
CSV_SEARCH_NAMES = [
    "Sessions_1-6_Master_Rubric_Mapping_20261015.csv",
    "Sessions_1-6_Master_Rubric_Mapping.csv",
    "Master_Rubric_Mapping.csv",
]

csv_path = None

# 1. Check working directory and common upload paths
for candidate in CSV_SEARCH_NAMES:
    for base in [".", "/tmp", "/uploads", "/data"]:
        full = os.path.join(base, candidate)
        if os.path.isfile(full):
            csv_path = full
            break
    if csv_path:
        break

# 2. Walk working directory for any *mapping*.csv or *rubric*.csv
if not csv_path:
    for root, dirs, files in os.walk("."):
        for fname in files:
            if fname.lower().endswith(".csv") and (
                "mapping" in fname.lower() or "rubric" in fname.lower()
            ):
                csv_path = os.path.join(root, fname)
                break
        if csv_path:
            break

# 3. If still not found, check if rows were passed directly in input
if not csv_path and "rows" in params:
    # Accept pre-loaded rows directly in input
    raw_rows = params["rows"]
else:
    raw_rows = None

if not csv_path and raw_rows is None:
    print(
        json.dumps({
            "error": "CSV file not found. Attach the Sessions Master Rubric Mapping CSV to the chat, "
                     "or pass rows directly as input.json[\"rows\"]."
        }),
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Column name normalisation
# The CSV uses original headers; map them to canonical keys.
# ---------------------------------------------------------------------------
COL_ALIASES = {
    # canonical_key: list of possible original header substrings (case-insensitive)
    "session":                    ["session"],
    "planned_question_id":        ["planned question id"],
    "planned_question":           ["planned question"],
    "uid":                        ["uid"],
    "qid":                        ["qid"],
    "capability":                 ["capability"],
    "dimension":                  ["dimension"],
    "priority":                   ["priority"],
    "exact_master_rubric_question": ["exact master rubric question"],
}


def normalise_header(raw_headers):
    """Return a dict mapping canonical_key -> index in the CSV row."""
    mapping = {}
    for canonical, aliases in COL_ALIASES.items():
        for idx, h in enumerate(raw_headers):
            h_clean = h.strip().lower()
            for alias in aliases:
                if alias in h_clean:
                    mapping[canonical] = idx
                    break
            if canonical in mapping:
                break
    return mapping


# ---------------------------------------------------------------------------
# Parse CSV or use pre-loaded rows
# ---------------------------------------------------------------------------
priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def sort_key(row):
    """Sort by planned_question_id (natural sort) then priority."""
    pid = row.get("planned_question_id", "")
    # natural sort: extract numeric suffix for correct S1-Q2 < S1-Q10 ordering
    parts = re.split(r"(\d+)", pid)
    parts_key = [int(p) if p.isdigit() else p.lower() for p in parts]
    pri = priority_rank.get(row.get("priority", "P3"), 99)
    return (parts_key, pri)


result_rows = []

if raw_rows is not None:
    # Pre-loaded rows — filter by session, keep only B-I fields
    for r in raw_rows:
        if str(r.get("session", "")).strip() == target_session:
            result_rows.append({
                "planned_question_id":        str(r.get("planned_question_id", "")).strip(),
                "planned_question":           str(r.get("planned_question", "")).strip(),
                "uid":                        str(r.get("uid", "")).strip(),
                "qid":                        str(r.get("qid", "")).strip(),
                "capability":                 str(r.get("capability", "")).strip(),
                "dimension":                  str(r.get("dimension", "")).strip(),
                "priority":                   str(r.get("priority", "")).strip(),
                "exact_master_rubric_question": str(r.get("exact_master_rubric_question", "")).strip(),
            })
else:
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        headers = next(reader)
        col_map = normalise_header(headers)

        required = list(COL_ALIASES.keys())
        missing = [k for k in required if k not in col_map]
        if missing:
            print(
                json.dumps({"error": f"Could not locate columns in CSV: {missing}. "
                                     f"Headers found: {headers}"}),
                file=sys.stderr,
            )
            sys.exit(1)

        for row in reader:
            if not any(cell.strip() for cell in row):
                continue  # skip blank rows
            row_session = row[col_map["session"]].strip()
            # Match as string (handles both "1" and 1)
            if row_session == target_session or row_session == str(int(float(target_session))):
                result_rows.append({
                    "planned_question_id":        row[col_map["planned_question_id"]].strip(),
                    "planned_question":           row[col_map["planned_question"]].strip(),
                    "uid":                        row[col_map["uid"]].strip(),
                    "qid":                        row[col_map["qid"]].strip(),
                    "capability":                 row[col_map["capability"]].strip(),
                    "dimension":                  row[col_map["dimension"]].strip(),
                    "priority":                   row[col_map["priority"]].strip(),
                    "exact_master_rubric_question": row[col_map["exact_master_rubric_question"]].strip(),
                })

# ---------------------------------------------------------------------------
# Sort: planned_question_id (B) then priority (H)
# ---------------------------------------------------------------------------
result_rows.sort(key=sort_key)

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
if not result_rows:
    print(
        json.dumps({
            "error": f"No rows found for session '{target_session}'. "
                     "Confirm the session number and that the correct CSV is attached.",
            "rows": []
        })
    )
else:
    output = {
        "session": target_session,
        "row_count": len(result_rows),
        "rows": result_rows
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
