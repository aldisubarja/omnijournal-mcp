"""DBLP provider — computer science bibliography."""

from __future__ import annotations

from urllib.parse import quote

from omnijournal.models import Author, Paper
from omnijournal.providers import Provider, SearchType


class DBLPProvider(Provider):
    name = "dblp"
    priority = 130
    base_delay = 0.5
    supported_search_types = [SearchType.KEYWORDS, SearchType.AUTHOR]

    async def search(self, query: str, search_type: SearchType, limit: int = 10) -> list[Paper]:
        await self._rate_limit()
        params = {"q": query, "format": "json", "h": limit}
        try:
            resp = await self.client.get("https://dblp.org/search/publ/api", params=params)
            resp.raise_for_status()
        except Exception:
            return []
        hits = resp.json().get("result", {}).get("hits", {}).get("hit", [])
        papers: list[Paper] = []
        for h in hits:
            info = h.get("info", {})
            authors_arr = info.get("authors", {}).get("author", [])
            if isinstance(authors_arr, dict):
                authors_arr = [authors_arr]
            papers.append(Paper(
                title=info.get("title", ""),
                authors=[Author(name=a.get("text", "Unknown") if isinstance(a, dict) else str(a)) for a in authors_arr],
                year=int(info.get("year")) if info.get("year") and str(info.get("year")).isdigit() else None,
                venue=info.get("venue"),
                journal=info.get("venue"),
                url=info.get("ee") or info.get("url"),
                doi=info.get("doi"),
                source_priority=self.priority,
                source=self.name,
            ))
        return papers
