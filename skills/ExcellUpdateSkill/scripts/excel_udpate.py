#!/usr/bin/env python3
"""
Script to populate Excel cells with answers from a JSON file by treating Excel as a ZIP.
Minimizes file changes by directly updating cell XML.

Usage:
    python script.py <excel_file> <json_file>

Example:
    python script.py questions.xlsx answers.json
"""

import sys
import json
import re
import zipfile
import shutil
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET


# Define namespace for Excel XML
NAMESPACES = {
    'ss': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'
}

# Register namespaces to preserve prefixes when writing
ET.register_namespace('', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main')
ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
ET.register_namespace('mc', 'http://schemas.openxmlformats.org/markup-compatibility/2006')
ET.register_namespace('x14ac', 'http://schemas.microsoft.com/office/spreadsheetml/2009/9/ac')


def parse_cell_location(cell_str):
    """
    Parse cell location string (e.g., 'H5', 'j13') into column and row.

    Args:
        cell_str: String representation of cell location

    Returns:
        str: Uppercase cell reference (e.g., 'H5')
    """
    cell_str = cell_str.strip().upper()

    match = re.match(r'^([A-Z]+)(\d+)$', cell_str)
    if not match:
        raise ValueError(f"Invalid cell location format: {cell_str}. Expected format like 'H5' or 'J13'")

    return cell_str


def get_sheet_filename(sheet_name, workbook_path, temp_dir):
    """
    Find the worksheet XML file corresponding to a sheet name.
    Tries multiple approaches for robustness:
    1. Look up via workbook.xml and relationships
    2. Fallback to direct file mapping (sheet1.xml, sheet2.xml, etc.)

    Args:
        sheet_name: Name of the sheet
        workbook_path: Path to extracted workbook.xml
        temp_dir: Temporary directory where files are extracted

    Returns:
        str: Relative path to the worksheet XML file (e.g., 'xl/worksheets/sheet1.xml')
    """

    # Parse workbook.xml to find sheets
    tree = ET.parse(workbook_path)
    root = tree.getroot()

    # Find sheets element
    sheets = root.find('.//ss:sheets', NAMESPACES)
    if sheets is None:
        raise ValueError("Could not find sheets in workbook.xml")

    sheet_list = sheets.findall('ss:sheet', NAMESPACES)
    if not sheet_list:
        raise ValueError("No sheets found in workbook.xml")

    # Approach 1: Try to match by name and get relationship ID
    sheet_id = None
    sheet_index = None

    for idx, sheet in enumerate(sheet_list, 1):
        sheet_name_attr = sheet.get('name')
        if sheet_name_attr == sheet_name:
            # Try to get relationship ID using various namespace formats
            sheet_id = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            if not sheet_id:
                sheet_id = sheet.get('{http://schemas.openxmlformats.org/package/2006/relationships}id')
            if not sheet_id:
                # Sometimes it's stored without namespace prefix
                for attr_name, attr_value in sheet.attrib.items():
                    if attr_name.endswith('}id') or attr_name == 'id':
                        sheet_id = attr_value
                        break

            sheet_index = idx
            break

    # Try relationship lookup if we found a sheet ID
    if sheet_id:
        try:
            rels_path = Path(temp_dir) / 'xl' / '_rels' / 'workbook.xml.rels'
            if rels_path.exists():
                rels_tree = ET.parse(rels_path)
                rels_root = rels_tree.getroot()

                # Find the relationship with matching ID
                for rel in rels_root.findall('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                    if rel.get('Id') == sheet_id:
                        target = rel.get('Target')
                        if target:
                            # Convert relative path to proper format if needed
                            if not target.startswith('xl/'):
                                target = 'xl/' + target
                            worksheet_path = Path(temp_dir) / target
                            if worksheet_path.exists():
                                return target
        except Exception as e:
            print(f"  Debug: Relationship lookup failed: {e}")

    # Approach 2: Fallback to direct file mapping using sheet index
    # Standard Excel format: sheet1.xml, sheet2.xml, etc.
    if sheet_index:
        direct_target = f'xl/worksheets/sheet{sheet_index}.xml'
        worksheet_path = Path(temp_dir) / direct_target
        if worksheet_path.exists():
            print(f"  Info: Using fallback mapping '{sheet_name}' -> {direct_target}")
            return direct_target

    # Approach 3: List available sheets for debugging
    available_sheets = []
    for idx, sheet in enumerate(sheet_list, 1):
        available_sheets.append(sheet.get('name'))

    raise ValueError(
        f"Sheet '{sheet_name}' not found in workbook. "
        f"Available sheets: {', '.join(available_sheets)}"
    )


def update_cell_in_worksheet(worksheet_path, cell_ref, value):
    """
    Update a cell value in a worksheet XML file.
    Uses inline string format to preserve formatting.

    Args:
        worksheet_path: Path to worksheet XML file
        cell_ref: Cell reference (e.g., 'H5')
        value: Value to set
    """
    tree = ET.parse(worksheet_path)
    root = tree.getroot()

    # Find or create sheetData element
    sheet_data = root.find('ss:sheetData', NAMESPACES)
    if sheet_data is None:
        raise ValueError("Could not find sheetData in worksheet")

    # Parse cell reference
    match = re.match(r'^([A-Z]+)(\d+)$', cell_ref)
    if not match:
        raise ValueError(f"Invalid cell reference: {cell_ref}")

    col_letters = match.group(1)
    row_num = int(match.group(2))

    # Find or create row
    row = None
    for r in sheet_data.findall('ss:row', NAMESPACES):
        row_attr = r.get('r')
        if row_attr and int(row_attr) == row_num:
            row = r
            break

    if row is None:
        row = ET.Element('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row')
        row.set('r', str(row_num))
        sheet_data.append(row)

    # Find or create cell
    cell = None
    for c in row.findall('ss:c', NAMESPACES):
        if c.get('r') == cell_ref:
            cell = c
            break

    if cell is None:
        cell = ET.Element('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c')
        cell.set('r', cell_ref)
        row.append(cell)

    # Remove old children (v, f, is, etc.)
    for child in list(cell):
        cell.remove(child)

    # Set cell type to inline string and add value
    cell.set('t', 'inlineStr')

    is_elem = ET.Element('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}is')
    t_elem = ET.Element('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
    t_elem.text = str(value)
    is_elem.append(t_elem)
    cell.append(is_elem)

    # Save the modified XML
    tree.write(worksheet_path, encoding='utf-8', xml_declaration=True)


def populate_excel(excel_file, json_file):
    """
    Populate Excel file with answers from JSON file by manipulating ZIP contents.

    Args:
        excel_file: Path to the Excel file
        json_file: Path to the JSON file containing answers
    """
    excel_path = Path(excel_file)
    json_path = Path(json_file)

    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_file}")
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_file}")

    # Load JSON answers
    with open(json_path, 'r', encoding='utf-8') as f:
        answers_data = json.load(f)

    if not isinstance(answers_data, list):
        raise ValueError("JSON file must contain a list of answers")

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Extract Excel as ZIP
        with zipfile.ZipFile(excel_path, 'r') as zip_ref:
            zip_ref.extractall(temp_path)

        # Process each answer
        answers_count = 0
        workbook_path = temp_path / 'xl' / 'workbook.xml'

        for answer in answers_data:
            if not isinstance(answer, dict):
                print(f"Warning: Skipping invalid answer entry (not a dict): {answer}")
                continue

            sheet_name = answer.get('sheet')
            cell_location = answer.get('cell')
            answer_text = answer.get('answer')

            if not sheet_name or not cell_location or answer_text is None:
                print(f"Warning: Skipping answer with missing fields: {answer}")
                continue

            try:
                # Parse and validate cell reference
                cell_ref = parse_cell_location(cell_location)

                # Find worksheet file for this sheet
                sheet_file = get_sheet_filename(sheet_name, workbook_path, temp_dir)
                worksheet_path = temp_path / sheet_file

                if not worksheet_path.exists():
                    print(f"Warning: Worksheet file not found for sheet '{sheet_name}': {worksheet_path}")
                    continue

                # Update cell in worksheet
                update_cell_in_worksheet(worksheet_path, cell_ref, answer_text)

                answers_count += 1
                print(f"✓ Set {sheet_name}!{cell_ref} = {repr(answer_text)}")

            except Exception as e:
                print(f"✗ Error processing answer for sheet '{sheet_name}': {e}")
                continue

        # Repack as ZIP (Excel file)
        # Create backup of original file
        backup_path = Path(str(excel_path) + '.backup')
        shutil.copy2(excel_path, backup_path)
        print(f"✓ Backup created: {backup_path}")

        # Create new ZIP file with updated content
        with zipfile.ZipFile(excel_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for file_path in temp_path.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(temp_path)
                    zip_ref.write(file_path, arcname)

        print(f"\n✓ Successfully updated {answers_count} cell(s)")
        print(f"✓ File saved: {excel_file}")


def main():
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: python script.py <excel_file> <json_file>")
        print("\nExample: python script.py questions.xlsx answers.json")
        sys.exit(1)

    excel_file = sys.argv[1]
    json_file = sys.argv[2]

    try:
        populate_excel(excel_file, json_file)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: JSON file is malformed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
