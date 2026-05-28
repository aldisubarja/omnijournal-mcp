"""Europe PMC provider — biomedical/life sciences."""

from __future__ import annotations

from omnijournal.models import Author, Paper
from omnijournal.providers import Provider, SearchType


class EuropePMCProvider(Provider):
    name = "europe_pmc"
    priority = 150
    base_delay = 0.2
    supports_pdf_lookup = True
    supported_search_types = [SearchType.KEYWORDS, SearchType.AUTHOR]

    async def search(self, query: str, search_type: SearchType, limit: int = 10) -> list[Paper]:
        await self._rate_limit()
        q = f'AUTHOR:"{query}"' if search_type == SearchType.AUTHOR else query
        params = {"query": q, "format": "json", "pageSize": limit, "resultType": "core"}
        resp = await self.client.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params=params)
        resp.raise_for_status()
        items = resp.json().get("resultList", {}).get("result", [])
        papers: list[Paper] = []
        for item in items:
            papers.append(Paper(
                title=item.get("title", ""),
                authors=[Author(name=a.strip()) for a in (item.get("authorString") or "").split(",") if a.strip()],
                abstract=item.get("abstractText"),
                doi=item.get("doi"),
                pmid=item.get("pmid"),
                year=int(item.get("pubYear")) if str(item.get("pubYear", "")).isdigit() else None,
                venue=item.get("journalTitle"),
                journal=item.get("journalTitle"),
                url=(f"https://europepmc.org/article/MED/{item.get('pmid')}" if item.get("pmid") else item.get("fullTextUrlList", {}).get("fullTextUrl", [{}])[0].get("url")),
                pdf_url=self._extract_pdf(item),
                is_open_access=bool(self._extract_pdf(item) or item.get("isOpenAccess") == "Y"),
                source_priority=self.priority,
                source=self.name,
            ))
        return [p for p in papers if p.title]

    def _extract_pdf(self, item: dict) -> str | None:
        urls = item.get("fullTextUrlList", {}).get("fullTextUrl", [])
        for u in urls:
            if str(u.get("documentStyle", "")).lower() == "pdf":
                return u.get("url")
        return None

    async def get_pdf_url(self, doi: str) -> str | None:
        return None
