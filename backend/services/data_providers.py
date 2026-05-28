"""
Data Providers - Phase 2 (OCP Fix)
Abstracts external data sources behind a common interface.
Add new sources (GitLab, HackerRank) without modifying analysis_service.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class DataProvider(ABC):
    """Abstract data provider — one method contract."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Identifier for this provider e.g. 'github', 'leetcode'."""
        ...

    @abstractmethod
    async def fetch_data(self, username: str) -> Dict[str, Any]:
        """Fetch all relevant data for a given username."""
        ...


class GithubDataProvider(DataProvider):
    """Fetches GitHub data for a user."""

    @property
    def source_name(self) -> str:
        return "github"

    async def fetch_data(self, username: str) -> Dict[str, Any]:
        from services import github_service
        return await github_service.get_full_github_data(username)


class LeetcodeDataProvider(DataProvider):
    """Fetches LeetCode data for a user."""

    @property
    def source_name(self) -> str:
        return "leetcode"

    async def fetch_data(self, username: str) -> Dict[str, Any]:
        from services import leetcode_service
        return await leetcode_service.get_full_leetcode_data(username)


# ── Provider registry ────────────────────────────────────────────────────────
# To add HackerRank: create HackerrankDataProvider, add to this list.
# analysis_service never needs to change.

DEFAULT_PROVIDERS = [
    GithubDataProvider(),
    LeetcodeDataProvider(),
]