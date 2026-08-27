"""
Vantaca Pre-Discovery: Extract discovery assessment answers from source documents.

This package provides tools to extract answers from meeting transcripts and
populate Excel rubric assessment workbooks with full provenance tracking.

Features:
    - Multi-session Excel support with automatic row alignment
    - Source attribution (every answer linked to document + timestamp)
    - Data integrity via file backup and rollback mechanisms
    - Comprehensive error handling with recovery paths
    - Excel schema validation before processing
    - Full audit trail of all modifications

Example:
    Basic usage example::

        from vantaca_prediscovery.writers.excel_writer import ExcelAnswerWriter
        from vantaca_prediscovery.utils.schema_validator import ExcelSchemaValidator

        # Validate schema before processing
        validator = ExcelSchemaValidator("assessment.xlsx")
        is_valid, errors = validator.validate()

        if not is_valid:
            print("Schema errors:", errors)
            exit(1)

        # Initialize writer with backup support
        writer = ExcelAnswerWriter("assessment.xlsx")
        writer.initialize_sessions([
            {"session_id": "session_1", "question_count": 20},
            {"session_id": "session_2", "question_count": 15},
        ])

        # Process with automatic error recovery
        try:
            writer.start_session("batch_1")
            writer.write_answer("session_1", 6, "H", "Answer text here")
            writer.complete_session()
        except Exception as e:
            print(f"Error: {e}")
"""

__version__ = "1.0.0"
__author__ = "Allata"
__email__ = "dev@allata.com"
__license__ = "Proprietary"

# Version info
VERSION = tuple(map(int, __version__.split(".")))

# Import key components for convenience
try:
    from .utils.row_alignment_manager import RowAlignmentManager
    from .utils.excel_file_manager import ExcelFileManager
    from .utils.schema_validator import ExcelSchemaValidator
    from .exceptions.processing_exceptions import (
        VantacaProcessingException,
        DocumentExtractionException,
        CorruptedDocumentException,
        SchemaValidationException,
        RowAlignmentException,
        FileLockException,
        PartialProcessingException,
    )
except ImportError:
    # Allow partial imports during development
    pass

# Public API
__all__ = [
    "RowAlignmentManager",
    "ExcelFileManager",
    "ExcelSchemaValidator",
    "VantacaProcessingException",
    "DocumentExtractionException",
    "CorruptedDocumentException",
    "SchemaValidationException",
    "RowAlignmentException",
    "FileLockException",
    "PartialProcessingException",
]
