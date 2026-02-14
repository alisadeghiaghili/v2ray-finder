"""Tests for custom exceptions."""

import pytest
from v2ray_finder.exceptions import (
    V2RayFinderError,
    ErrorType,
    NetworkError,
    TimeoutError,
    GitHubAPIError,
    RateLimitError,
    AuthenticationError,
    RepositoryNotFoundError,
    ParseError,
    ValidationError,
)


def test_base_exception():
    """Test base V2RayFinderError."""
    error = V2RayFinderError(
        "Test error",
        error_type=ErrorType.NETWORK_ERROR,
        details={"url": "https://example.com"},
    )
    
    assert error.message == "Test error"
    assert error.error_type == ErrorType.NETWORK_ERROR
    assert error.details["url"] == "https://example.com"
    assert "network_error" in str(error)
    assert "Test error" in str(error)


def test_exception_to_dict():
    """Test exception serialization."""
    error = NetworkError("Connection failed", url="https://api.github.com")
    error_dict = error.to_dict()
    
    assert error_dict["error_type"] == "network_error"
    assert error_dict["message"] == "Connection failed"
    assert error_dict["details"]["url"] == "https://api.github.com"


def test_network_error():
    """Test NetworkError exception."""
    error = NetworkError("Failed to connect", url="https://example.com")
    
    assert isinstance(error, V2RayFinderError)
    assert error.error_type == ErrorType.NETWORK_ERROR
    assert error.details["url"] == "https://example.com"


def test_timeout_error():
    """Test TimeoutError exception."""
    error = TimeoutError(
        "Request timed out",
        url="https://example.com",
        timeout=10.0,
    )
    
    assert error.error_type == ErrorType.TIMEOUT_ERROR
    assert error.details["timeout_seconds"] == 10.0


def test_rate_limit_error():
    """Test RateLimitError with full details."""
    error = RateLimitError(
        limit=60,
        remaining=0,
        reset_time=1234567890,
    )
    
    assert error.error_type == ErrorType.RATE_LIMIT_EXCEEDED
    assert error.details["limit"] == 60
    assert error.details["remaining"] == 0
    assert error.details["reset_time"] == 1234567890
    assert "reset_at" in error.details
    assert error.details["status_code"] == 429


def test_authentication_error():
    """Test AuthenticationError."""
    error = AuthenticationError()
    
    assert error.error_type == ErrorType.AUTHENTICATION_ERROR
    assert error.details["status_code"] == 401
    assert "authentication" in error.message.lower()


def test_repository_not_found_error():
    """Test RepositoryNotFoundError."""
    error = RepositoryNotFoundError("user/repo")
    
    assert error.error_type == ErrorType.REPOSITORY_NOT_FOUND
    assert error.details["repository"] == "user/repo"
    assert error.details["status_code"] == 404
    assert "user/repo" in error.message


def test_parse_error():
    """Test ParseError."""
    content = "x" * 200
    error = ParseError("Failed to parse", content_preview=content)
    
    assert error.error_type == ErrorType.PARSE_ERROR
    # Should truncate long content
    assert len(error.details["content_preview"]) < len(content)
    assert "..." in error.details["content_preview"]


def test_validation_error():
    """Test ValidationError."""
    config = "vmess://" + "x" * 100
    error = ValidationError("Invalid config", config=config)
    
    assert error.error_type == ErrorType.VALIDATION_ERROR
    # Should only include preview (first 50 chars)
    assert len(error.details["config_preview"]) <= 53  # 50 + "..."


def test_error_hierarchy():
    """Test exception hierarchy."""
    # All custom exceptions should inherit from V2RayFinderError
    assert issubclass(NetworkError, V2RayFinderError)
    assert issubclass(GitHubAPIError, V2RayFinderError)
    assert issubclass(RateLimitError, GitHubAPIError)
    assert issubclass(AuthenticationError, GitHubAPIError)


def test_exception_can_be_raised():
    """Test that exceptions can be raised and caught."""
    with pytest.raises(V2RayFinderError) as exc_info:
        raise NetworkError("Test", url="https://example.com")
    
    assert exc_info.value.error_type == ErrorType.NETWORK_ERROR


def test_exception_string_representation():
    """Test exception string formatting."""
    error = RateLimitError(limit=60, remaining=0)
    error_str = str(error)
    
    assert "rate_limit_exceeded" in error_str
    assert "limit=60" in error_str
    assert "remaining=0" in error_str
