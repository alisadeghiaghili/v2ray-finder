"""Core module for V2Ray server discovery with improved error handling."""

import logging
import os
import re
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import requests

from .exceptions import (
    AuthenticationError,
    ErrorType,
    GitHubAPIError,
    NetworkError,
    ParseError,
    RateLimitError,
    RepositoryNotFoundError,
    TimeoutError,
    V2RayFinderError,
    ValidationError,
)
from .result import Err, Ok, Result

logger = logging.getLogger(__name__)


class V2RayServerFinder:
    """
    V2Ray server finder that aggregates configs from GitHub and curated sources.

    Attributes:
        BASE_URL: GitHub API base URL
        DIRECT_SOURCES: List of curated direct subscription URLs
    """

    BASE_URL = "https://api.github.com"

    DIRECT_SOURCES = [
        "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/refs/heads/main/V2Ray-Config-By-EbraSha.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Sub1.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_Sub.txt",
    ]

    # Environment variable name for token
    TOKEN_ENV_VAR = "GITHUB_TOKEN"

    def __init__(self, token: Optional[str] = None, raise_errors: bool = False):
        """
        Initialize V2RayServerFinder.

        Args:
            token: Optional GitHub personal access token for higher API rate limits.
                   If not provided, will attempt to read from GITHUB_TOKEN environment variable.

                   SECURITY WARNING: Passing tokens directly as strings can expose them in:
                   - Process listings (ps, top)
                   - Shell history
                   - Application logs
                   - Exception tracebacks

                   RECOMMENDED: Use environment variables instead:
                     export GITHUB_TOKEN="your_token_here"
                     finder = V2RayServerFinder()  # Will read from env

            raise_errors: If True, raise exceptions instead of logging and returning empty results.
                         This is useful for applications that want explicit error handling.
        """
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        self.raise_errors = raise_errors
        self._last_rate_limit_info: Optional[Dict] = None
        self._token_source: str = "none"

        # Stop mechanism for graceful interruption
        self._stop_requested = threading.Event()
        self._lock = threading.Lock()

        # Try to get token from environment if not provided
        if token is None:
            token = os.environ.get(self.TOKEN_ENV_VAR)
            if token:
                self._token_source = "environment"
                logger.debug(
                    f"Using GitHub token from {self.TOKEN_ENV_VAR} environment variable"
                )
        else:
            self._token_source = "parameter"
            # Warn about security risk
            logger.warning(
                "Security Warning: GitHub token passed as parameter. "
                f"Consider using {self.TOKEN_ENV_VAR} environment variable instead to avoid token exposure."
            )

        # Validate and sanitize token
        if token:
            token = self._validate_and_sanitize_token(token)
            if token:  # Only set if validation passed
                self.headers["Authorization"] = f"token {token}"
                logger.info(f"GitHub token configured from {self._token_source}")
            else:
                logger.warning(
                    "Invalid token format - proceeding without authentication (rate limit: 60/hour)"
                )
        else:
            logger.info(
                "No GitHub token provided - using unauthenticated access (rate limit: 60/hour)"
            )

    def request_stop(self):
        """Request graceful stop of ongoing operations."""
        self._stop_requested.set()
        logger.info("Stop requested - operations will terminate gracefully")

    def reset_stop(self):
        """Reset stop flag for new operations."""
        self._stop_requested.clear()

    def should_stop(self) -> bool:
        """Check if stop has been requested.

        Returns:
            True if stop was requested, False otherwise
        """
        return self._stop_requested.is_set()

    def _validate_and_sanitize_token(self, token: str) -> Optional[str]:
        """
        Validate and sanitize GitHub token.

        Args:
            token: Raw token string

        Returns:
            Sanitized token if valid, None if invalid
        """
        # Strip whitespace
        token = token.strip()

        # Check for empty token
        if not token:
            logger.error("Empty token provided")
            return None

        # Validate token format
        # GitHub personal access tokens typically start with ghp_ (classic) or github_pat_ (fine-grained)
        # OAuth tokens start with gho_
        # But we'll be lenient and accept any reasonable token format

        # Check minimum length (GitHub tokens are typically 40+ characters)
        if len(token) < 20:
            logger.error(
                f"Token too short ({len(token)} chars). GitHub tokens are typically 40+ characters."
            )
            return None

        # Check for suspicious characters (tokens should be alphanumeric + underscore)
        if not re.match(r"^[a-zA-Z0-9_]+$", token):
            logger.error(
                "Token contains invalid characters. GitHub tokens should be alphanumeric."
            )
            return None

        # Validate known token prefixes (informational, not enforced)
        known_prefixes = ["ghp_", "gho_", "ghu_", "ghs_", "ghr_", "github_pat_"]
        has_known_prefix = any(token.startswith(prefix) for prefix in known_prefixes)

        if not has_known_prefix:
            logger.warning(
                f"Token doesn't start with a known GitHub prefix ({', '.join(known_prefixes)}). "
                "This might be an old token format or invalid token."
            )

        # Log token info without exposing the token itself
        token_preview = f"{token[:4]}...{token[-4:]}" if len(token) > 8 else "****"
        logger.debug(
            f"Token validated: {token_preview} ({len(token)} chars, source: {self._token_source})"
        )

        return token

    @classmethod
    def from_env(cls, raise_errors: bool = False) -> "V2RayServerFinder":
        """
        Create V2RayServerFinder instance using token from environment variable.

        This is the recommended way to initialize the finder with authentication.

        Args:
            raise_errors: If True, raise exceptions instead of logging errors

        Returns:
            V2RayServerFinder instance

        Example:
            export GITHUB_TOKEN="your_token_here"
            finder = V2RayServerFinder.from_env()
        """
        return cls(token=None, raise_errors=raise_errors)

    def _check_rate_limit(self, response: requests.Response) -> None:
        """Check and store rate limit information from response headers.

        Args:
            response: HTTP response object

        Raises:
            RateLimitError: If rate limit is exceeded
        """
        if response.status_code == 403 or response.status_code == 429:
            limit = response.headers.get("X-RateLimit-Limit")
            remaining = response.headers.get("X-RateLimit-Remaining")
            reset = response.headers.get("X-RateLimit-Reset")

            self._last_rate_limit_info = {
                "limit": int(limit) if limit else None,
                "remaining": int(remaining) if remaining else None,
                "reset": int(reset) if reset else None,
            }

            if remaining == "0" or response.status_code == 429:
                raise RateLimitError(
                    limit=self._last_rate_limit_info["limit"],
                    remaining=self._last_rate_limit_info["remaining"],
                    reset_time=self._last_rate_limit_info["reset"],
                )
        else:
            # Update rate limit info from successful requests
            limit = response.headers.get("X-RateLimit-Limit")
            remaining = response.headers.get("X-RateLimit-Remaining")
            reset = response.headers.get("X-RateLimit-Reset")

            if limit and remaining:
                try:
                    self._last_rate_limit_info = {
                        "limit": int(limit),
                        "remaining": int(remaining),
                        "reset": int(reset) if reset else None,
                    }

                    # Warn if getting close to limit
                    if int(remaining) < 10:
                        logger.warning(
                            f"GitHub API rate limit low: {remaining}/{limit} remaining. "
                            f"Consider using a GitHub token for higher limits."
                        )
                except (ValueError, TypeError):
                    logger.debug(
                        f"Malformed rate limit headers ignored: "
                        f"limit={limit!r}, remaining={remaining!r}, reset={reset!r}"
                    )

    def get_rate_limit_info(self) -> Optional[Dict]:
        """Get the last known rate limit information.

        Returns:
            Dict with 'limit', 'remaining', and 'reset' keys, or None if no requests made yet.
        """
        return self._last_rate_limit_info.copy() if self._last_rate_limit_info else None

    def search_repos(
        self, keywords: Optional[List[str]] = None, max_results: int = 30
    ) -> Result[List[Dict], V2RayFinderError]:
        """
        Search GitHub repositories matching keywords.

        Args:
            keywords: List of search keywords (default: ["v2ray", "free", "config"])
            max_results: Maximum number of results to return

        Returns:
            Result[List[Dict], V2RayFinderError]: Ok with list of repository metadata,
                                                   or Err with error details
        """
        if self.should_stop():
            logger.info("Search repos stopped by user request")
            return Ok([])

        if keywords is None:
            keywords = ["v2ray", "free", "config"]

        query = "+".join(keywords)
        url = f"{self.BASE_URL}/search/repositories"
        params = {
            "q": query,
            "sort": "updated",
            "order": "desc",
            "per_page": min(max_results, 100),
        }

        try:
            response = requests.get(
                url, headers=self.headers, params=params, timeout=10
            )

            # Handle HTTP errors first (before _check_rate_limit to avoid
            # TypeError when mock headers return non-string values)
            if response.status_code == 401:
                raise AuthenticationError("Invalid or expired GitHub token")
            elif response.status_code == 404:
                raise GitHubAPIError("GitHub API endpoint not found", status_code=404)

            # Then check rate limits
            self._check_rate_limit(response)

            response.raise_for_status()
            data = response.json()

            results = []
            for repo in data.get("items", []):
                if self.should_stop():
                    logger.info(f"Search repos interrupted after {len(results)} repos")
                    break

                results.append(
                    {
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "description": repo.get("description", ""),
                        "stars": repo["stargazers_count"],
                        "updated_at": repo["updated_at"],
                        "url": repo["html_url"],
                    }
                )

            logger.info(f"Found {len(results)} repositories matching '{query}'")
            return Ok(results)

        except RateLimitError as e:
            logger.error(f"GitHub rate limit exceeded: {e}")
            return Err(e)
        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            return Err(e)
        except requests.exceptions.Timeout as e:
            error = TimeoutError(
                f"Request timed out while searching repositories", url=url, timeout=10.0
            )
            logger.error(str(error))
            return Err(error)
        except requests.exceptions.ConnectionError as e:
            error = NetworkError(
                f"Connection error while searching repositories: {e}", url=url
            )
            logger.error(str(error))
            return Err(error)
        except requests.exceptions.RequestException as e:
            error = GitHubAPIError(
                f"GitHub API request failed: {e}",
                status_code=(
                    getattr(response, "status_code", None)
                    if "response" in locals()
                    else None
                ),
            )
            logger.error(str(error))
            return Err(error)
        except Exception as e:
            error = V2RayFinderError(
                f"Unexpected error during repository search: {e}",
                ErrorType.UNKNOWN_ERROR,
            )
            logger.error(str(error), exc_info=True)
            return Err(error)

    def search_repos_or_empty(
        self, keywords: Optional[List[str]] = None, max_results: int = 30
    ) -> List[Dict]:
        """Legacy wrapper for backward compatibility. Returns empty list on error.

        Use search_repos() directly for explicit error handling.
        """
        result = self.search_repos(keywords, max_results)
        if result.is_ok():
            return result.unwrap()
        else:
            if self.raise_errors:
                raise result.error
            return []

    def get_repo_files(
        self, repo_full_name: str, path: str = ""
    ) -> Result[List[Dict], V2RayFinderError]:
        """
        Get config files from a GitHub repository.

        Args:
            repo_full_name: Full repository name (e.g., "user/repo")
            path: Optional subdirectory path

        Returns:
            Result[List[Dict], V2RayFinderError]: Ok with list of file metadata,
                                                   or Err with error details
        """
        if self.should_stop():
            logger.info("Get repo files stopped by user request")
            return Ok([])

        url = f"{self.BASE_URL}/repos/{repo_full_name}/contents/{path}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)

            # Handle HTTP errors first (before _check_rate_limit)
            if response.status_code == 404:
                raise RepositoryNotFoundError(repo_full_name)
            elif response.status_code == 401:
                raise AuthenticationError()

            # Then check rate limits
            self._check_rate_limit(response)

            response.raise_for_status()
            files = response.json()

            config_files = []
            for file in files if isinstance(files, list) else [files]:
                if self.should_stop():
                    logger.info(f"Get repo files interrupted after {len(config_files)} files")
                    break

                if file.get("type") == "file":
                    name_lower = file["name"].lower()
                    if any(
                        ext in name_lower for ext in [".txt", ".json", "config", "sub"]
                    ):
                        config_files.append(
                            {
                                "name": file["name"],
                                "path": file["path"],
                                "download_url": file.get("download_url"),
                                "size": file["size"],
                            }
                        )

            logger.info(f"Found {len(config_files)} config files in {repo_full_name}")
            return Ok(config_files)

        except (RateLimitError, AuthenticationError, RepositoryNotFoundError) as e:
            logger.error(str(e))
            return Err(e)
        except requests.exceptions.Timeout as e:
            error = TimeoutError(
                f"Request timed out while fetching files from {repo_full_name}",
                url=url,
                timeout=10.0,
            )
            logger.error(str(error))
            return Err(error)
        except requests.exceptions.ConnectionError as e:
            error = NetworkError(f"Connection error while fetching files: {e}", url=url)
            logger.error(str(error))
            return Err(error)
        except requests.exceptions.RequestException as e:
            error = GitHubAPIError(f"Failed to fetch files from {repo_full_name}: {e}")
            logger.error(str(error))
            return Err(error)
        except Exception as e:
            error = V2RayFinderError(
                f"Unexpected error while fetching files: {e}", ErrorType.UNKNOWN_ERROR
            )
            logger.error(str(error), exc_info=True)
            return Err(error)

    def get_repo_files_or_empty(
        self, repo_full_name: str, path: str = ""
    ) -> List[Dict]:
        """Legacy wrapper for backward compatibility. Returns empty list on error.

        Use get_repo_files() directly for explicit error handling.
        """
        result = self.get_repo_files(repo_full_name, path)
        if result.is_ok():
            return result.unwrap()
        else:
            if self.raise_errors:
                raise result.error
            return []

    def _parse_servers(self, content: str) -> List[str]:
        """
        Parse V2Ray server configs from text content.

        Args:
            content: Raw text content containing server configs

        Returns:
            List of valid server configuration strings
        """
        servers = []
        supported_protocols = ["vmess://", "vless://", "trojan://", "ss://", "ssr://"]

        for line in content.split("\n"):
            if self.should_stop():
                logger.info(f"Parse servers interrupted after {len(servers)} servers")
                break

            line = line.strip()
            if any(line.startswith(p) for p in supported_protocols):
                servers.append(line)

        return servers

    def get_servers_from_url(
        self, url: str, timeout: float = 10.0
    ) -> Result[List[str], V2RayFinderError]:
        """
        Fetch and parse servers from a URL.

        Args:
            url: URL to fetch server configs from
            timeout: Request timeout in seconds

        Returns:
            Result[List[str], V2RayFinderError]: Ok with parsed server configs,
                                                  or Err with error details
        """
        if self.should_stop():
            logger.info("Get servers from URL stopped by user request")
            return Ok([])

        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()

            servers = self._parse_servers(response.text)
            logger.info(f"Fetched {len(servers)} servers from {url}")
            return Ok(servers)

        except requests.exceptions.Timeout as e:
            error = TimeoutError(
                f"Request timed out while fetching from {url}", url=url, timeout=timeout
            )
            logger.error(str(error))
            return Err(error)
        except requests.exceptions.ConnectionError as e:
            error = NetworkError(f"Connection error: {e}", url=url)
            logger.error(str(error))
            return Err(error)
        except requests.exceptions.RequestException as e:
            error = NetworkError(f"Failed to fetch from {url}: {e}", url=url)
            logger.error(str(error))
            return Err(error)
        except Exception as e:
            error = ParseError(f"Error parsing content from {url}: {e}")
            logger.error(str(error), exc_info=True)
            return Err(error)

    def get_servers_from_url_or_empty(
        self, url: str, timeout: float = 10.0
    ) -> List[str]:
        """Legacy wrapper for backward compatibility. Returns empty list on error.

        Use get_servers_from_url() directly for explicit error handling.
        """
        result = self.get_servers_from_url(url, timeout)
        if result.is_ok():
            return result.unwrap()
        else:
            if self.raise_errors:
                raise result.error
            return []

    def get_servers_from_github(
        self, search_keywords: Optional[List[str]] = None, max_repos: int = 10
    ) -> List[str]:
        """
        Search GitHub and extract servers from found repositories.

        Args:
            search_keywords: Keywords to search (default: ["free-v2ray", "v2ray-config"])
            max_repos: Maximum repositories to check per keyword

        Returns:
            Deduplicated list of server configs. Returns partial results if the
            operation is stopped via request_stop() or Ctrl+C.

        Note:
            This method uses legacy error handling (returns empty on error) for backward compatibility.
            Check get_rate_limit_info() after calling to see if rate limits were hit.
        """
        if search_keywords is None:
            search_keywords = ["free-v2ray", "v2ray-config"]

        all_servers: List[str] = []
        errors = []

        try:
            for keyword in search_keywords:
                if self.should_stop():
                    logger.info(
                        "GitHub search stopped by user request after "
                        f"{len(all_servers)} servers"
                    )
                    break

                repos_result = self.search_repos(
                    keywords=[keyword, "v2ray"], max_results=max_repos
                )

                if repos_result.is_err():
                    errors.append(repos_result.error)
                    if self.raise_errors:
                        raise repos_result.error
                    continue

                repos = repos_result.unwrap()

                for repo in repos[:max_repos]:
                    if self.should_stop():
                        logger.info(
                            "GitHub search stopped by user request after "
                            f"{len(all_servers)} servers"
                        )
                        break

                    files_result = self.get_repo_files(repo["full_name"])

                    if files_result.is_err():
                        errors.append(files_result.error)
                        if self.raise_errors:
                            raise files_result.error
                        continue

                    files = files_result.unwrap()

                    for file in files:
                        if self.should_stop():
                            logger.info(
                                "GitHub search stopped by user request after "
                                f"{len(all_servers)} servers"
                            )
                            break

                        if file["download_url"]:
                            servers_result = self.get_servers_from_url(
                                file["download_url"]
                            )

                            if servers_result.is_ok():
                                all_servers.extend(servers_result.unwrap())
                            else:
                                errors.append(servers_result.error)
                                if self.raise_errors:
                                    raise servers_result.error

        except KeyboardInterrupt:
            # Ctrl+C pressed during a blocking requests.get() call.
            # Partial all_servers list is captured here and returned.
            logger.info(
                "GitHub search interrupted via Ctrl+C — "
                f"returning {len(all_servers)} partial results"
            )
            self.request_stop()

        if errors:
            logger.warning(f"Encountered {len(errors)} errors during GitHub search")
            for error in errors:
                logger.debug(f"  - {error}")

        return list(dict.fromkeys(all_servers))

    def get_servers_from_known_sources(self) -> List[str]:
        """
        Fetch servers from curated known sources.

        Returns:
            Deduplicated list of server configs from known sources. Returns
            partial results if the operation is stopped via request_stop() or Ctrl+C.

        Note:
            This method uses legacy error handling for backward compatibility.
        """
        all_servers: List[str] = []
        errors = []

        try:
            for url in self.DIRECT_SOURCES:
                if self.should_stop():
                    logger.info(
                        "Known sources fetch stopped by user request after "
                        f"{len(all_servers)} servers"
                    )
                    break

                result = self.get_servers_from_url(url)

                if result.is_ok():
                    all_servers.extend(result.unwrap())
                else:
                    errors.append(result.error)
                    if self.raise_errors:
                        raise result.error

        except KeyboardInterrupt:
            # Ctrl+C pressed during a blocking requests.get() call.
            logger.info(
                "Known sources fetch interrupted via Ctrl+C — "
                f"returning {len(all_servers)} partial results"
            )
            self.request_stop()

        if errors:
            logger.warning(
                f"Failed to fetch from {len(errors)}/{len(self.DIRECT_SOURCES)} sources"
            )

        return list(dict.fromkeys(all_servers))

    def get_all_servers(self, use_github_search: bool = False) -> List[str]:
        """
        Get all servers from known sources and optionally GitHub search.

        Args:
            use_github_search: Whether to include GitHub repository search

        Returns:
            Deduplicated list of all discovered server configs
        """
        servers = self.get_servers_from_known_sources()

        if use_github_search and not self.should_stop():
            github_servers = self.get_servers_from_github()
            servers.extend(github_servers)
            servers = list(dict.fromkeys(servers))

        return servers

    def get_servers_sorted(
        self, limit: Optional[int] = None, use_github_search: bool = False
    ) -> List[Dict]:
        """
        Get structured server list with metadata.

        Args:
            limit: Optional limit on number of servers to return
            use_github_search: Whether to include GitHub search results

        Returns:
            List of dictionaries with server metadata (index, protocol, config, timestamp)
        """
        servers = self.get_all_servers(use_github_search=use_github_search)
        server_list = []

        for i, server in enumerate(servers, 1):
            if self.should_stop():
                logger.info(f"Get servers sorted stopped by user request after {len(server_list)} servers")
                break

            protocol = server.split("://")[0] if "://" in server else "unknown"
            server_list.append(
                {
                    "index": i,
                    "protocol": protocol,
                    "config": server,
                    "fetched_at": datetime.now().isoformat(),
                }
            )

        if limit:
            server_list = server_list[:limit]

        return server_list

    def get_servers_with_health(
        self,
        use_github_search: bool = False,
        check_health: bool = True,
        health_timeout: float = 5.0,
        concurrent_checks: int = 50,
        min_quality_score: float = 0.0,
        filter_unhealthy: bool = False,
        health_batch_size: int = 50,
    ) -> List[Dict]:
        """
        Get servers with optional health checking.

        Args:
            use_github_search: Whether to include GitHub search
            check_health: Whether to perform health checks
            health_timeout: Timeout for health checks in seconds
            concurrent_checks: Max concurrent health checks
            min_quality_score: Minimum quality score (0-100) to include
            filter_unhealthy: Whether to exclude unhealthy servers
            health_batch_size: Servers per health-check batch (enables stop between batches)

        Returns:
            List of server dictionaries with health information
        """
        servers = self.get_all_servers(use_github_search=use_github_search)

        if self.should_stop():
            logger.info("Health check stopped by user request before checking")
            return [
                {
                    "config": server,
                    "protocol": (
                        server.split("://")[0] if "://" in server else "unknown"
                    ),
                    "health_checked": False,
                }
                for server in servers
            ]

        if not check_health:
            # Return without health info
            return [
                {
                    "config": server,
                    "protocol": (
                        server.split("://")[0] if "://" in server else "unknown"
                    ),
                    "health_checked": False,
                }
                for server in servers
            ]

        # Import health checker only when needed
        try:
            from .health_checker import (
                HealthChecker,
                filter_healthy_servers,
                sort_by_quality,
            )
        except ImportError:
            logger.warning(
                "Health checker not available, returning servers without health info"
            )
            return [
                {
                    "config": server,
                    "protocol": (
                        server.split("://")[0] if "://" in server else "unknown"
                    ),
                    "health_checked": False,
                }
                for server in servers
            ]

        # Prepare server list for health checking
        server_tuples = [
            (server, server.split("://")[0] if "://" in server else "unknown")
            for server in servers
        ]

        checker = HealthChecker(
            timeout=health_timeout, concurrent_limit=concurrent_checks
        )

        # Batch health checking so stop requests are honoured between batches.
        # A single checker.check_servers(all) call would block until all N servers
        # are tested with no opportunity to cancel mid-way.
        logger.info(
            f"Checking health of {len(server_tuples)} servers "
            f"(batch_size={health_batch_size})..."
        )
        health_results = []
        try:
            for i in range(0, len(server_tuples), health_batch_size):
                if self.should_stop():
                    logger.info(
                        f"Health check stopped by user after {len(health_results)} servers "
                        f"(batch {i // health_batch_size + 1}/"
                        f"{(len(server_tuples) + health_batch_size - 1) // health_batch_size})"
                    )
                    break
                batch = server_tuples[i: i + health_batch_size]
                batch_results = checker.check_servers(batch)
                health_results.extend(batch_results)
        except KeyboardInterrupt:
            logger.info(
                f"Health check interrupted via Ctrl+C after {len(health_results)} servers"
            )
            self.request_stop()

        # Filter and sort on whatever results we have (full or partial)
        if filter_unhealthy or min_quality_score > 0:
            health_results = filter_healthy_servers(
                health_results,
                min_quality_score=min_quality_score,
                exclude_unreachable=filter_unhealthy,
            )

        health_results = sort_by_quality(health_results, descending=True)

        # Convert to dict format
        result_list = []
        for health in health_results:
            if self.should_stop() and not result_list:
                # Only skip conversion if we haven't started yet; once started
                # finish converting so the caller always gets a usable list.
                pass
            result_list.append(
                {
                    "config": health.config,
                    "protocol": health.protocol,
                    "health_checked": True,
                    "health_status": health.status.value,
                    "latency_ms": health.latency_ms,
                    "quality_score": health.quality_score,
                    "host": health.host,
                    "port": health.port,
                    "error": health.error,
                    "validation_error": health.validation_error,
                }
            )

        return result_list

    def save_to_file(
        self,
        filename: str = "v2ray_servers.txt",
        limit: Optional[int] = None,
        use_github_search: bool = False,
        check_health: bool = False,
        filter_unhealthy: bool = False,
        min_quality_score: float = 0.0,
    ) -> Tuple[int, str]:
        """
        Save servers to a text file.

        Args:
            filename: Output filename
            limit: Optional limit on number of servers
            use_github_search: Whether to include GitHub search
            check_health: Whether to perform health checks before saving
            filter_unhealthy: Whether to exclude unhealthy servers
            min_quality_score: Minimum quality score to include

        Returns:
            Tuple of (number of servers saved, filename)
        """
        if check_health:
            servers_data = self.get_servers_with_health(
                use_github_search=use_github_search,
                check_health=True,
                filter_unhealthy=filter_unhealthy,
                min_quality_score=min_quality_score,
            )
            servers = [s["config"] for s in servers_data]
        else:
            servers = self.get_all_servers(use_github_search=use_github_search)

        if limit:
            servers = servers[:limit]

        with open(filename, "w", encoding="utf-8") as f:
            for server in servers:
                f.write(f"{server}\n")

        logger.info(f"Saved {len(servers)} servers to {filename}")
        return len(servers), filename
