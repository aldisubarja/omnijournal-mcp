"""bioRxiv provider — life sciences preprints."""

from __future__ import annotations

from omnijournal.models import Paper, Author
from omnijournal.providers import Provider, SearchType


class BiorxivProvider(Provider):
    name = "biorxiv"
    priority = 120
    base_delay = 1.0
    supports_pdf_lookup = True
    supported_search_types = [SearchType.KEYWORDS]

    async def search(self, query: str, search_type: SearchType, limit: int = 10) -> list[Paper]:
        await self._rate_limit()
        resp = await self.client.get("https://api.biorxiv.org/details/biorxiv/2020-01-01/9999-12-31/0")
        resp.raise_for_status()
        all_papers = resp.json().get("collection", [])
        filtered = []
        q_lower = query.lower()
        for item in all_papers:
            title = item.get("title", "")
            abstract = item.get("abstract", "")
            if q_lower in title.lower() or q_lower in abstract.lower():
                filtered.append(item)
            if len(filtered) >= limit:
                break
        papers: list[Paper] = []
        for item in filtered:
            papers.append(Paper(
                title=item.get("title", ""),
                authors=[Author(name=item.get("author_corresponding", "Unknown"))],
                abstract=item.get("abstract"),
                doi=item.get("doi"),
                year=int(item.get("date", "0")[:4]) if item.get("date") else None,
                url=item.get("doi") and f"https://doi.org/{item['doi']}",
                pdf_url=item.get("doi") and f"https://www.biorxiv.org/content/{item['doi']}.full.pdf",
                is_open_access=True,
                source_priority=self.priority,
                source=self.name,
            ))
        return papers
