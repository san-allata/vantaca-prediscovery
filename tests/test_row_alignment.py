import pytest
from src.vantaca_prediscovery.utils.row_alignment_manager import RowAlignmentManager, SessionRowMapping


class TestRowAlignmentManager:
    def setup_method(self):
        self.manager = RowAlignmentManager(header_rows=5)

    def test_register_first_session(self):
        mapping = self.manager.register_session("session_1", 10)
        assert mapping.start_row == 6  # 5 headers + 1
        assert mapping.end_row == 15
        assert mapping.question_count == 10

    def test_register_sequential_sessions(self):
        m1 = self.manager.register_session("session_1", 10)
        m2 = self.manager.register_session("session_2", 8)

        assert m1.end_row + 1 == m2.start_row
        assert m2.start_row == 16
        assert m2.end_row == 23

    def test_prevent_duplicate_registration(self):
        self.manager.register_session("session_1", 10)

        with pytest.raises(ValueError, match="already registered"):
            self.manager.register_session("session_1", 5)

    def test_validate_write_in_range(self):
        self.manager.register_session("session_1", 10)
        is_valid, error = self.manager.validate_write(
            "session_1", 10, "test answer"
        )
        assert is_valid
        assert error == ""

    def test_validate_write_out_of_range(self):
        self.manager.register_session("session_1", 10)
        is_valid, error = self.manager.validate_write(
            "session_1", 20, "test answer"
        )
        assert not is_valid
        assert "outside session bounds" in error

    def test_prevent_collision(self):
        self.manager.register_session("session_1", 10)
        self.manager.register_session("session_2", 8)

        # Try to write session_1's answer in session_2's space
        is_valid, error = self.manager.validate_write(
            "session_1", 16, "collision test"
        )
        assert not is_valid
        assert "already allocated" in error

    def test_export_audit_report(self):
        self.manager.register_session("session_1", 10)
        self.manager.register_session("session_2", 8)

        report = self.manager.export_mapping_report()
        assert report["total_sessions"] == 2
        assert "session_1" in report["sessions"]
        assert "session_2" in report["sessions"]
        assert report["next_available_row"] == 24
