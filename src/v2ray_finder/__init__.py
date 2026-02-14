"""V2Ray server finder - Search and collect V2Ray configs from GitHub"""

__version__ = "0.1.0"
__author__ = "Ali Sadeghi Aghili"
__email__ = "alisadeghiaghili@gmail.com"

from .core import V2RayServerFinder
from .health_checker import (
    HealthChecker,
    ServerHealth,
    HealthStatus,
    ServerValidator,
    filter_healthy_servers,
    sort_by_quality,
)
from .exceptions import (
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
from .result import Result, Ok, Err

__all__ = [
    # Core
    "V2RayServerFinder",
    # Health checking
    "HealthChecker",
    "ServerHealth",
    "HealthStatus",
    "ServerValidator",
    "filter_healthy_servers",
    "sort_by_quality",
    # Exceptions
    "V2RayFinderError",
    "ErrorType",
    "NetworkError",
    "TimeoutError",
    "GitHubAPIError",
    "RateLimitError",
    "AuthenticationError",
    "RepositoryNotFoundError",
    "ParseError",
    "ValidationError",
    # Result type
    "Result",
    "Ok",
    "Err",
]
