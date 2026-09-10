#!/usr/bin/env python3
"""
build_assessment_batch.py
─────────────────────────
Reads input.json (written by the execute_code sandbox from the `input` parameter)
and produces Assessment_Run<N>_<CapGroup>.xlsx.

Expected input.json structure:
{
  "batch_name": "Run1_MgmtFee",          # used in filename
  "rows": [
    {
      "uid": "Q0468",
      "qid": "6.15.1",
      "session": 6,
      "planned_question_id": "S6-Q3",
      "domain": "Financial Operations",
      "cap_num": "6.15",
      "capability": "Management Fee Administration",
      "dimension": "Fee schedule configuration per association",
      "priority": "P0",
      "discovery_question": "...",
      "branch_answer": "...",
      "townsq_capability": "...",
      "classification": "AC",
      "assessor_notes": "...",
      "hitl": false
    },
    ...
  ]
}

Output:
  Assessment_Run<batch_name>.xlsx  (written to cwd)
  summary.json                     (written to cwd — row count + classification breakdown)

Usage in execute_code:
  Pass rows as the `input` parameter (≤ 30 rows per call to stay under payload limits).
  The sandbox writes input to input.json automatically.
  This script reads input.json and writes the xlsx.

Color map:
  AC  = #70AD47 (green)  white bold font
  FB  = #FF0000 (red)    white bold font
  PC  = #4472C4 (blue)   white bold font
  NA  = #FFD966 (yellow) black bold font
  HITL= #FFC000 (amber)  black bold font  [when row["hitl"] is True]

Column schema (14 cols):
  UID | QID | Session | Planned Question ID | Domain | Cap # | Capability |
  Dimension | Priority | Discovery Question | Branch Answer |
  TownSq Capability | Classification | Assessor Notes
"""

import json
import sys
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment
    from openpyxl.utils import get_column_letter
except ImportError:
    print("ERROR: openpyxl not available in this sandbox", file=sys.stderr)
    sys.exit(1)

# ── Color definitions ────────────────────────────────────────────────────────
FILLS = {
    "AC":   PatternFill("solid", fgColor="70AD47"),
    "FB":   PatternFill("solid", fgColor="FF0000"),
    "PC":   PatternFill("solid", fgColor="4472C4"),
    "NA":   PatternFill("solid", fgColor="FFD966"),
    "HITL": PatternFill("solid", fgColor="FFC000"),
}
FONT_WHITE_BOLD = Font(color="FFFFFF", bold=True)
FONT_BLACK_BOLD = Font(color="000000", bold=True)
HEADER_FILL    = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT    = Font(color="FFFFFF", bold=True, size=11)

WHITE_CODES = {"AC", "FB", "PC"}  # white font on these classification fills

# ── Column definitions ────────────────────────────────────────────────────────
HEADERS = [
    "UID", "QID", "Session", "Planned Question ID", "Domain", "Cap #",
    "Capability", "Dimension", "Priority", "Discovery Question",
    "Branch Answer", "TownSq Capability", "Classification", "Assessor Notes"
]

# Width per column (characters) — tuned for readability
COL_WIDTHS = [10, 10, 8, 14, 18, 8, 22, 28, 9, 45, 55, 45, 14, 60]


def row_to_values(r: dict) -> list:
    """Extract the 14 column values from a row dict."""
    return [
        r.get("uid", ""),
        r.get("qid", ""),
        r.get("session", ""),
        r.get("planned_question_id", ""),
        r.get("domain", ""),
        str(r.get("cap_num", "")),
        r.get("capability", ""),
        r.get("dimension", ""),
        r.get("priority", ""),
        r.get("discovery_question", ""),
        r.get("branch_answer", ""),
        r.get("townsq_capability", ""),
        r.get("classification", ""),
        r.get("assessor_notes", ""),
    ]


def build_xlsx(rows: list, batch_name: str) -> str:
    """Build the Assessment xlsx and return the output filename."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Assessment"

    # ── Header row ────────────────────────────────────────────────────────
    for ci, h in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=ci, value=h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.row_dimensions[1].height = 30

    # ── Data rows ──────────────────────────────────────────────────────────
    counts = {"AC": 0, "FB": 0, "PC": 0, "NA": 0, "HITL": 0, "OTHER": 0}

    for ri, r in enumerate(rows, 2):
        vals    = row_to_values(r)
        cl      = (r.get("classification") or "").strip().upper()
        is_hitl = bool(r.get("hitl", False))

        for ci, val in enumerate(vals, 1):
            cell = ws.cell(row=ri, column=ci, value=val)
            cell.alignment = Alignment(wrap_text=True, vertical="top")

            # Apply classification color to column 13 only
            if ci == 13:
                if is_hitl:
                    cell.fill = FILLS["HITL"]
                    cell.font = FONT_BLACK_BOLD
                    counts["HITL"] += 1
                elif cl in FILLS:
                    cell.fill = FILLS[cl]
                    cell.font = FONT_WHITE_BOLD if cl in WHITE_CODES else FONT_BLACK_BOLD
                    counts[cl] = counts.get(cl, 0) + 1
                else:
                    counts["OTHER"] += 1

        ws.row_dimensions[ri].height = 80

    # ── Column widths ──────────────────────────────────────────────────────
    for i, w in enumerate(COL_WIDTHS, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # ── Freeze header ──────────────────────────────────────────────────────
    ws.freeze_panes = "A2"

    # ── Save ──────────────────────────────────────────────────────────────
    filename = f"Assessment_{batch_name}.xlsx"
    wb.save(filename)
    return filename, counts


def main():
    # Read input
    input_path = Path("input.json")
    if not input_path.exists():
        print("ERROR: input.json not found. Pass rows via the execute_code `input` parameter.",
              file=sys.stderr)
        sys.exit(1)

    with open(input_path) as f:
        data = json.load(f)

    rows       = data.get("rows", [])
    batch_name = data.get("batch_name", "Batch")

    if not rows:
        print("ERROR: No rows provided in input.json", file=sys.stderr)
        sys.exit(1)

    if len(rows) > 35:
        print(f"WARNING: {len(rows)} rows provided. Recommended max is 30 per batch "
              f"to avoid payload limits. Proceeding anyway.", file=sys.stderr)

    filename, counts = build_xlsx(rows, batch_name)

    # Summary
    summary = {
        "output_file": filename,
        "rows_written": len(rows),
        "batch_name": batch_name,
        "classification_counts": counts,
    }
    with open("summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Done. Output: {filename}")
    print(f"Rows written: {len(rows)}")
    print(f"AC: {counts['AC']} | FB: {counts['FB']} | PC: {counts['PC']} "
          f"| NA: {counts['NA']} | HITL: {counts['HITL']}")


if __name__ == "__main__":
    main()
