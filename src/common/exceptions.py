from enum import Enum
from typing import Optional

class ErrorCode(str, Enum):
    """Application-level error codes returned in API and domain errors."""

    RESUME_NOT_FOUND = "RESUME_NOT_FOUND"
    RESUME_PARSE_FAILED = "RESUME_PARSE_FAILED"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    FILE_TOO_LARGE_ERROR = "FILE_TOO_LARGE_ERROR"
    KB_NOT_FOUND = "KB_NOT_FOUND"
    KB_PARSE_FAILED = "KB_PARSE_FAILED"
    KB_VECTORIZE_ERROR = "KB_VECTORIZE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_FOUND = "NOT_FOUND"
    INTERVIEW_SESSION_NOT_FOUND = "INTERVIEW_SESSION_NOT_FOUND"
    SANDBOX_POLICY_VIOLATION = "SANDBOX_POLICY_VIOLATION"
    SANDBOX_SCRIPT_TIMEOUT = "SANDBOX_SCRIPT_TIMEOUT"
    SANDBOX_SCRIPT_EXECUTION_FAILED = "SANDBOX_SCRIPT_EXECUTION_FAILED"


class BusinessException(Exception):
    """Business exception carrying stable error code and optional details."""

    def __init__(self, code: ErrorCode, message: str, details: Optional[str] = None):
        """Create a business exception with code, message, and optional details."""
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
