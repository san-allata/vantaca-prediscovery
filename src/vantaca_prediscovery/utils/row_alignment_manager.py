from dataclasses import dataclass
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class SessionRowMapping:
    """Immutable mapping of session to row ranges."""
    session_id: str
    start_row: int
    end_row: int
    question_count: int

    def __post_init__(self):
        if self.start_row > self.end_row:
            raise ValueError(
                f"Invalid range: start_row ({self.start_row}) > "
                f"end_row ({self.end_row})"
            )

    @property
    def row_count(self) -> int:
        return self.end_row - self.start_row + 1

    def validate_target_row(self, row_num: int) -> bool:
        """Verify row is within this session's range."""
        return self.start_row <= row_num <= self.end_row


class RowAlignmentManager:
    """
    Manages row offsets across multiple sessions to prevent collisions.

    Maintains a global registry of which rows belong to which sessions.
    All writes are validated against this registry before execution.
    """

    def __init__(self, header_rows: int = 5):
        """
        Args:
            header_rows: Number of header rows before session data starts
        """
        self.header_rows = header_rows
        self._session_mappings: Dict[str, SessionRowMapping] = {}
        self._next_available_row = header_rows + 1

    def register_session(
        self,
        session_id: str,
        question_count: int
    ) -> SessionRowMapping:
        """
        Register a session and allocate its row range.

        Args:
            session_id: Unique session identifier
            question_count: Number of answers to allocate rows for

        Returns:
            SessionRowMapping with allocated rows

        Raises:
            ValueError: If session already registered
        """
        if session_id in self._session_mappings:
            raise ValueError(f"Session {session_id} already registered")

        start_row = self._next_available_row
        end_row = start_row + question_count - 1

        mapping = SessionRowMapping(
            session_id=session_id,
            start_row=start_row,
            end_row=end_row,
            question_count=question_count
        )

        self._session_mappings[session_id] = mapping
        self._next_available_row = end_row + 1

        logger.info(
            f"Registered session {session_id}: "
            f"rows {start_row}-{end_row} ({question_count} questions)"
        )

        return mapping

    def get_session_mapping(self, session_id: str) -> Optional[SessionRowMapping]:
        """Retrieve row mapping for a session."""
        return self._session_mappings.get(session_id)

    def validate_write(
        self,
        session_id: str,
        row_num: int,
        answer_content: str
    ) -> tuple[bool, str]:
        """
        Validate that a write is safe before execution.

        Args:
            session_id: Target session
            row_num: Target row number
            answer_content: Answer text (for logging)

        Returns:
            (is_valid, error_message)
        """
        mapping = self.get_session_mapping(session_id)

        if not mapping:
            return False, f"Session {session_id} not registered"

        if not mapping.validate_target_row(row_num):
            return False, (
                f"Row {row_num} outside session bounds "
                f"({mapping.start_row}-{mapping.end_row})"
            )

        # Check for collision with other sessions
        for other_id, other_mapping in self._session_mappings.items():
            if other_id == session_id:
                continue
            if other_mapping.validate_target_row(row_num):
                return False, (
                    f"Row {row_num} already allocated to "
                    f"session {other_id}"
                )

        return True, ""

    def export_mapping_report(self) -> Dict:
        """Generate audit report of all row allocations."""
        return {
            "header_rows": self.header_rows,
            "total_sessions": len(self._session_mappings),
            "sessions": {
                session_id: {
                    "start_row": m.start_row,
                    "end_row": m.end_row,
                    "question_count": m.question_count,
                    "row_count": m.row_count
                }
                for session_id, m in self._session_mappings.items()
            },
            "next_available_row": self._next_available_row
        }
