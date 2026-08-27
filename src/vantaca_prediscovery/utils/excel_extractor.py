#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel Data Extraction Tool
Extracts data from Excel files with flexible filtering and column selection.
Supports CSV, JSON, and JSON-compact output formats.
Outputs to file or stdout with UTF-8 encoding.
Includes row numbers from the source file.
"""
import csv
import pandas as pd
import json
import re
import argparse
import sys
from typing import Optional, Union
from io import TextIOWrapper

# Ensure stdout/stderr use UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def parse_column_range(column_range: str) -> tuple:
    """
    Parse column range string into list of column indices or names.

    Examples:
        "A:D" -> columns A through D
        "1:5" -> first 5 columns
        "A,C,E" -> columns A, C, E
        "0:3" -> columns 0 through 3 (zero-indexed)

    Args:
        column_range: Column specification string

    Returns:
        tuple: (use_names, columns) where use_names is bool and columns is list
    """
    column_range = column_range.strip()

    # Check if it's letter-based (A:D format)
    if re.match(r'^[A-Z]:[A-Z]$', column_range):
        start = ord(column_range[0]) - ord('A')
        end = ord(column_range[2]) - ord('A') + 1
        return (True, list(range(start, end)))

    # Check if it's comma-separated letters (A,C,E format)
    if re.match(r'^[A-Z](,[A-Z])*$', column_range):
        columns = [ord(c) - ord('A') for c in column_range.split(',')]
        return (True, columns)

    # Check if it's numeric range (1:5 or 0:3 format)
    if ':' in column_range:
        parts = column_range.split(':')
        start = int(parts[0])
        end = int(parts[1]) + 1
        return (False, list(range(start, end)))

    # Check if it's comma-separated numbers (0,2,4 format)
    if ',' in column_range:
        columns = [int(x.strip()) for x in column_range.split(',')]
        return (False, columns)

    # Single column
    try:
        col = int(column_range)
        return (False, [col])
    except ValueError:
        return (True, [ord(column_range) - ord('A')])


def replace_nan(df: pd.DataFrame) -> pd.DataFrame:
    """
    Replace NaN values with None (which serializes to null in JSON).

    Args:
        df: DataFrame with potential NaN values

    Returns:
        pd.DataFrame: DataFrame with NaN replaced by None
    """
    return df.fillna(value='').map(lambda x: x.strip() if isinstance(x, str) else x)


def extract_excel_data(
    filename: str,
    sheet_name: Union[str, int] = 0,
    column_range: Optional[str] = None,
    skip_rows: Optional[int] = None,
    filter_column: Optional[str] = None,
    filter_regex: Optional[str] = None,
    output_file: Optional[str] = None,
    output_format: str = 'csv',
) -> pd.DataFrame:
    """
    Extract data from Excel file with optional filtering.
    Includes a 'row_number' column with original source row numbers.

    Args:
        filename: Path to Excel file
        sheet_name: Sheet name or index (default: 0 for first sheet)
        column_range: Column range specification (e.g., "A:D", "0:3", "A,C,E") - optional
        skip_rows: List of row indices to skip (e.g., [1, 2, 5])
        filter_column: Column name or index to filter on
        filter_regex: Regex pattern to match in filter_column
        output_file: Optional output file path (if None, outputs to stdout)
        output_format: Output format ('csv', 'json', 'json-compact') - default: 'csv'

    Returns:
        pd.DataFrame: Extracted and filtered data with row_number column

    Raises:
        FileNotFoundError: If Excel file not found
        ValueError: If sheet not found or invalid parameters
    """

    # Read Excel file
    try:
        df = pd.read_excel(filename, sheet_name=sheet_name, header=None)
    except FileNotFoundError:
        raise FileNotFoundError(f"Excel file not found: {filename}")
    except ValueError as e:
        raise ValueError(f"Sheet '{sheet_name}' not found: {e}")

    print(f"✓ Loaded {len(df)} rows from '{filename}' sheet '{sheet_name}'", file=sys.stderr)

    df.insert(0, 'row_number', df.index + 1)

    # Skip rows if specified
    if skip_rows:
        df.columns = df.iloc[skip_rows]
        df = df.tail(-skip_rows-1)
        df = df.rename(columns={df.columns[0]: 'row_number'})
        df.columns = df.columns.str.replace('\n', ' ').str.strip()
        print(f"✓ Skipped {skip_rows} rows", file=sys.stderr)

    # Select column range if specified
    if column_range:
        use_names, columns = parse_column_range(column_range)

        # Adjust column indices to account for row_number column (it's now at index 0)
        adjusted_columns = [col + 1 for col in columns]

        if use_names:
            # Convert column indices to letters for display
            selected_cols = [chr(ord('A') + i) for i in columns]
            try:
                # Keep row_number column and add selected columns
                df = df.iloc[:, [0] + adjusted_columns]
            except IndexError:
                raise ValueError(f"Column range out of bounds: {column_range}")
            print(f"✓ Selected columns: {', '.join(selected_cols)}", file=sys.stderr)
        else:
            try:
                # Keep row_number column and add selected columns
                df = df.iloc[:, [0] + adjusted_columns]
            except IndexError:
                raise ValueError(f"Column range out of bounds: {column_range}")
            print(f"✓ Selected columns: {columns}", file=sys.stderr)

    # Filter rows by regex if specified
    if filter_regex:
        if filter_column is None:
            raise ValueError("filter_column must be specified when using filter_regex")

        # Get column (by name or index) - adjust for row_number column if needed
        if isinstance(filter_column, int):
            # If numeric index, adjust for row_number column being at position 0
            actual_col_index = filter_column + 1
            col_name = df.columns[actual_col_index]
        else:
            col_name = filter_column

        if col_name not in df.columns:
            raise ValueError(f"Filter column '{filter_column}' not found in DataFrame")

        # Apply regex filter
        pattern = re.compile(filter_regex)
        mask = df[col_name].astype(str).apply(lambda x: bool(pattern.search(x)))
        rows_before = len(df)
        df = df[mask]
        rows_removed = rows_before - len(df)
        print(f"✓ Applied regex filter '{filter_regex}' on '{col_name}': removed {rows_removed} rows", file=sys.stderr)

    # Replace NaN with None before output
    df = replace_nan(df)

    print(f"✓ Final result: {len(df)} rows × {len(df.columns)} columns\n", file=sys.stderr)

    # Output data
    if output_format == 'csv':
        if output_file:
            df.to_csv(output_file, quoting=csv.QUOTE_NONNUMERIC, index=False, lineterminator='\n', encoding='utf-8')
            print(f"✓ Saved to '{output_file}'", file=sys.stderr)
        else:
            df.to_csv(sys.stdout, quoting=csv.QUOTE_NONNUMERIC, index=False, lineterminator='\n', encoding='utf-8')
    elif output_format == 'json':
        output = json.dumps(df.to_dict(orient='records'), indent=2, ensure_ascii=False, default=str)
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"✓ Saved to '{output_file}'", file=sys.stderr)
        else:
            print(output)
    elif output_format == 'json-compact':
        output = json.dumps(df.to_dict(orient='records'), separators=(',', ':'), ensure_ascii=False, default=str)
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"✓ Saved to '{output_file}'", file=sys.stderr)
        else:
            print(output)

    return df


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description='Extract data from Excel files with filtering options',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Extract all columns to stdout as CSV (includes row_number column)
  python extract_excel.py data.xlsx

  # Extract columns A-D to file (row_number always included)
  python extract_excel.py data.xlsx --columns A:D --output result.csv

  # Extract specific columns to stdout as JSON
  python extract_excel.py data.xlsx --columns A,C,E --format json

  # Skip rows, filter, output as compact JSON to file
  python extract_excel.py data.xlsx --skip-rows 1 2 --filter-column B --filter-regex ".*@example\\.com" --output result.json --format json-compact

  # Extract from named sheet with column range, pipe to stdout
  python extract_excel.py data.xlsx --sheet "Sales Data" --columns 0:5 --format json | jq .

  # Filter by column index and save to file (note: row_number is not affected by column selection)
  python extract_excel.py data.xlsx --filter-column 3 --filter-regex "^[0-9]{4}$" --output filtered.csv
        '''
    )

    parser.add_argument('filename', help='Path to Excel file')
    parser.add_argument('--sheet', default=0, help='Sheet name or index (default: 0)')
    parser.add_argument('--columns', help='Column range (e.g., A:D, 0:5, A,C,E) - optional')
    parser.add_argument('--skip-rows', type=int, help='Rows to skip')
    parser.add_argument('--filter-column', help='Column name or index to filter')
    parser.add_argument('--filter-regex', help='Regex pattern to match in filter column')
    parser.add_argument('--output', help='Output file path (if not specified, outputs to stdout)')
    parser.add_argument('--format', choices=['csv', 'json', 'json-compact'], default='csv',
                        help='Output format (default: csv)')

    args = parser.parse_args()

    try:
        # Try to convert sheet to int if possible
        try:
            sheet = int(args.sheet)
        except ValueError:
            sheet = args.sheet

        # Convert filter_column to int if it looks like a number
        filter_col = args.filter_column
        if filter_col is not None:
            try:
                filter_col = int(filter_col)
            except ValueError:
                pass

        extract_excel_data(
            filename=args.filename,
            sheet_name=sheet,
            column_range=args.columns,
            skip_rows=args.skip_rows,
            filter_column=filter_col,
            filter_regex=args.filter_regex,
            output_file=args.output,
            output_format=args.format,
        )

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()