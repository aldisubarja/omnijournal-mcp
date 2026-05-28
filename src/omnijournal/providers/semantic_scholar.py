"""Semantic Scholar provider — citations, recommendations, OA links."""

from __future__ import annotations

from omnijournal.models import Author, Paper
from omnijournal.providers import Provider, SearchType

FIELDS = ",".join([
    "title","abstract","authors","year","venue","url","externalIds","citationCount","isOpenAccess","openAccessPdf"
])


class SemanticScholarProvider(Provider):
    name = "semantic_scholar"
    priority = 170
    base_delay = 2.0  # 1 req/sec without key; pad for safety
    supports_pdf_lookup = True
    supported_search_types = [SearchType.KEYWORDS, SearchType.DOI, SearchType.AUTHOR]

    def _headers(self) -> dict[str, str]:
        headers = {}
        if self.config.semantic_scholar_api_key:
            headers["x-api-key"] = self.config.semantic_scholar_api_key
        return headers

    async def search(self, query: str, search_type: SearchType, limit: int = 10) -> list[Paper]:
        await self._rate_limit()
        try:
            if search_type == SearchType.DOI:
                clean = query.replace("https://doi.org/", "").strip()
                resp = await self.client.get(
                    f"https://api.semanticscholar.org/graph/v1/paper/DOI:{clean}",
                    params={"fields": FIELDS},
                    headers=self._headers(),
                )
                if resp.status_code == 429:
                    return []
                resp.raise_for_status()
                paper = self._parse(resp.json())
                return [paper] if paper else []
            params = {"query": query, "limit": limit, "fields": FIELDS}
            resp = await self.client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params=params,
                headers=self._headers(),
            )
            if resp.status_code == 429:
                return []
            resp.raise_for_status()
            return [p for p in (self._parse(item) for item in resp.json().get("data", [])) if p]
        except Exception:
            return []

    def _parse(self, item: dict) -> Paper | None:
        if not item.get("title"):
            return None
        external = item.get("externalIds") or {}
        pdf = item.get("openAccessPdf") or {}
        doi = external.get("DOI")
        arxiv_id = external.get("ArXiv")
        return Paper(
            title=item.get("title", ""),
            authors=[Author(name=a.get("name", "Unknown")) for a in item.get("authors", [])],
            abstract=item.get("abstract"),
            doi=doi,
            arxiv_id=arxiv_id,
            semantic_scholar_id=item.get("paperId"),
            year=item.get("year"),
            venue=item.get("venue"),
            url=item.get("url"),
            pdf_url=pdf.get("url"),
            citation_count=item.get("citationCount"),
            is_open_access=bool(item.get("isOpenAccess") or pdf.get("url")),
            source_priority=self.priority,
            source=self.name,
        )

    async def get_pdf_url(self, doi: str) -> str | None:
        try:
            results = await self.search(doi, SearchType.DOI, limit=1)
            return results[0].pdf_url if results else None
        except Exception:
            return None
