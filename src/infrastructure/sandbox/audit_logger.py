"""Audit logging support for sandbox script execution."""
import logging

logger = logging.getLogger(__file__)

class SandboxAuditLogger:
    """Emit audit summaries for sandbox script runs."""

    def log_run_summary(self, summary: dict[str, object]) -> None:
        """Record one sandbox execution summary for audit consumers."""
        # Current implementation is intentionally minimal and side-effect free.
        # It provides a stable extension point for persistence/integration later.
        logger.info(f"Script execution summary: {summary}")
