"""Crossref provider — DOI resolution and rich metadata."""

from __future__ import annotations

from urllib.parse import quote

from omnijournal.models import Author, Paper
from omnijournal.providers import Provider, SearchType


class CrossrefProvider(Provider):
    name = "crossref"
    priority = 180
    base_delay = 0.2
    supported_search_types = [SearchType.KEYWORDS, SearchType.DOI, SearchType.AUTHOR]

    async def search(self, query: str, search_type: SearchType, limit: int = 10) -> list[Paper]:
        await self._rate_limit()
        if search_type == SearchType.DOI:
            return await self._by_doi(query)
        params = {"rows": limit, "select": "DOI,title,author,abstract,published-print,issued,container-title,URL,is-referenced-by-count,volume,issue,page"}
        if search_type == SearchType.AUTHOR:
            params["query.author"] = query
        else:
            params["query.bibliographic"] = query
        headers = {"User-Agent": f"omnijournal/0.1 ({self.config.crossref_email})"} if self.config.crossref_email else {}
        resp = await self.client.get("https://api.crossref.org/works", params=params, headers=headers)
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])
        return [p for p in (self._parse(item) for item in items) if p]

    async def _by_doi(self, doi: str) -> list[Paper]:
        clean = doi.replace("https://doi.org/", "").strip()
        headers = {"User-Agent": f"omnijournal/0.1 ({self.config.crossref_email})"} if self.config.crossref_email else {}
        resp = await self.client.get(f"https://api.crossref.org/works/{quote(clean, safe='')}" , headers=headers)
        resp.raise_for_status()
        item = resp.json().get("message", {})
        paper = self._parse(item)
        return [paper] if paper else []

    def _parse(self, item: dict) -> Paper | None:
        titles = item.get("title") or []
        if not titles:
            return None
        year = None
        issued = item.get("issued", {}).get("date-parts", [])
        if issued and issued[0]:
            year = issued[0][0]
        return Paper(
            title=titles[0],
            authors=[Author(name=" ".join(filter(None, [a.get("given"), a.get("family")])).strip() or a.get("name", "Unknown")) for a in item.get("author", [])],
            abstract=item.get("abstract"),
            doi=item.get("DOI"),
            year=year,
            venue=(item.get("container-title") or [None])[0],
            journal=(item.get("container-title") or [None])[0],
            url=item.get("URL"),
            volume=item.get("volume"),
            issue=item.get("issue"),
            pages=item.get("page"),
            citation_count=item.get("is-referenced-by-count"),
            source_priority=self.priority,
            source=self.name,
        )

    async def get_pdf_url(self, doi: str) -> str | None:
        return None
