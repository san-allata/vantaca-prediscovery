---
name: docx-transcript-extractor
description: Use this skill whenever a session/meeting transcript is only available as a Word (.docx) file and needs to be converted into clean plain text (and optionally speaker/timestamp-segmented JSON) before it can be analyzed, searched for answers, or fed into a rubric-answering workflow. Trigger this even if the user doesn't say "docx" or "extract" — e.g., "the transcript is in the Word doc", "I only have the meeting recording transcript as .docx", "no txt transcript exists for this session", or as an automatic fallback step inside a larger rubric-answering pipeline (such as session-rubric-answerer) when a plain-text transcript file is not found alongside a session's Word transcript.
---

# Docx Transcript Extractor

## Purpose
Convert a Word (.docx) meeting/session transcript into clean plain text, preserving speaker labels and timestamps when present, so downstream skills (answer extraction, rubric patching) can work from plain text instead of ever opening the binary document directly.

## Use When
- A session folder contains only a `.docx` transcript and no `.txt` version.
- The user says a transcript is "in Word format", "only as docx", or asks to "convert the transcript".
- Used automatically as a fallback step within a larger workflow (e.g., `session-rubric-answerer`) whenever a plain-text transcript is expected but missing for the requested session.

## Do Not Use When
- A `.txt` transcript already exists for the session — use it directly, never re-extract.
- The source is only a video/audio file with no transcript — this skill does not perform speech-to-text, only docx-to-text extraction.
- The document is not a transcript (e.g., a policy PDF, a slide deck) — use a general document extraction approach instead.

## Inputs
- Required: the `.docx` file bytes, provided one of these ways:
  - `run_skill_script` `inputFiles` — a chat-uploaded document ID
  - `run_skill_script` `inputData.docx_base64` — base64-encoded bytes (typical when the file was just fetched from SharePoint via the Office 365 extension)
  - `run_skill_script` `args[0]` — a path to a `.docx` already present in the working directory
- Optional: `inputData.output_name` — base filename for outputs (default: `transcript`)
- Assumption: if none of the above is supplied, the script scans the working directory for the first `*.docx` file it finds.

## Workflow
1. Locate the `.docx` source using the input rules above.
2. Run `scripts/extract_docx_text.py` via `run_skill_script`.
3. The script parses the document (using `python-docx` when available, with a built-in stdlib zipfile/XML fallback so it never hard-fails on a missing dependency), extracting paragraph and table text in document order.
4. It detects speaker/timestamp patterns (e.g., `Speaker Name:`, `[00:12:34]`, `00:12:34 - Name:`) with regex heuristics and segments the transcript accordingly whenever a pattern is found.
5. It writes `transcript.txt` (plain text) and `transcript_segments.json` (structured `{index, speaker, timestamp, text}` array) to the working directory, and prints the full plain text to stdout so the calling agent can use it immediately.
6. Report to the user: paragraph/segment counts, whether speaker/timestamp segmentation was detected, and any parsing warnings (e.g., fallback engine used).

## Output Format
- `transcript.txt` — full plain text, one paragraph (or table row) per line, in original document order.
- `transcript_segments.json` — structured array, e.g.:
```json
[
  {"index": 0, "speaker": "Jane Doe", "timestamp": "00:01:12", "text": "We reconcile twelve accounts monthly."},
  {"index": 1, "speaker": null, "timestamp": null, "text": "Additional context paragraph with no detected speaker tag."}
]
```
- Stdout JSON summary: `engine_used`, `paragraph_count`, `table_row_count`, `segment_count`, `speakers_detected`, `warnings`, `output_files` — followed by the full transcript text between `----- TRANSCRIPT TEXT START -----` / `----- TRANSCRIPT TEXT END -----` markers.

## Tool and Data Rules
- Never ask a human to open or paste the Word document manually — always extract via this skill's script.
- Do not fabricate speaker names or timestamps when patterns are not present; leave `speaker`/`timestamp` as `null` rather than guessing.
- Treat the extracted text as the only valid transcript evidence for downstream answer extraction — never supplement with assumptions about what "probably" was said.
- When the extracted text is later cited as evidence, cite the original transcript filename — not this skill — as the source.

## Examples
### Example Request
"Session 3 doesn't have a txt transcript, only the Word file from SharePoint. Extract it so we can answer the session questions."

### Expected Behavior
1. Fetch the docx bytes via the Office 365 extension (e.g., `download-onedrive-file-content`).
2. Call `run_skill_script` with `scriptPath: scripts/extract_docx_text.py` and `inputData.docx_base64` set to the fetched bytes (base64-encoded).
3. Receive the transcript text via stdout; report segment/speaker counts to the user before proceeding to answer extraction.

## Validation Checklist
- [ ] Confirmed no `.txt` transcript existed for this session before invoking this skill.
- [ ] Extraction did not silently drop content — paragraph count looks reasonable versus session length.
- [ ] Speaker/timestamp segmentation reported honestly, including "none detected" when that's the case.
- [ ] Output text used as-is for evidence — no manual edits, cleanup, or guesses added.

## Troubleshooting
- If `python-docx` is unavailable in the sandbox, the script automatically falls back to a stdlib zipfile/XML parser — no action needed, but note the fallback in your report.
- If the docx is empty, password-protected, or corrupted, report `0 paragraphs extracted` and ask the user for a different file rather than inventing content.
- If transcript content lives in tables rather than paragraphs, it is still extracted (appended after paragraphs, prefixed `[TABLE]` in the text and labeled in the segments JSON).