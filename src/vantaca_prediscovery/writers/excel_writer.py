class ExcelAnswerWriter:
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.file_manager = ExcelFileManager(excel_path)
        self.backup_path = None

    def start_session(self, session_name: str) -> bool:
        """Begin Excel modification with backup."""
        try:
            # Verify file integrity before starting
            integrity = self.file_manager.verify_file_integrity()
            if not integrity["is_valid"]:
                raise RuntimeError(f"File corrupted before operation: {integrity}")

            # Create backup
            self.backup_path = self.file_manager.create_backup(session_name)
            return True

        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            return False

    def complete_session(self) -> bool:
        """Finalize session with verification."""
        try:
            workbook.save(self.excel_path)

            # Verify integrity after save
            integrity = self.file_manager.verify_file_integrity()
            if not integrity["is_valid"]:
                logger.error("File corrupted after save, initiating rollback")
                self.file_manager.rollback(
                    self.backup_path,
                    "Post-save corruption detected"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Session failed: {e}, rolling back")
            if self.backup_path:
                self.file_manager.rollback(self.backup_path, str(e))
            return False

    def cleanup(self) -> None:
        """Clean up old backups."""
        self.file_manager.cleanup_old_backups(keep_count=5)
