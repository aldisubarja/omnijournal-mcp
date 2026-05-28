"""OpenAlex provider — largest open scholarly database."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnijournal.models import Author, Paper
from omnijournal.providers import Provider, SearchType

if TYPE_CHECKING:
    from omnijournal.config import Config
    import httpx


class OpenAlexProvider(Provider):
    name = "openalex"
    priority = 200
    base_delay = 0.1  # generous — 100K calls/day
    supported_search_types = [SearchType.KEYWORDS, SearchType.DOI, SearchType.AUTHOR]

    def __init__(self, client: httpx.AsyncClient, config: Config) -> None:
        super().__init__(client, config)
        self._params: dict[str, str] = {}
        if config.openalex_email:
            self._params["mailto"] = config.openalex_email

    async def search(self, query: str, search_type: SearchType, limit: int = 10) -> list[Paper]:
        await self._rate_limit()

        if search_type == SearchType.DOI:
            return await self._by_doi(query)
        if search_type == SearchType.AUTHOR:
            return await self._by_author(query, limit)
        return await self._by_keywords(query, limit)

    async def _by_doi(self, doi: str) -> list[Paper]:
        clean = doi.strip()
        if clean.lower().startswith("https://doi.org/"):
            clean = clean[len("https://doi.org/"):]
        url = f"https://api.openalex.org/works/doi:{clean}"
        params = self._params.copy()
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        paper = self._parse(data)
        return [paper] if paper else []

    async def _by_author(self, author: str, limit: int) -> list[Paper]:
        url = "https://api.openalex.org/works"
        quoted = f'"{author}"'  # OpenAlex requires double-quoted values when names contain spaces
        params = {
            **self._params,
            "filter": f"author.display_name.search:{quoted}",
            "per-page": limit,
            "sort": "cited_by_count:desc",
        }
        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            return self._parse_list(resp.json())
        except Exception:
            return []

    async def _by_keywords(self, query: str, limit: int) -> list[Paper]:
        url = "https://api.openalex.org/works"
        params = {
            **self._params,
            "search": query,
            "per-page": limit,
        }
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        return self._parse_list(resp.json())

    def _parse_list(self, data: dict) -> list[Paper]:
        papers: list[Paper] = []
        for item in data.get("results", []):
            p = self._parse(item)
            if p:
                papers.append(p)
        return papers

    def _parse(self, item: dict) -> Paper | None:
        if not item.get("title"):
            return None

        doi = None
        oa_info = item.get("open_access", {})
        is_oa = oa_info.get("is_oa", False)
        pdf_url = None
        if is_oa and oa_info.get("oa_url"):
            pdf_url = oa_info["oa_url"]

        primary_loc = item.get("primary_location") or {}
        source_info = primary_loc.get("source") or {}

        authors = [
            Author(
                name=(a.get("author", {}).get("display_name") or "Unknown"),
                orcid=a.get("author", {}).get("orcid"),
            )
            for a in item.get("authorships", [])
        ]

        # Resolve DOI from standard DOI or from any known ID
        doi = item.get("doi")
        if doi:
            doi = doi.replace("https://doi.org/", "")

        return Paper(
            title=item.get("title", ""),
            authors=authors,
            doi=doi,
            openalex_id=item.get("id", "").replace("https://openalex.org/", ""),
            year=item.get("publication_year"),
            venue=source_info.get("display_name"),
            journal=source_info.get("display_name"),
            pdf_url=pdf_url,
            url=item.get("doi") or primary_loc.get("landing_page_url"),
            citation_count=item.get("cited_by_count"),
            is_open_access=is_oa,
            source_priority=self.priority,
            source=self.name,
            abstract=None,  # OpenAlex free tier may omit abstract
        )
