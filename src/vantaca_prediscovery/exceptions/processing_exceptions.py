class VantacaProcessingException(Exception):
    """Base exception for all processing errors."""
    def __init__(self, message: str, error_code: str, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class DocumentExtractionException(VantacaProcessingException):
    """Raised when document extraction fails."""
    pass


class CorruptedDocumentException(DocumentExtractionException):
    """DOCX file is corrupted or unreadable."""
    error_code = "ERR_DOCX_CORRUPTED"


class SchemaValidationException(VantacaProcessingException):
    """Column structure doesn't match expected schema."""
    error_code = "ERR_SCHEMA_MISMATCH"


class RowAlignmentException(VantacaProcessingException):
    """Multi-session row alignment conflict."""
    error_code = "ERR_ROW_COLLISION"


class FileLockException(VantacaProcessingException):
    """Cannot access file (locked or permission denied)."""
    error_code = "ERR_FILE_LOCKED"


class PartialProcessingException(VantacaProcessingException):
    """Some sessions succeeded, some failed."""
    error_code = "ERR_PARTIAL_SUCCESS"

    def __init__(self, message: str, successful: list, failed: list):
        self.successful_sessions = successful
        self.failed_sessions = failed
        super().__init__(message, self.error_code, {
            "successful": successful,
            "failed": failed
        })
