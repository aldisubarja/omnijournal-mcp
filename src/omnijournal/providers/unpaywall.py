"""Unpaywall provider — Open Access resolver for any DOI."""

from __future__ import annotations

from omnijournal.models import Paper
from omnijournal.providers import Provider, SearchType


class UnpaywallProvider(Provider):
    name = "unpaywall"
    priority = 145
    base_delay = 0.2  # 100K calls/day
    supports_pdf_lookup = True
    supported_search_types = [SearchType.DOI]

    async def search(self, query: str, search_type: SearchType, limit: int = 10) -> list[Paper]:
        await self._rate_limit()
        clean = query.strip()
        if clean.lower().startswith("https://doi.org/"):
            clean = clean[len("https://doi.org/"):]
        params = {"email": self.config.unpaywall_email or "omnijournal@example.com"}
        resp = await self.client.get(f"https://api.unpaywall.org/v2/{clean}", params=params)
        resp.raise_for_status()
        data = resp.json()
        oa_loc = data.get("best_oa_location") or {}
        return [Paper(
            title=data.get("title", ""),
            doi=data.get("doi"),
            year=data.get("year"),
            venue=data.get("journal_name"),
            journal=data.get("journal_name"),
            url=oa_loc.get("url_for_landing_page"),
            pdf_url=oa_loc.get("url_for_pdf"),
            is_open_access=data.get("is_oa", False),
            source_priority=self.priority,
            source=self.name,
        )]

    async def get_pdf_url(self, doi: str) -> str | None:
        try:
            results = await self.search(doi, SearchType.DOI, limit=1)
            return results[0].pdf_url if results else None
        except Exception:
            return None
