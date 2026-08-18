# JSON Rubric Tools Skill

## Purpose

Tools to manipulate and convert rubric assessment files between JSON and Excel (XLSX) formats. This skill enables seamless transformation of rubric data for different workflows — from programmatic JSON-based processing to human-friendly Excel editing and back again.

## When to Use This Skill

- **Convert JSON to Excel**: You have a rubric assessment in JSON format and need to:
  - Review or edit it in Excel
  - Share it with team members who prefer spreadsheet format
  - Perform manual scoring, classification, or analysis
  - Create a standardized workbook from JSON data

- **Convert Excel to JSON**: You have a completed or edited rubric in Excel format and need to:
  - Ingest the data into a programmatic workflow
  - Update a JSON-based assessment system
  - Preserve structured data for APIs or downstream processing
  - Maintain a single source of truth in JSON format

## Available Tools

### 1. `rubric_json_to_xlsx.py`
**Purpose**: Transforms rubric data FROM JSON TO Excel workbook

**Input**:
- A JSON file containing rubric structure and data (questions, answers, classifications, scores, metadata)

**Output**:
- An Excel (.xlsx) file with:
  - Properly formatted sheets
  - Headers, question mappings, answer columns
  - All JSON data preserved in readable spreadsheet format
  - Suitable for manual review, editing, and collaboration

**Typical Usage**:
```
Convert a JSON rubric assessment → create an Excel workbook for manual scoring and review
```

### 2. `rubric_xlsx_to_json.py`
**Purpose**: Transforms rubric data FROM Excel TO JSON format

**Input**:
- An Excel (.xlsx) file containing rubric data with:
  - Structured sheet layout
  - Question and answer columns
  - Classification, scores, and metadata

**Output**:
- A JSON file with:
  - All Excel data converted to JSON structure
  - Preserved field mappings and relationships
  - Ready for programmatic processing, APIs, or integration

**Typical Usage**:
```
Convert a completed Excel rubric assessment → create a JSON file for system integration
```

## Workflow Examples

### Example 1: Assessment Creation Workflow
1. Start with a **JSON rubric template** containing question structure
2. Use `rubric_json_to_xlsx.py` to convert → create an **Excel workbook**
3. Share the workbook with assessors for scoring and classification
4. Collect completed Excel workbook
5. Use `rubric_xlsx_to_json.py` to convert → update the **JSON assessment file**
6. Process the JSON through downstream systems (reporting, analytics, archiving)

### Example 2: Data Migration & Integration
1. Have an existing **Excel-based rubric** system
2. Use `rubric_xlsx_to_json.py` to convert → create a **JSON export**
3. Feed JSON into new assessment platform or API
4. Integrate with other systems (data product, reporting dashboard, ML pipeline)

### Example 3: Round-Trip Synchronization
1. Start with **JSON source of truth**
2. Convert to Excel for manual review: `rubric_json_to_xlsx.py`
3. Make edits in Excel
4. Convert back to JSON: `rubric_xlsx_to_json.py`
5. JSON is now updated with all changes

## Data Preservation

Both tools preserve:
- All original content and metadata
- Field mappings and relationships
- Formatting and structure integrity
- Custom columns and extended attributes

## Integration Notes

- Scripts are designed to work with standard rubric structures (questions, answers, classifications, scores)
- JSON files should follow a consistent schema for predictable conversion
- Excel files should use a standard layout with headers and organized columns
- Both conversions are designed to be bidirectional and repeatable

## How to Request Conversion

When you need a conversion, provide:
1. The source file (JSON or Excel)
2. Target format (Excel or JSON)
3. Any specific column mappings or data requirements
4. Expected output file name or location