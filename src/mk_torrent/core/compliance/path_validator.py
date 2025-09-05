"""
Path validation for different trackers
"""

from pathlib import Path
from typing import Any
from dataclasses import dataclass
import unicodedata
import logging

logger = logging.getLogger(__name__)


@dataclass
class PathRule:
    """Path validation rule"""

    max_length: int = 255
    forbidden_chars: list[str] | None = None
    require_unicode_nfc: bool = False

    def __post_init__(self):
        if self.forbidden_chars is None:
            self.forbidden_chars = []


class PathValidator:
    """Validates paths against tracker requirements"""

    # Tracker-specific rules
    TRACKER_RULES = {
        "red": PathRule(max_length=150, require_unicode_nfc=True),
        "redacted": PathRule(max_length=150, require_unicode_nfc=True),
        "mam": PathRule(max_length=255),
        "myanonamouse": PathRule(max_length=255),
        "ops": PathRule(max_length=180),
        "orpheus": PathRule(max_length=180),
        "default": PathRule(max_length=255),
    }

    def __init__(self, tracker: str = "default"):
        self.tracker = tracker.lower()
        self.rule = self.TRACKER_RULES.get(self.tracker, self.TRACKER_RULES["default"])

    def validate(self, path: Path) -> tuple[bool, list[str]]:
        """Validate a path against tracker rules"""
        issues: list[str] = []
        path_str = str(path)

        # Check length
        if len(path_str) > self.rule.max_length:
            issues.append(
                f"Path exceeds {self.rule.max_length} character limit "
                f"({len(path_str)} chars)"
            )

        # Check forbidden characters
        for char in self.rule.forbidden_chars or []:
            if char in path_str:
                issues.append(f"Contains forbidden character: '{char}'")

        # Check Unicode normalization
        if self.rule.require_unicode_nfc:
            normalized = unicodedata.normalize("NFC", path_str)
            if normalized != path_str:
                issues.append("Path is not Unicode NFC normalized")

        return len(issues) == 0, issues

    def validate_tree(self, root: Path) -> dict[str, Any]:
        """Validate all paths in a directory tree"""
        invalid_files: list[dict[str, Any]] = []
        total_files = 0
        longest_path = ""
        longest_length = 0

        for file_path in root.rglob("*"):
            if file_path.is_file():
                total_files += 1

                # Check this file's full path
                full_path = str(file_path)
                valid, issues = self.validate(file_path)

                if not valid:
                    invalid_files.append(
                        {
                            "path": full_path,
                            "length": len(full_path),
                            "issues": issues,
                            "overage": (
                                len(full_path) - self.rule.max_length
                                if len(full_path) > self.rule.max_length
                                else 0
                            ),
                        }
                    )

                # Track longest path
                if len(full_path) > longest_length:
                    longest_path = full_path
                    longest_length = len(full_path)

        # Calculate compliance rate
        if total_files > 0:
            valid_files = total_files - len(invalid_files)
            compliance_rate = valid_files / total_files
        else:
            compliance_rate = 1.0

        results: dict[str, Any] = {
            "valid": len(invalid_files) == 0,
            "total_files": total_files,
            "invalid_files": invalid_files,
            "longest_path": longest_path,
            "longest_length": longest_length,
            "tracker": self.tracker,
            "max_length": self.rule.max_length,
            "compliance_rate": compliance_rate,
        }

        return results

    def check_single_path(self, path_str: str) -> dict[str, Any]:
        """Check a single path string for compliance"""
        valid, issues = self.validate(Path(path_str))

        return {
            "path": path_str,
            "length": len(path_str),
            "valid": valid,
            "issues": issues,
            "overage": (
                len(path_str) - self.rule.max_length
                if len(path_str) > self.rule.max_length
                else 0
            ),
            "tracker": self.tracker,
            "max_length": self.rule.max_length,
        }

    @classmethod
    def get_available_trackers(cls) -> list[str]:
        """Get list of available tracker rules"""
        return [k for k in cls.TRACKER_RULES.keys() if k != "default"]

    @classmethod
    def compare_trackers(cls, path_str: str) -> dict[str, dict[str, Any]]:
        """Compare path compliance across all trackers"""
        results = {}

        for tracker in cls.get_available_trackers():
            validator = cls(tracker)
            results[tracker] = validator.check_single_path(path_str)

        return results  # type: ignore[return-value]
