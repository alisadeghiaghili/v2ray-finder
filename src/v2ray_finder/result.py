"""Result type for better error handling.

Provides a Result[T, E] type similar to Rust's Result enum for explicit error handling.
"""

from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar, Union

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")
F = TypeVar("F")


@dataclass
class Ok(Generic[T]):
    """Represents a successful result."""

    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, default: T) -> T:
        return self.value

    def map(self, func: Callable[[T], U]) -> "Result[U, E]":
        return Ok(func(self.value))

    def map_err(self, func: Callable[[E], F]) -> "Result[T, F]":
        return Ok(self.value)


@dataclass
class Err(Generic[E]):
    """Represents an error result."""

    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self):
        raise RuntimeError(f"Called unwrap() on Err: {self.error}")

    def unwrap_or(self, default: T) -> T:
        return default

    def map(self, func: Callable[[T], U]) -> "Result[U, E]":
        return Err(self.error)

    def map_err(self, func: Callable[[E], F]) -> "Result[T, F]":
        return Err(func(self.error))


Result = Union[Ok[T], Err[E]]
