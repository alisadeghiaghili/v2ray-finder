"""Custom exceptions for v2ray_finder.

This module provides a comprehensive exception hierarchy for proper error handling
and user-friendly error messages.
"""

from enum import Enum
from typing import Any, Optional


class ErrorType(Enum):
    """Types of errors that can occur during server discovery."""

    # Network errors
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    CONNECTION_ERROR = "connection_error"

    # GitHub API errors
    GITHUB_API_ERROR = "github_api_error"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    AUTHENTICATION_ERROR = "authentication_error"
    REPOSITORY_NOT_FOUND = "repository_not_found"

    # Parsing errors
    PARSE_ERROR = "parse_error"
    INVALID_CONFIG = "invalid_config"

    # General errors
    UNKNOWN_ERROR = "unknown_error"
    VALIDATION_ERROR = "validation_error"


class V2RayFinderError(Exception):
    """Base exception for all v2ray_finder errors.

    Attributes:
        message: Human-readable error message
        error_type: Type of error from ErrorType enum
        details: Optional dict with additional error context
    """

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.UNKNOWN_ERROR,
        details: Optional[dict] = None,
    ):
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        base = f"[{self.error_type.value}] {self.message}"
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{base} ({details_str})"
        return base

    def to_dict(self) -> dict:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "details": self.details,
        }


class NetworkError(V2RayFinderError):
    """Raised when network-related errors occur."""

    def __init__(self, message: str, url: Optional[str] = None, **kwargs):
        details = {"url": url} if url else {}
        details.update(kwargs)
        super().__init__(message, ErrorType.NETWORK_ERROR, details)


class TimeoutError(V2RayFinderError):
    """Raised when a request times out."""

    def __init__(
        self, message: str, url: Optional[str] = None, timeout: Optional[float] = None
    ):
        details = {}
        if url:
            details["url"] = url
        if timeout:
            details["timeout_seconds"] = timeout
        super().__init__(message, ErrorType.TIMEOUT_ERROR, details)


class GitHubAPIError(V2RayFinderError):
    """Raised when GitHub API returns an error."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_type: ErrorType = ErrorType.GITHUB_API_ERROR,
        **kwargs,
    ):
        details = {"status_code": status_code} if status_code else {}
        details.update(kwargs)
        super().__init__(message, error_type, details)


class RateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded.

    Attributes:
        limit: Total rate limit
        remaining: Remaining requests
        reset_time: Unix timestamp when rate limit resets
    """

    def __init__(
        self,
        message: str = "GitHub API rate limit exceeded",
        limit: Optional[int] = None,
        remaining: Optional[int] = None,
        reset_time: Optional[int] = None,
    ):
        details = {}
        if limit is not None:
            details["limit"] = limit
        if remaining is not None:
            details["remaining"] = remaining
        if reset_time is not None:
            details["reset_time"] = reset_time
            from datetime import datetime

            details["reset_at"] = datetime.fromtimestamp(reset_time).isoformat()

        super().__init__(
            message,
            status_code=429,
            error_type=ErrorType.RATE_LIMIT_EXCEEDED,
            **details,
        )


class AuthenticationError(GitHubAPIError):
    """Raised when GitHub authentication fails."""

    def __init__(self, message: str = "GitHub authentication failed"):
        super().__init__(
            message, status_code=401, error_type=ErrorType.AUTHENTICATION_ERROR
        )


class RepositoryNotFoundError(GitHubAPIError):
    """Raised when a repository is not found or not accessible."""

    def __init__(self, repo_name: str):
        message = f"Repository not found or not accessible: {repo_name}"
        super().__init__(
            message,
            status_code=404,
            error_type=ErrorType.REPOSITORY_NOT_FOUND,
            repository=repo_name,
        )


class ParseError(V2RayFinderError):
    """Raised when parsing server configs fails."""

    def __init__(self, message: str, content_preview: Optional[str] = None):
        details = {}
        if content_preview:
            details["content_preview"] = (
                content_preview[:100] + "..."
                if len(content_preview) > 100
                else content_preview
            )
        super().__init__(message, ErrorType.PARSE_ERROR, details)


class ValidationError(V2RayFinderError):
    """Raised when server config validation fails."""

    def __init__(self, message: str, config: Optional[str] = None):
        details = {}
        if config:
            # Only include first 50 chars to avoid leaking sensitive data
            details["config_preview"] = config[:50] + "..."
        super().__init__(message, ErrorType.VALIDATION_ERROR, details)
