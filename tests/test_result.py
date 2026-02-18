"""Tests for Result type."""

import pytest

from v2ray_finder.result import Err, Ok, Result


def test_ok_creation():
    """Test Ok result creation."""
    result = Ok(42)
    assert result.is_ok()
    assert not result.is_err()
    assert result.value == 42


def test_err_creation():
    """Test Err result creation."""
    result = Err("error message")
    assert result.is_err()
    assert not result.is_ok()
    assert result.error == "error message"


def test_ok_unwrap():
    """Test unwrapping Ok result."""
    result = Ok("success")
    assert result.unwrap() == "success"


def test_err_unwrap_raises():
    """Test that unwrapping Err raises."""
    result = Err("failure")
    with pytest.raises(RuntimeError) as exc_info:
        result.unwrap()
    assert "failure" in str(exc_info.value)


def test_ok_unwrap_or():
    """Test unwrap_or with Ok."""
    result = Ok(10)
    assert result.unwrap_or(20) == 10


def test_err_unwrap_or():
    """Test unwrap_or with Err."""
    result = Err("error")
    assert result.unwrap_or(20) == 20


def test_ok_map():
    """Test mapping over Ok result."""
    result = Ok(5)
    mapped = result.map(lambda x: x * 2)
    assert mapped.is_ok()
    assert mapped.unwrap() == 10


def test_err_map():
    """Test mapping over Err result (should not apply function)."""
    result = Err("error")
    mapped = result.map(lambda x: x * 2)
    assert mapped.is_err()
    assert mapped.error == "error"


def test_ok_map_err():
    """Test map_err over Ok (should not apply function)."""
    result = Ok(5)
    mapped = result.map_err(lambda e: f"Error: {e}")
    assert mapped.is_ok()
    assert mapped.unwrap() == 5


def test_err_map_err():
    """Test map_err over Err result."""
    result = Err("failure")
    mapped = result.map_err(lambda e: f"Error: {e}")
    assert mapped.is_err()
    assert mapped.error == "Error: failure"


def test_result_type_annotation():
    """Test that Result can be used in type annotations."""

    def divide(a: int, b: int) -> Result[float, str]:
        if b == 0:
            return Err("Division by zero")
        return Ok(a / b)

    result1 = divide(10, 2)
    assert result1.is_ok()
    assert result1.unwrap() == 5.0

    result2 = divide(10, 0)
    assert result2.is_err()
    assert result2.error == "Division by zero"


def test_chaining_operations():
    """Test chaining map operations."""
    result = Ok(5)
    final = result.map(lambda x: x * 2).map(lambda x: x + 3)
    assert final.unwrap() == 13


def test_error_propagation():
    """Test that errors propagate through map chains."""
    result = Err("initial error")
    final = result.map(lambda x: x * 2).map(lambda x: x + 3)
    assert final.is_err()
    assert final.error == "initial error"
