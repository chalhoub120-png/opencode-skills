"""Request validation for API endpoints."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from security.redaction import sanitize

logger = logging.getLogger(__name__)


class RequestValidator:
    """Validates incoming API requests."""

    MAX_MESSAGE_LENGTH = 10000
    MAX_QUERY_LENGTH = 2000
    MAX_FILENAME_LENGTH = 255
    MAX_TOP_K = 20
    DEFAULT_TOP_K = 5

    @staticmethod
    def validate_message(message: str) -> Optional[str]:
        """Validate a user chat message. Returns error message or None."""
        if not message or not message.strip():
            return "Message cannot be empty"
        if len(message) > RequestValidator.MAX_MESSAGE_LENGTH:
            return f"Message exceeds maximum length of {RequestValidator.MAX_MESSAGE_LENGTH} characters"
        return None

    @staticmethod
    def validate_query(query: str) -> Optional[str]:
        """Validate a search query (shorter limit than a chat message)."""
        if not query or not query.strip():
            return "Query cannot be empty"
        if len(query) > RequestValidator.MAX_QUERY_LENGTH:
            return f"Query exceeds maximum length of {RequestValidator.MAX_QUERY_LENGTH} characters"
        return None

    @staticmethod
    def validate_language(language: str) -> Optional[str]:
        """Validate language code."""
        allowed = {"ar", "en", "lb"}
        if language not in allowed:
            return f"Unsupported language: {language}. Allowed: {', '.join(sorted(allowed))}"
        return None

    @staticmethod
    def validate_filename(filename: str) -> Optional[str]:
        """Validate an uploaded filename."""
        if not filename:
            return "Filename is required"
        if len(filename) > RequestValidator.MAX_FILENAME_LENGTH:
            return "Filename too long"
        # Block path traversal
        if ".." in filename or filename.startswith("/") or "\\" in filename:
            return "Invalid filename: path traversal not allowed"
        return None

    @staticmethod
    def validate_task_status(status: str) -> Optional[str]:
        allowed = {"pending", "in_progress", "completed", "failed", "cancelled"}
        if status not in allowed:
            return f"Invalid status: {status}. Allowed: {', '.join(sorted(allowed))}"
        return None

    @staticmethod
    def normalize_top_k(value: Any) -> int:
        """Clamp a caller-supplied top_k into a safe range."""
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return RequestValidator.DEFAULT_TOP_K
        if parsed < 1:
            return 1
        return min(parsed, RequestValidator.MAX_TOP_K)

    @staticmethod
    def validate_uuid(value: str, field: str = "id") -> Optional[str]:
        """Validate a UUID string. Returns error message or None."""
        try:
            uuid.UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            return f"Invalid {field}: must be a UUID"
        return None

    @staticmethod
    def validate_idempotency_key(key: str) -> Optional[str]:
        """Validate an Idempotency-Key header value.

        Follows the IETF idempotency-key draft: an opaque, bounded token.
        Restricting the charset keeps the value safe for logs and indexes.
        """
        if not key:
            return "Idempotency-Key cannot be empty"
        if not (8 <= len(key) <= 255):
            return "Idempotency-Key must be between 8 and 255 characters"
        allowed = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-"
        )
        if any(ch not in allowed for ch in key):
            return "Idempotency-Key contains unsupported characters"
        return None

    @staticmethod
    def sanitize_log_value(value: Any) -> Any:
        """Recursively redact secrets before logging (delegates to redaction)."""
        return sanitize(value)
