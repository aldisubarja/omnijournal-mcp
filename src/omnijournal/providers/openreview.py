"""OpenReview provider — ML conference papers."""

from __future__ import annotations

from omnijournal.models import Author, Paper
from omnijournal.providers import Provider, SearchType


def _unwrap(value):
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


class OpenReviewProvider(Provider):
    name = "openreview"
    priority = 140
    base_delay = 1.0
    supports_pdf_lookup = True
    supported_search_types = [SearchType.KEYWORDS]

    async def search(self, query: str, search_type: SearchType, limit: int = 10) -> list[Paper]:
        await self._rate_limit()
        try:
            resp = await self.client.get("https://api2.openreview.net/notes/search", params={
                "query": query,
                "limit": limit,
            })
            resp.raise_for_status()
            payload = resp.json()
            notes = payload.get("notes", payload.get("results", []))
        except Exception:
            return []
        papers: list[Paper] = []
        for note in notes:
            content = note.get("content", {})
            authors_arr = _unwrap(content.get("authors")) or []
            if isinstance(authors_arr, str):
                authors_arr = [authors_arr]
            title = _unwrap(content.get("title")) or "Unknown title"
            abstract = _unwrap(content.get("abstract"))
            venue = _unwrap(content.get("venue"))
            year_raw = _unwrap(content.get("year"))
            pdf_raw = _unwrap(content.get("pdf")) or _unwrap(content.get("pdf_url"))
            pdf_url = pdf_raw or (f"https://openreview.net/pdf?id={note['id']}" if note else None)
            if isinstance(pdf_url, str) and pdf_url.startswith("/"):
                pdf_url = f"https://openreview.net{pdf_url}"
            papers.append(Paper(
                title=title,
                authors=[Author(name=a) for a in authors_arr],
                abstract=abstract,
                url=f"https://openreview.net/forum?id={note['id']}",
                pdf_url=pdf_url,
                venue=venue,
                year=int(year_raw) if year_raw and str(year_raw).isdigit() else None,
                is_open_access=bool(pdf_url),
                source_priority=self.priority,
                source=self.name,
            ))
        return papers
