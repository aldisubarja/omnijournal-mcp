"""Provider base class, search types, and registry."""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    import httpx

    from omnijournal.config import Config
    from omnijournal.models import Paper

logger = logging.getLogger(__name__)


class SearchType(Enum):
    DOI = auto()
    KEYWORDS = auto()
    AUTHOR = auto()
    TITLE = auto()
    ARXIV = auto()


class Provider(ABC):
    name: str = "base"
    priority: int = 0
    base_delay: float = 0.1
    supports_pdf_lookup: bool = False
    supported_search_types: ClassVar[list[SearchType]] = [SearchType.KEYWORDS]

    def __init__(self, client: httpx.AsyncClient, config: Config) -> None:
        self.client = client
        self.config = config
        self._last_request: float = 0.0

    async def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.base_delay:
            await asyncio.sleep(self.base_delay - elapsed)
        self._last_request = time.monotonic()

    @abstractmethod
    async def search(self, query: str, search_type: SearchType, limit: int = 10) -> list[Paper]:
        """Search this provider and return normalized Paper objects."""
        ...

    async def get_pdf_url(self, doi: str) -> str | None:
        """Return a direct PDF URL for the given DOI, if available.

        Override in providers that support direct PDF resolution.
        """
        return None


def create_all_providers(client: httpx.AsyncClient, config: Config) -> list[Provider]:
    """Create and return all provider instances sorted by priority (highest first)."""
    from omnijournal.providers.openalex import OpenAlexProvider
    from omnijournal.providers.crossref import CrossrefProvider
    from omnijournal.providers.semantic_scholar import SemanticScholarProvider
    from omnijournal.providers.arxiv import ArxivProvider
    from omnijournal.providers.europe_pmc import EuropePMCProvider
    from omnijournal.providers.dblp import DBLPProvider
    from omnijournal.providers.pubmed import PubMedProvider
    from omnijournal.providers.openreview import OpenReviewProvider
    from omnijournal.providers.biorxiv import BiorxivProvider
    from omnijournal.providers.core import CoreProvider
    from omnijournal.providers.unpaywall import UnpaywallProvider

    providers: list[Provider] = [
        OpenAlexProvider(client, config),
        CrossrefProvider(client, config),
        PubMedProvider(client, config),
        SemanticScholarProvider(client, config),
        UnpaywallProvider(client, config),
        CoreProvider(client, config),
        OpenReviewProvider(client, config),
        ArxivProvider(client, config),
        BiorxivProvider(client, config),
        EuropePMCProvider(client, config),
        DBLPProvider(client, config),
    ]
    return sorted(providers, key=lambda p: p.priority, reverse=True)
