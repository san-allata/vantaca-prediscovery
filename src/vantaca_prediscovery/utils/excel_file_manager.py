import shutil
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ExcelFileManager:
    """
    Manages Excel file safety through backups and rollback capability.
    Maintains an operation log for audit trails.
    """

    def __init__(self, excel_path: str, backup_dir: Optional[str] = None):
        self.excel_path = Path(excel_path)
        self.backup_dir = Path(backup_dir or self.excel_path.parent / ".backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.operation_log_path = self.backup_dir / f"{self.excel_path.stem}_operations.json"

    def create_backup(self, operation_name: str) -> str:
        """
        Create timestamped backup before operation.

        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{self.excel_path.stem}_{operation_name}_{timestamp}.bak"

        try:
            shutil.copy2(self.excel_path, backup_path)
            logger.info(f"Created backup: {backup_path}")

            # Log this backup
            self._log_operation("BACKUP_CREATED", {
                "backup_path": str(backup_path),
                "original_file": str(self.excel_path),
                "operation": operation_name,
                "file_hash": self._calculate_hash(self.excel_path)
            })

            return str(backup_path)
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            raise RuntimeError(f"Cannot proceed without backup: {e}")

    def rollback(self, backup_path: str, reason: str = "Manual rollback") -> bool:
        """
        Restore from backup file.

        Args:
            backup_path: Path to backup file
            reason: Why rollback was triggered

        Returns:
            True if rollback succeeded
        """
        backup_file = Path(backup_path)

        if not backup_file.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False

        try:
            # Create safety copy before rollback
            emergency_backup = (
                self.backup_dir /
                f"{self.excel_path.stem}_emergency_before_rollback.bak"
            )
            shutil.copy2(self.excel_path, emergency_backup)

            # Restore from backup
            shutil.copy2(backup_file, self.excel_path)

            self._log_operation("ROLLBACK_COMPLETED", {
                "backup_source": backup_path,
                "emergency_backup": str(emergency_backup),
                "reason": reason
            })

            logger.info(f"Successfully rolled back from {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def verify_file_integrity(self) -> dict:
        """Verify file is readable and not corrupted."""
        try:
            from openpyxl import load_workbook
            workbook = load_workbook(self.excel_path)
            workbook.close()

            return {
                "is_valid": True,
                "file_hash": self._calculate_hash(self.excel_path),
                "file_size": self.excel_path.stat().st_size
            }
        except Exception as e:
            return {
                "is_valid": False,
                "error": str(e)
            }

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _log_operation(self, operation: str, details: dict) -> None:
        """Append operation to audit log."""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "details": details
            }

            operations = []
            if self.operation_log_path.exists():
                with open(self.operation_log_path, "r") as f:
                    operations = json.load(f)

            operations.append(log_entry)

            with open(self.operation_log_path, "w") as f:
                json.dump(operations, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to log operation: {e}")

    def get_operation_log(self) -> list:
        """Return all logged operations."""
        if self.operation_log_path.exists():
            with open(self.operation_log_path, "r") as f:
                return json.load(f)
        return []

    def cleanup_old_backups(self, keep_count: int = 5) -> None:
        """Keep only the N most recent backups."""
        backups = sorted(
            self.backup_dir.glob(f"{self.excel_path.stem}_*.bak"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for old_backup in backups[keep_count:]:
            old_backup.unlink()
            logger.info(f"Removed old backup: {old_backup}")
