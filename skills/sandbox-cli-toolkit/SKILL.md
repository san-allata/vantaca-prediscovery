---
name: sandbox-cli-toolkit
description: Use this skill whenever you are about to run a shell/Linux command inside execute_code (bash) or need to decide between a CLI tool and a Python one-liner for text/data manipulation — e.g. filtering, searching, sorting, counting, diffing, archiving, or JSON/CSV wrangling. Consult it BEFORE assuming a tool like jq, sqlite3, unzip, zip, libreoffice, wget, or patch exists, and BEFORE writing a brand-new ad-hoc script — it lists exactly what is installed in this sandbox, what is missing, and the verified substitute command for each missing tool. Also use it when told "use Linux commands, don't create scripts."
---

# Sandbox CLI Toolkit

## Purpose
This sandbox (execute_code, bash/python/node) is **offline** — no network access, no `pip install`, no `apt install`. Before running any command, check this reference instead of guessing. Guessing costs a failed tool call and burns tokens; this file is the ground truth, verified by direct probe on the current image (Debian 13 "trixie", Python 3.12.13).

## Rule
**Prefer a verified-available command or a short Python one-liner over inventing a new persistent script.** Do not create new skill scripts for one-off text/data manipulation that a single shell command or Python stdlib call can do. Reserve real scripts (added via `add_skill_resource`/`update_skill_resource`) for logic that is reused across many runs (e.g. the session-scope resolver, the xlsx patcher).

## Verified AVAILABLE (safe to use directly)
| Command | Notes |
|---|---|
| `sed`, `awk`, `grep`, `cut`, `sort`, `uniq`, `wc`, `find`, `xargs`, `diff` | GNU coreutils, standard behavior |
| `tar`, `gzip` | Archives — no `zip`/`unzip` binary, see substitute below |
| `curl` | Present but **useless — sandbox has no network access**. Do not attempt external fetches. |
| `node`, `npm` | Present but `npm install` will fail (no network) — only use packages already vendored |
| `python3` (3.12.13) | Primary tool for anything non-trivial |
| Python packages: `openpyxl` 3.1.5, `pandas` 3.0.5, `xlrd` 2.0.2, `xlsxwriter` 3.2.9, `lxml` 6.1.1 | Pre-installed; sufficient for all Excel read/write/patch work |
| Python stdlib `sqlite3`, `zipfile`, `json`, `csv`, `re`, `xml.etree.ElementTree` | Use these instead of the missing CLI equivalents below |

## Verified NOT AVAILABLE — do not assume these exist
| Missing | Use instead |
|---|---|
| `jq` | Python: `python3 -c "import json,sys; data=json.load(open('f.json')); ..."` or a short inline script using stdlib `json`. **`excel-qa-processor` skill's documented jq-filtering workflow does not work in this sandbox as written — substitute Python filtering.** |
| `sqlite3` (CLI) | Python stdlib `import sqlite3` works fine — use that, never shell out to a `sqlite3` binary |
| `csvkit` / `in2csv` | Python stdlib `csv` module, or `pandas.read_csv` |
| `libreoffice` / `soffice` | Not available — never plan a LibreOffice round-trip for any xlsx operation. Use `openpyxl` for all read/write/formula-preserving edits. (Also: a LibreOffice round-trip is called out elsewhere as a known cause of hidden-sheet corruption — another reason to avoid it even if it were installed.) |
| `unzip`, `zip` | An `.xlsx` is a zip archive. Use Python's `zipfile` module: `zipfile.ZipFile(path)` to inspect/extract, `zipfile.ZipFile(path, 'a')` to add/replace parts. Never shell out to `unzip`/`zip`. |
| `wget`, `rsync` | No network access at all — neither works regardless. Any workflow step that says "download from URL" cannot execute here. |
| `patch` | Use Python to read, transform, and rewrite the target file directly instead of generating/applying a diff patch file. |
| `xmllint`, `xsltproc` | Use Python's `lxml` (pre-installed) or `xml.etree.ElementTree` for any raw XML inspection (e.g. checking `hidden="1"` in sheet XML inside an xlsx). |

## Practical recipes for this environment

**Filter/search JSON without jq:**
```python
import json
data = json.load(open("input.json"))
rows = [r for r in data if r.get("session") == 3]
```

**Check for hidden sheets in a saved xlsx (replaces xmllint):**
```python
import zipfile, re
with zipfile.ZipFile("workbook.xlsx") as z:
    for name in z.namelist():
        if name.startswith("xl/worksheets/sheet"):
            xml = z.read(name).decode("utf-8", errors="ignore")
            if 'hidden="1"' in re.sub(r"\s+", " ", xml):
                print(f"HIDDEN SHEET FOUND: {name}")
```

**Query a spreadsheet-like structure without sqlite3 CLI:**
Use the platform's `executeQuery`/`getSpreadsheetInfo` tools directly (they already run against a parquet-backed engine) — never shell out to a `sqlite3` binary for this.

## Validation Checklist
- [ ] Before running a shell command, it appears in the AVAILABLE table above, or is a plain POSIX builtin (`cd`, `echo`, `cat`, etc.)
- [ ] No step assumes network access (no `pip install`, `npm install` of new packages, `curl`/`wget` to an external host, cloning a repo)
- [ ] No step shells out to `jq`, `sqlite3`, `unzip`/`zip`, `libreoffice`/`soffice`, `wget`, `patch`, `xmllint`/`xsltproc` — a Python substitute from this file is used instead
- [ ] A new ad-hoc script is created only when the logic will be reused across runs — otherwise inline Python/bash via execute_code is used and discarded

## Troubleshooting
- If a command returns "command not found", it is very likely one of the "NOT AVAILABLE" entries above — check the substitute rather than retrying or installing.
- If a workflow document (skill, persona) instructs using `jq` or a LibreOffice round-trip, treat that instruction as stale for this sandbox and use the Python substitute instead; flag the source document for correction.