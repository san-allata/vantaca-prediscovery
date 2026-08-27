from functools import wraps
from src.vantaca_prediscovery.exceptions.processing_exceptions import *

def handle_docx_errors(func):
    """Decorator to handle DOCX-specific errors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except zipfile.BadZipFile:
            raise CorruptedDocumentException(
                f"DOCX file is corrupted: {args[0]}",
                details={"file": str(args[0])}
            )
        except KeyError as e:
            raise CorruptedDocumentException(
                f"DOCX missing required XML: {e}",
                details={"missing_key": str(e)}
            )
        except Exception as e:
            raise DocumentExtractionException(
                f"Unknown extraction error: {e}",
                details={"error": str(e)}
            )
    return wrapper


class ErrorRecoveryHandler:
    """Centralized error recovery logic."""

    @staticmethod
    def handle_schema_mismatch(
        expected_columns: list,
        actual_columns: list
    ) -> dict:
        """Guide user to fix schema mismatch."""
        missing = set(expected_columns) - set(actual_columns)
        extra = set(actual_columns) - set(expected_columns)

        return {
            "is_recoverable": True,
            "missing_columns": list(missing),
            "extra_columns": list(extra),
            "recommendation": (
                "Update Excel column headers to match expected schema or "
                "update schema definition"
            )
        }

    @staticmethod
    def handle_file_lock(file_path: str) -> dict:
        """Recovery steps for file lock."""
        return {
            "is_recoverable": True,
            "steps": [
                "1. Close the Excel file in all applications",
                "2. Ensure no other processes are accessing it",
                f"3. Check file permissions for: {file_path}",
                "4. Retry the operation"
            ]
        }

    @staticmethod
    def handle_partial_failure(
        successful: list,
        failed: list
    ) -> dict:
        """Generate recovery report for partial failures."""
        return {
            "status": "PARTIAL_SUCCESS",
            "successful_count": len(successful),
            "failed_count": len(failed),
            "successful_sessions": successful,
            "failed_sessions": failed,
            "recommendation": "Review failed sessions and retry"
        }
