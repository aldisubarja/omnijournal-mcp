"""arXiv provider."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from omnijournal.models import Author, Paper
from omnijournal.providers import Provider, SearchType

NS = {"a": "http://www.w3.org/2005/Atom"}


class ArxivProvider(Provider):
    name = "arxiv"
    priority = 160
    base_delay = 3.0
    supports_pdf_lookup = True
    supported_search_types = [SearchType.KEYWORDS, SearchType.DOI, SearchType.ARXIV]

    async def search(self, query: str, search_type: SearchType, limit: int = 10) -> list[Paper]:
        await self._rate_limit()
        search_query = f"all:{query}"
        if search_type in (SearchType.DOI, SearchType.ARXIV):
            clean_id = query.split(":", 1)[1] if ":" in query else query
            url = "https://export.arxiv.org/api/query"
            resp = await self.client.get(url, params={"id_list": clean_id})
        else:
            url = "https://export.arxiv.org/api/query"
            resp = await self.client.get(url, params={"search_query": search_query, "start": 0, "max_results": limit})
        resp.raise_for_status()
        return self._parse_feed(resp.text)

    def _parse_feed(self, xml_text: str) -> list[Paper]:
        root = ET.fromstring(xml_text)
        papers: list[Paper] = []
        for entry in root.findall("a:entry", NS):
            title = (entry.findtext("a:title", default="", namespaces=NS) or "").strip().replace("\n", " ")
            if not title:
                continue
            abs_url = entry.findtext("a:id", default="", namespaces=NS)
            arxiv_id = abs_url.split("/abs/")[-1] if "/abs/" in abs_url else None
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None
            published = entry.findtext("a:published", default="", namespaces=NS)
            year = int(published[:4]) if published[:4].isdigit() else None
            papers.append(Paper(
                title=title,
                authors=[Author(name=(a.findtext("a:name", default="", namespaces=NS) or "Unknown")) for a in entry.findall("a:author", NS)],
                abstract=(entry.findtext("a:summary", default="", namespaces=NS) or "").strip(),
                arxiv_id=arxiv_id,
                year=year,
                url=abs_url,
                pdf_url=pdf_url,
                is_open_access=True,
                source_priority=self.priority,
                source=self.name,
            ))
        return papers

    async def get_pdf_url(self, doi: str) -> str | None:
        if doi.lower().startswith("arxiv:"):
            arxiv_id = doi.split(":", 1)[1]
            return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        return None
