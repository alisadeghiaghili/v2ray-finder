"""Core module for V2Ray server discovery."""

import logging
import requests
from typing import List, Dict, Optional, Tuple
from datetime import datetime


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

    def __init__(self, token: Optional[str] = None):
        """
        Initialize V2RayServerFinder.

        Args:
            token: Optional GitHub personal access token for higher API rate limits
        """
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            self.headers["Authorization"] = f"token {token}"

    def search_repos(
        self, keywords: Optional[List[str]] = None, max_results: int = 30
    ) -> List[Dict]:
        """
        Search GitHub repositories matching keywords.

        Args:
            keywords: List of search keywords (default: ["v2ray", "free", "config"])
            max_results: Maximum number of results to return

        Returns:
            List of repository metadata dictionaries
        """
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
            response.raise_for_status()
            data = response.json()

            results = []
            for repo in data.get("items", []):
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
            return results
        except Exception as e:
            logger.error(f"Repository search failed: {e}")
            return []

    def get_repo_files(self, repo_full_name: str, path: str = "") -> List[Dict]:
        """
        Get config files from a GitHub repository.

        Args:
            repo_full_name: Full repository name (e.g., "user/repo")
            path: Optional subdirectory path

        Returns:
            List of file metadata dictionaries with download URLs
        """
        url = f"{self.BASE_URL}/repos/{repo_full_name}/contents/{path}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            files = response.json()

            config_files = []
            for file in files if isinstance(files, list) else [files]:
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
            return config_files
        except Exception as e:
            logger.error(f"Failed to get files from {repo_full_name}: {e}")
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
            line = line.strip()
            if any(line.startswith(p) for p in supported_protocols):
                servers.append(line)

        return servers

    def get_servers_from_url(self, url: str) -> List[str]:
        """
        Fetch and parse servers from a URL.

        Args:
            url: URL to fetch server configs from

        Returns:
            List of parsed server configs
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return self._parse_servers(response.text)
        except Exception as e:
            logger.error(f"Failed to fetch from {url}: {e}")
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
            Deduplicated list of server configs
        """
        if search_keywords is None:
            search_keywords = ["free-v2ray", "v2ray-config"]

        all_servers = []

        for keyword in search_keywords:
            repos = self.search_repos(
                keywords=[keyword, "v2ray"], max_results=max_repos
            )

            for repo in repos[:max_repos]:
                files = self.get_repo_files(repo["full_name"])
                for file in files:
                    if file["download_url"]:
                        servers = self.get_servers_from_url(file["download_url"])
                        all_servers.extend(servers)

        return list(dict.fromkeys(all_servers))

    def get_servers_from_known_sources(self) -> List[str]:
        """
        Fetch servers from curated known sources.

        Returns:
            Deduplicated list of server configs from known sources
        """
        all_servers = []

        for url in self.DIRECT_SOURCES:
            servers = self.get_servers_from_url(url)
            all_servers.extend(servers)

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

        if use_github_search:
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

    def save_to_file(
        self,
        filename: str = "v2ray_servers.txt",
        limit: Optional[int] = None,
        use_github_search: bool = False,
    ) -> Tuple[int, str]:
        """
        Save servers to a text file.

        Args:
            filename: Output filename
            limit: Optional limit on number of servers
            use_github_search: Whether to include GitHub search

        Returns:
            Tuple of (number of servers saved, filename)
        """
        servers = self.get_all_servers(use_github_search=use_github_search)

        if limit:
            servers = servers[:limit]

        with open(filename, "w", encoding="utf-8") as f:
            for server in servers:
                f.write(f"{server}\n")

        logger.info(f"Saved {len(servers)} servers to {filename}")
        return len(servers), filename
