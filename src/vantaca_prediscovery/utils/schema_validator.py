from dataclasses import dataclass
from typing import List, Dict
from openpyxl import load_workbook

@dataclass
class ColumnSchema:
    """Expected column structure."""
    name: str
    column_letter: str
    data_type: str  # "string", "integer", "date", etc.
    required: bool = True
    example_value: str = None


class ExcelSchemaValidator:
    """Validate Excel file structure before processing."""

    EXPECTED_SCHEMA = [
        ColumnSchema("Session ID", "A", "string", required=True),
        ColumnSchema("Branch Name", "B", "string", required=True),
        ColumnSchema("Question Number", "C", "integer", required=True),
        ColumnSchema("Question Text", "D", "string", required=True),
        ColumnSchema("Status", "E", "string", required=False),
        ColumnSchema("Notes", "F", "string", required=False),
        ColumnSchema("Score", "G", "integer", required=False),
        ColumnSchema("Answer", "H", "string", required=True),
    ]

    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.workbook = load_workbook(excel_path)
        self.worksheet = self.workbook.active

    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate workbook schema.

        Returns:
            (is_valid, list of error messages)
        """
        errors = []

        # Check header row exists
        header_row = self._find_header_row()
        if not header_row:
            errors.append("Could not find header row")
            return False, errors

        # Validate each expected column
        for col_schema in self.EXPECTED_SCHEMA:
            header_cell = self.worksheet[f"{col_schema.column_letter}{header_row}"]
            actual_header = header_cell.value

            if actual_header != col_schema.name:
                errors.append(
                    f"Column {col_schema.column_letter}: "
                    f"expected '{col_schema.name}', got '{actual_header}'"
                )

            if col_schema.required and not actual_header:
                errors.append(
                    f"Required column missing: {col_schema.column_letter}"
                )

        return len(errors) == 0, errors

    def _find_header_row(self) -> int:
        """Find the row containing headers."""
        for row_num in range(1, 10):  # Check first 10 rows
            row_values = []
            for col in ['A', 'B', 'C', 'D']:
                cell_val = self.worksheet[f"{col}{row_num}"].value
                row_values.append(cell_val)

            # Check if this looks like a header row
            if all(v is not None for v in row_values):
                return row_num

        return None

    def generate_schema_report(self) -> Dict:
        """Generate report of actual vs expected schema."""
        is_valid, errors = self.validate()

        actual_schema = {}
        header_row = self._find_header_row()
        if header_row:
            for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                cell_val = self.worksheet[f"{col}{header_row}"].value
                actual_schema[col] = cell_val

        return {
            "is_valid": is_valid,
            "errors": errors,
            "expected_schema": [
                {
                    "column": s.column_letter,
                    "name": s.name,
                    "type": s.data_type,
                    "required": s.required
                }
                for s in self.EXPECTED_SCHEMA
            ],
            "actual_schema": actual_schema
        }
