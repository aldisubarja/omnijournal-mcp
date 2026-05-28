"""CORE provider — global open access repository aggregator."""

from __future__ import annotations

from urllib.parse import quote

from omnijournal.models import Author, Paper
from omnijournal.providers import Provider, SearchType


class CoreProvider(Provider):
    name = "core"
    priority = 135
    base_delay = 1.0
    supports_pdf_lookup = True
    supported_search_types = [SearchType.KEYWORDS]

    async def search(self, query: str, search_type: SearchType, limit: int = 10) -> list[Paper]:
        await self._rate_limit()
        params = {
            "q": query,
            "limit": limit,
        }
        resp = await self.client.get("https://api.core.ac.uk/v3/search/works", params=params, headers={"User-Agent": "omnijournal/0.1"})
        resp.raise_for_status()
        hits = resp.json().get("results", [])
        papers: list[Paper] = []
        for h in hits:
            papers.append(Paper(
                title=h.get("title", ""),
                authors=[Author(name=a.get("name", "Unknown")) for a in h.get("authors", [])],
                abstract=h.get("abstract"),
                doi=h.get("doi"),
                year=h.get("yearPublished"),
                venue=h.get("publisher"),
                url=h.get("sourceFulltextUrls", [None])[0],
                pdf_url=self._best_pdf(h),
                is_open_access=True,
                source_priority=self.priority,
                source=self.name,
            ))
        return papers

    def _best_pdf(self, item: dict) -> str | None:
        links = item.get("links", [])
        for link in links:
            if link.get("type") == "download":
                return link.get("url")
        return item.get("downloadUrl")

    async def get_pdf_url(self, doi: str) -> str | None:
        try:
            results = await self.search(doi, SearchType.KEYWORDS, limit=1)
            return results[0].pdf_url if results else None
        except Exception:
            return None
